"""analyze_meme_usage: how do people actually use a song in shorts/memes?

Finds the original MV plus short-form videos (challenges, covers, memes) and aligns each
short's audio against the MV to learn which part of the song gets reused and for how long.
When there are few shorts (e.g. a song released days ago) the song's own most-repeated
section (the hook) is used as supporting evidence."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import statistics
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import Image as MCPImage
from mcp.server.fastmcp.exceptions import ToolError
from PIL import Image, ImageDraw

from make_meme import ingest
from make_meme.analysis import audio_align as A
from make_meme.config import get_settings
from make_meme.server import _load_sources_backend, get_assets, load_media, mcp

logger = logging.getLogger(__name__)

MAX_SHORT_SEC = 75
_GENERIC = {
    "official", "video", "music", "mv", "m/v", "the", "feat", "ver", "version", "performance",
    "dance", "practice", "teaser", "lyrics", "audio", "hd", "4k", "8k", "뮤직비디오", "공식", "티저",
}


def title_tokens(title: str) -> set[str]:
    """Distinctive words of a title (artist/song names), used to drop unrelated search hits."""
    words = re.findall(r"[A-Za-z0-9]{2,}|[가-힣]{2,}", title)
    return {w.lower() for w in words if w.lower() not in _GENERIC}


def is_relevant(title: str | None, tokens: set[str]) -> bool:
    if not title or not tokens:
        return False
    found = {w.lower() for w in re.findall(r"[A-Za-z0-9]{2,}|[가-힣]{2,}", title)}
    return bool(found & tokens)


def core_name(title: str) -> str:
    """'A2O LITE 'NEON' Official Video' -> 'A2O LITE NEON'."""
    cleaned = re.sub(r"[\[\(].*?[\]\)]|['\"‘’“”|]", " ", title)
    words = [w for w in cleaned.split() if w.lower() not in _GENERIC]
    return " ".join(words[:5]) or title


async def _pick_reference(sources, song: str) -> str:
    cands = await sources.search(f"{song} official MV", kind="video", n=6, provider="youtube")
    for c in cands:
        t = (c.title or "").lower()
        if any(k in t for k in ("official", "m/v", " mv", "뮤직비디오")) and (c.duration or 0) > 90:
            return c.url
    if not cands:
        raise ToolError(f"Couldn't find an MV for {song!r}; pass `reference` (link or asset id).")
    return cands[0].url


async def _find_shorts(sources, queries: list[str], tokens: set[str], exclude: str, n: int) -> tuple[list, int]:
    seen, picked, dropped = {exclude}, [], 0
    for q in queries:
        try:
            cands = await sources.search(q, kind="video", n=12, provider="youtube")
        except sources.SourceError as e:
            logger.info("search %r failed: %s", q, e)
            continue
        for c in cands:
            if c.url in seen or not c.duration or c.duration > MAX_SHORT_SEC:
                continue
            seen.add(c.url)
            if not is_relevant(c.title, tokens):
                dropped += 1
                continue
            picked.append(c)
            if len(picked) >= n:
                return picked, dropped
    return picked, dropped


def _timeline(duration: float, rows: list[dict], hook: A.Hook | None, hot: list[A.Hotspot], path: Path) -> Path:
    W, row_h, top = 1000, 22, 60
    H = top + row_h * max(1, len(rows)) + 30
    img = Image.new("RGB", (W, H), (250, 250, 250))
    d = ImageDraw.Draw(img)

    def sx(t: float) -> float:
        return 40 + (W - 80) * t / max(duration, 1)

    d.text((40, 8), "MV timeline (s). grey = hook repeats, orange = most reused, blue = each short", fill=(0, 0, 0))
    for t in range(0, int(duration) + 1, 15):
        d.line([sx(t), 30, sx(t), H - 20], fill=(225, 225, 225))
        d.text((sx(t) - 6, H - 18), str(t), fill=(90, 90, 90))
    if hook:
        for s in [hook.start, *hook.repeats]:
            d.rectangle([sx(s), 30, sx(s + hook.end - hook.start), 44], fill=(190, 190, 190))
    for h in hot:
        d.rectangle([sx(h.start), 46, sx(h.end), 56], fill=(255, 150, 40))
    for i, r in enumerate(rows):
        y = top + i * row_h
        if r.get("used"):
            s, e = r["used"]
            d.rectangle([sx(s), y + 3, sx(e), y + row_h - 5], fill=(60, 120, 230))
        d.text((sx(0) - 32, y + 4), f"#{i + 1}", fill=(0, 0, 0))
    img.save(path)
    return path


@mcp.tool()
async def analyze_meme_usage(song: str, reference: str | None = None, n: int = 10) -> list[Any]:
    """Learn how a song is used in shorts/memes before making one: which part of the song
    people reuse and for how long. Finds the official MV (or uses `reference`: link or video
    asset id) and up to `n` short videos (challenges/covers/memes, ≤75 s, YouTube), aligns
    each short's audio to the MV, and also detects the song's most-repeated section (hook).
    Returns per-short matches, the most reused MV ranges, the hook, a recommended segment
    (start/end in MV seconds) and a timeline image. The MV is registered as an asset so you
    can trim it with load_media(reference_asset, start_sec, end_sec). Takes ~1-3 minutes."""
    sources = _load_sources_backend()
    n = max(1, min(n, 20))
    ref_source = reference or await _pick_reference(sources, song)
    ref_info = json.loads((await load_media(ref_source))[0])
    ref_asset = get_assets().get(ref_info["id"])
    if ref_asset is None or ref_asset.kind != "video":
        raise ToolError("The reference must be a video.")
    title = str(ref_asset.origin.get("title") or song)
    tokens = title_tokens(title) or title_tokens(song)
    core = core_name(title)
    queries = [f"{core} 챌린지", f"{core} challenge", f"{core} shorts", f"{core} 밈", f"{song} 챌린지", f"{core} cover"]
    exclude = str(ref_asset.origin.get("url") or ref_source)
    shorts, dropped = await _find_shorts(sources, queries, tokens, exclude, n)

    ref_feat = await asyncio.to_thread(lambda: A.features(A.load_audio(ref_asset.path)))
    duration = ref_feat.shape[0] * A.FRAME_SEC
    hook = await asyncio.to_thread(A.find_hook, ref_feat)

    dest = get_settings().videos_dir / "_fetched"
    sem = asyncio.Semaphore(3)

    async def analyze(c) -> dict:
        row: dict[str, Any] = {"title": c.title, "url": c.url, "duration": c.duration}
        try:
            async with sem:
                fetched = await sources.fetch(c.url, dest)
            al = await asyncio.to_thread(lambda: A.align(ref_feat, A.features(A.load_audio(fetched.path))))
            row["_path"] = str(fetched.path)
        except Exception as e:  # noqa: BLE001 - one bad short must not sink the analysis
            row["error"] = f"{type(e).__name__}: {e}"[:200]
            return row
        if al is not None:
            row.update(used=[round(al.ref_start, 1), round(al.ref_end, 1)], length=round(al.length, 1),
                       speed=al.speed, confidence=round(al.confidence, 2))
        return row

    rows = await asyncio.gather(*(analyze(c) for c in shorts))
    matched = [(i, r) for i, r in enumerate(rows) if r.get("used")]
    aligns = [(i, A.Alignment(r["used"][0], r["used"][1], r["speed"], r["confidence"], [])) for i, r in matched]
    hot = A.hotspots(aligns, duration=duration)
    lengths = [r["length"] for _, r in matched]

    rec_len = min(8.0, max(3.0, statistics.median(lengths))) if lengths else 5.0
    if hot and hot[0].count >= 2:
        center = (hot[0].start + hot[0].end) / 2
        basis = f"most reused range ({hot[0].count} of {len(matched)} matched shorts)"
    elif hook:
        center = (hook.start + hook.end) / 2
        basis = "song's most repeated section (hook); too few shorts to rely on usage data"
    else:
        center, basis = duration / 3, "no usage data or clear hook; first third of the song"
    start = max(0.0, round(center - rec_len / 2, 1))
    recommendation = {"start": start, "end": round(min(duration, start + rec_len), 1), "basis": basis}

    vibe_paths = [r["_path"] for _, r in matched[:6]]
    timeline = _timeline(duration, rows, hook, hot, ref_asset.path.parent / "meme_usage_timeline.png")
    content: list[Any] = [json.dumps({
        "reference": {"asset_id": ref_asset.id, "title": title, "duration": round(duration, 1)},
        "shorts_analyzed": len(rows), "shorts_matched": len(matched), "unrelated_results_dropped": dropped,
        "shorts": [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows],
        "most_reused": [{"start": h.start, "end": h.end, "shorts": h.count} for h in hot],
        "hook": None if hook is None else {"start": round(hook.start, 1), "end": round(hook.end, 1),
                                           "repeats_at": hook.repeats},
        "typical_length_sec": round(statistics.median(lengths), 1) if lengths else None,
        "recommendation": recommendation,
        "notes": "TikTok has no keyless search, so usage data comes from YouTube Shorts/videos. "
                 "Few matches usually means the song is new; weigh the hook more then.",
    }, indent=2, ensure_ascii=False), MCPImage(path=str(timeline))]
    if vibe_paths:
        content.append(MCPImage(path=str(await asyncio.to_thread(_vibe_board, vibe_paths, ref_asset.path.parent))))
    return content


def _vibe_board(paths: list[str], out_dir: Path) -> Path:
    """One mid-clip frame per matched short, so the caller can see the meme style."""
    thumbs = []
    for p in paths:
        try:
            info = ingest.probe(Path(p))
            im = ingest.extract_frame(Path(p), info["duration"] * 0.4)
            im.thumbnail((240, 240))
            thumbs.append(im)
        except Exception:
            logger.debug("no vibe frame for %s", p, exc_info=True)
            continue
    board = Image.new("RGB", (250 * max(1, len(thumbs)), 250), (20, 20, 20))
    for i, im in enumerate(thumbs):
        board.paste(im, (250 * i + (250 - im.width) // 2, (250 - im.height) // 2))
        ImageDraw.Draw(board).text((250 * i + 6, 4), f"#{i + 1}", fill=(255, 255, 0))
    out = out_dir / "meme_usage_vibe.jpg"
    board.save(out)
    return out
