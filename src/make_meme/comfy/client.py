"""Async client for the ComfyUI HTTP/WebSocket API (local or remote)."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Self

import httpx
import websockets

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str, float, str], Awaitable[None]]
"""(stage, progress 0-1, message) -> None"""


class ComfyError(RuntimeError):
    """A ComfyUI request or execution failed; message is user-facing."""


@dataclass
class OutputFile:
    filename: str
    subfolder: str
    type: str  # "output" | "temp"
    node_id: str
    kind: str  # "images" | "gifs" | "videos" | ...


@dataclass
class ExecutionResult:
    prompt_id: str
    outputs: list[OutputFile] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


class ComfyClient:
    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.client_id = uuid.uuid4().hex
        self._http = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    # ---- info -------------------------------------------------------------
    async def system_stats(self) -> dict[str, Any]:
        try:
            r = await self._http.get("/system_stats", timeout=5.0)
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise ComfyError(
                f"ComfyUI is not reachable at {self.base_url} ({e.__class__.__name__}). "
                "Start it (`make-meme comfy start`) or set COMFY_URL to a running instance."
            ) from e
        return r.json()

    async def object_info(self) -> dict[str, Any]:
        r = await self._http.get("/object_info", timeout=60.0)
        r.raise_for_status()
        return r.json()

    # ---- files ------------------------------------------------------------
    async def upload(self, path: Path) -> str:
        """Upload any file (image, video, mask) into ComfyUI's input dir; returns the name
        to reference from LoadImage / LoadVideo widgets.

        Files go to the top level of the input dir (some loaders only list top-level
        files) under a content-hashed name, so re-uploads are idempotent and never clash."""
        digest = hashlib.sha1(path.read_bytes()).hexdigest()[:12]
        remote_name = f"mm_{digest}{path.suffix.lower()}"
        with path.open("rb") as fh:
            r = await self._http.post(
                "/upload/image",
                files={"image": (remote_name, fh, "application/octet-stream")},
                data={"overwrite": "true", "type": "input"},
                timeout=300.0,
            )
        if r.status_code != 200:
            raise ComfyError(f"Upload of {path.name} failed: HTTP {r.status_code} {r.text[:200]}")
        info = r.json()
        return f"{info['subfolder']}/{info['name']}" if info.get("subfolder") else info["name"]

    async def download(self, out: OutputFile, dest: Path) -> Path:
        params = {"filename": out.filename, "subfolder": out.subfolder, "type": out.type}
        dest.parent.mkdir(parents=True, exist_ok=True)
        async with self._http.stream("GET", "/view", params=params, timeout=600.0) as r:
            r.raise_for_status()
            with dest.open("wb") as fh:
                async for chunk in r.aiter_bytes():
                    fh.write(chunk)
        return dest

    # ---- execution --------------------------------------------------------
    async def submit(self, workflow: dict[str, Any]) -> str:
        r = await self._http.post("/prompt", json={"prompt": workflow, "client_id": self.client_id})
        if r.status_code != 200:
            raise ComfyError(_format_validation_error(r))
        return r.json()["prompt_id"]

    async def interrupt(self) -> None:
        try:
            await self._http.post("/interrupt", timeout=5.0)
        except httpx.HTTPError:
            logger.warning("interrupt request failed", exc_info=True)

    async def history(self, prompt_id: str) -> dict[str, Any] | None:
        r = await self._http.get(f"/history/{prompt_id}")
        r.raise_for_status()
        return r.json().get(prompt_id)

    async def run(
        self,
        workflow: dict[str, Any],
        *,
        on_progress: ProgressCallback | None = None,
        cancelled: asyncio.Event | None = None,
        stage: str = "generating",
        poll_interval: float = 2.0,
        progress_node: str | None = None,
    ) -> ExecutionResult:
        """Submit a workflow and wait for completion, streaming progress when the
        WebSocket is available and falling back to polling /history otherwise.

        If `progress_node` is given, only that node's step progress is reported (other
        nodes, e.g. VAE encoding, report their own unrelated step counts)."""
        prompt_id = await self.submit(workflow)
        logger.info("submitted prompt %s", prompt_id)
        ws_task = asyncio.create_task(self._watch_ws(prompt_id, on_progress, stage, progress_node))
        try:
            while True:
                if cancelled is not None and cancelled.is_set():
                    await self.interrupt()
                    raise asyncio.CancelledError
                entry = await self.history(prompt_id)
                if entry is not None and entry.get("status", {}).get("completed") is not None:
                    return _parse_history(prompt_id, entry)
                await asyncio.sleep(poll_interval)
        finally:
            ws_task.cancel()

    async def _watch_ws(
        self, prompt_id: str, on_progress: ProgressCallback | None, stage: str, progress_node: str | None
    ) -> None:
        if on_progress is None:
            return
        url = self.base_url.replace("http", "ws", 1) + f"/ws?clientId={self.client_id}"
        try:
            async with websockets.connect(url, max_size=None, open_timeout=10) as ws:
                async for raw in ws:
                    if not isinstance(raw, str):
                        continue  # binary preview frames
                    msg = json.loads(raw)
                    data = msg.get("data", {})
                    if data.get("prompt_id") not in (None, prompt_id):
                        continue
                    if msg.get("type") == "progress" and data.get("max"):
                        if progress_node is not None and str(data.get("node")) != progress_node:
                            continue
                        frac = data["value"] / data["max"]
                        await on_progress(stage, frac, f"step {data['value']}/{data['max']}")
                    elif msg.get("type") == "executing" and data.get("node"):
                        await on_progress(stage, -1.0, f"node {data['node']}")
        except asyncio.CancelledError:
            raise
        except Exception:  # progress is best-effort; polling still drives completion
            logger.debug("progress websocket unavailable", exc_info=True)


def _parse_history(prompt_id: str, entry: dict[str, Any]) -> ExecutionResult:
    status = entry.get("status", {})
    if status.get("status_str") == "error":
        detail = "unknown error"
        for kind, payload in status.get("messages", []):
            if kind == "execution_error":
                detail = (
                    f"{payload.get('node_type')} (node {payload.get('node_id')}): "
                    f"{payload.get('exception_message', '').strip()[:500]}"
                )
        raise ComfyError(f"ComfyUI execution failed in {detail}")
    if status.get("status_str") == "interrupted" or any(
        kind == "execution_interrupted" for kind, _ in status.get("messages", [])
    ):
        raise asyncio.CancelledError
    outputs: list[OutputFile] = []
    for node_id, node_out in entry.get("outputs", {}).items():
        for kind, items in node_out.items():
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, dict) and "filename" in item:
                    outputs.append(
                        OutputFile(
                            filename=item["filename"],
                            subfolder=item.get("subfolder", ""),
                            type=item.get("type", "output"),
                            node_id=node_id,
                            kind=kind,
                        )
                    )
    return ExecutionResult(prompt_id=prompt_id, outputs=outputs, raw=entry)


def _format_validation_error(r: httpx.Response) -> str:
    try:
        body = r.json()
    except ValueError:
        return f"ComfyUI rejected the workflow: HTTP {r.status_code} {r.text[:300]}"
    parts = [body.get("error", {}).get("message", "workflow rejected")]
    for node_id, err in (body.get("node_errors") or {}).items():
        for e in err.get("errors", []):
            parts.append(f"node {node_id} ({err.get('class_type')}): {e.get('message')} {e.get('details', '')}".strip())
    return "ComfyUI rejected the workflow: " + "; ".join(parts)[:1500]
