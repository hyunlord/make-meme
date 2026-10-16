"""Performance measurement: live ComfyUI memory polling during a generation
(:class:`PerfRecorder`), a cost model fit from recorded history (:func:`estimate_seconds`),
and precaching the Wan text encoder before a batch of generations
(:func:`precache_prompts`).

History lives in ``$MAKE_MEME_HOME/perf.jsonl``, one JSON object per line:
``{ts, profile, recipe, width, height, frames, steps, refs, seconds, peak_bytes,
peak_system_used_bytes, ok}``. The caller supplies the generation params (profile,
recipe, width, height, frames, steps, refs) as ``meta`` to :class:`PerfRecorder`;
everything else is measured.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Self

from .config import get_settings
from .pipelines.runtime import run_recipe
from .recipes.loader import get_recipe

logger = logging.getLogger(__name__)


class PerfRecorder:
    """Async context manager: polls ``client.stats()`` every ``POLL_INTERVAL_SEC`` while
    active, tracking peak device and system memory, then appends one JSON line to
    ``perf.jsonl`` on exit (success or failure) combining ``meta`` with what was measured.
    """

    POLL_INTERVAL_SEC = 10.0

    def __init__(self, client: Any, job_label: str, meta: dict[str, Any]) -> None:
        self.client = client
        self.job_label = job_label
        self.meta = dict(meta)
        self._task: asyncio.Task[None] | None = None
        self._start = 0.0
        self._peak_device_bytes = 0
        self._peak_system_used_bytes = 0
        self._last_record: dict[str, Any] = {}

    async def __aenter__(self) -> Self:
        self._start = time.monotonic()
        self._task = asyncio.ensure_future(self._poll_loop())
        return self

    async def _poll_loop(self) -> None:
        while True:
            await self._sample()
            await asyncio.sleep(self.POLL_INTERVAL_SEC)

    async def _sample(self) -> None:
        try:
            stats = await self.client.stats()
        except Exception:  # noqa: BLE001 - polling must never crash the job it's measuring
            stats = None
        if not stats:
            return

        device_vals = [
            stats.get(key)
            for key in ("driver_allocated_bytes", "max_allocated_bytes", "allocated_bytes")
        ]
        device_vals = [v for v in device_vals if isinstance(v, (int, float))]
        if device_vals:
            self._peak_device_bytes = max(self._peak_device_bytes, int(max(device_vals)))

        total, available = stats.get("system_total_bytes"), stats.get("system_available_bytes")
        if isinstance(total, (int, float)) and isinstance(available, (int, float)):
            self._peak_system_used_bytes = max(self._peak_system_used_bytes, int(total - available))

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._sample()  # one last sample so even a very short job gets a data point

        seconds = time.monotonic() - self._start
        self._last_record = {
            **self.meta,
            "ts": time.time(),
            "seconds": round(seconds, 3),
            "peak_bytes": self._peak_device_bytes or None,
            "peak_system_used_bytes": self._peak_system_used_bytes or None,
            "ok": exc_type is None,
        }
        try:
            settings = get_settings()
            settings.home.mkdir(parents=True, exist_ok=True)
            with (settings.home / "perf.jsonl").open("a") as fh:
                fh.write(json.dumps(self._last_record) + "\n")
        except OSError:
            logger.warning("could not write perf.jsonl", exc_info=True)

        return False  # never swallow the original exception

    def summary(self) -> dict[str, Any]:
        return dict(self._last_record)


# --------------------------------------------------------------------------
# Cost model
# --------------------------------------------------------------------------


def _tokens_for(width: int, height: int, frames: int) -> float:
    """Rough token count for a Wan generation at this size/frame count."""
    return float((frames // 4 * 2 + 3) * (width // 16) * (height // 16))


def _fit_quadratic_no_intercept(points: list[tuple[float, float]]) -> tuple[float, float]:
    """Least-squares fit of seconds_per_step ~= a*tokens + b*tokens^2 (no intercept) from
    >=2 (tokens, seconds_per_step) points."""
    sx2 = sum(t * t for t, _ in points)
    sx3 = sum(t**3 for t, _ in points)
    sx4 = sum(t**4 for t, _ in points)
    sxy = sum(t * s for t, s in points)
    sx2y = sum(t * t * s for t, s in points)
    det = sx2 * sx4 - sx3 * sx3
    if abs(det) < 1e-6:
        # degenerate (e.g. every sample has the same tokens) -- average linear ratio
        avg_ratio = sum(s / t for t, s in points if t) / len(points)
        return avg_ratio, 0.0
    a = (sx4 * sxy - sx3 * sx2y) / det
    b = (sx2 * sx2y - sx3 * sxy) / det
    return a, b


def _seconds_per_step_from_points(points: list[tuple[float, float]], tokens: float) -> float:
    """>=2 points: quadratic least-squares fit, evaluated at `tokens`. 1 point: scale by
    the tokens ratio, split 50/50 between linear and quadratic (can't separate a from b
    from a single point)."""
    if len(points) >= 2:
        a, b = _fit_quadratic_no_intercept(points)
        return max(0.0, a * tokens + b * tokens * tokens)
    (tokens0, sps0) = points[0]
    ratio = (tokens / tokens0) if tokens0 else 1.0
    return max(0.0, sps0 * (0.5 * ratio + 0.5 * ratio * ratio))


def _load_samples(profile: str, recipe: str) -> list[tuple[float, float]]:
    """(tokens, seconds_per_step) points from perf.jsonl matching `profile`/`recipe`,
    excluding failed runs (``ok: false``) and rows missing what's needed to compute them.
    """
    path = get_settings().home / "perf.jsonl"
    if not path.is_file():
        return []
    points: list[tuple[float, float]] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("profile") != profile or rec.get("recipe") != recipe:
            continue
        if not rec.get("ok", True):
            continue
        width, height, frames = rec.get("width"), rec.get("height"), rec.get("frames")
        steps, seconds = rec.get("steps"), rec.get("seconds")
        if not all(isinstance(v, (int, float)) and v for v in (width, height, frames, steps, seconds)):
            continue
        tokens = _tokens_for(int(width), int(height), int(frames))
        points.append((tokens, seconds / steps))
    return points


# Hardcoded fallbacks for when perf.jsonl has no matching samples yet.
_DEFAULT_ANCHORS: dict[tuple[str, str], list[tuple[float, float]]] = {
    # Real measurements (M4 Max, 36 GB): tokens -> seconds/step.
    ("mps", "mocha_swap"): [(7488.0, 50.0), (25920.0, 360.0)],
}
_DEFAULT_GUESS_ANCHORS: dict[tuple[str, str], list[tuple[float, float]]] = {
    # Unverified guesses -- replace with real measurements as they come in.
    ("cuda_lowvram", "mocha_swap"): [(25920.0, 40.0)],
}
_DEFAULT_GUESS_FLAT: dict[tuple[str, str], float] = {
    ("cuda", "mocha_swap"): 15.0,
}
_FALLBACK_FLAT_SECONDS_PER_STEP = 60.0  # last resort: any profile/recipe with no data at all


def estimate_seconds(
    profile: str, recipe: str, width: int, height: int, frames: int, steps: int
) -> dict[str, Any]:
    """Rough wall-clock estimate for a generation, in seconds.

    Cost model: seconds ~= steps * (a*tokens + b*tokens^2), tokens from width/height/frames
    (see :func:`_tokens_for`). (a, b) are fit by least squares from perf.jsonl rows matching
    `profile`/`recipe` when there are >=2; with exactly 1 matching row the estimate scales
    that sample by the tokens ratio. With zero recorded samples, falls back to hardcoded
    per-profile/recipe defaults (``basis`` distinguishes real measurements -- "default" --
    from unverified guesses -- "default-guess").
    """

    tokens = _tokens_for(width, height, frames)
    samples = _load_samples(profile, recipe)
    if samples:
        per_step = _seconds_per_step_from_points(samples, tokens)
        return {"seconds": per_step * steps, "basis": "measured", "samples": len(samples)}

    key = (profile, recipe)
    if key in _DEFAULT_ANCHORS:
        per_step = _seconds_per_step_from_points(_DEFAULT_ANCHORS[key], tokens)
        return {"seconds": per_step * steps, "basis": "default", "samples": 0}
    if key in _DEFAULT_GUESS_ANCHORS:
        per_step = _seconds_per_step_from_points(_DEFAULT_GUESS_ANCHORS[key], tokens)
        return {"seconds": per_step * steps, "basis": "default-guess", "samples": 0}
    per_step = _DEFAULT_GUESS_FLAT.get(key, _FALLBACK_FLAT_SECONDS_PER_STEP)
    return {"seconds": per_step * steps, "basis": "default-guess", "samples": 0}


# --------------------------------------------------------------------------
# Precaching
# --------------------------------------------------------------------------


async def precache_prompts(client: Any, pairs: list[tuple[str, str]], *, profile: str) -> None:
    """Run wan_text_cache once per unique (prompt, negative_prompt) pair so a later
    mocha_swap run with the same prompt hits the on-disk T5 cache instead of re-encoding,
    then free the encoder from memory (11 GB) before sampling starts."""

    recipe = get_recipe("wan_text_cache")
    seen: set[tuple[str, str]] = set()
    for prompt, negative in pairs:
        key = (prompt, negative)
        if key in seen:
            continue
        seen.add(key)
        await run_recipe(
            client, recipe,
            media={}, values={"prompt": prompt, "negative_prompt": negative},
            profile=profile, stage="precaching",
        )
    await client.free()
