"""Async client for the ComfyUI HTTP/WebSocket API (local or remote)."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
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
    """HTTP/WebSocket client. All network failures surface as ComfyError.

    If COMFY_TOKEN is set (remote ComfyUI behind `make-meme comfy proxy`), it is sent as
    a bearer token on every request and on the progress WebSocket."""

    def __init__(
        self, base_url: str, timeout: float = 30.0, token: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.client_id = uuid.uuid4().hex
        self.token = token if token is not None else os.environ.get("COMFY_TOKEN") or None
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        self._http = httpx.AsyncClient(base_url=self.base_url, timeout=timeout, headers=headers, transport=transport)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def _request(self, method: str, url: str, **kw: Any) -> httpx.Response:
        try:
            r = await self._http.request(method, url, **kw)
        except httpx.HTTPError as e:
            raise ComfyError(
                f"ComfyUI request {method} {url} failed ({type(e).__name__}: {e}). Is ComfyUI running at "
                f"{self.base_url}? Start it with `make-meme comfy start` or set COMFY_URL."
            ) from e
        if r.status_code in (401, 403):
            raise ComfyError(f"ComfyUI at {self.base_url} rejected the request (HTTP {r.status_code}); check COMFY_TOKEN.")
        return r

    # ---- info -------------------------------------------------------------
    async def system_stats(self) -> dict[str, Any]:
        r = await self._request("GET", "/system_stats", timeout=5.0)
        if r.status_code != 200:
            raise ComfyError(f"ComfyUI at {self.base_url} answered HTTP {r.status_code} to /system_stats.")
        return r.json()

    async def object_info(self) -> dict[str, Any]:
        r = await self._request("GET", "/object_info", timeout=60.0)
        if r.status_code != 200:
            raise ComfyError(f"ComfyUI /object_info failed: HTTP {r.status_code}")
        return r.json()

    async def queue(self) -> dict[str, Any]:
        r = await self._request("GET", "/queue", timeout=10.0)
        return r.json() if r.status_code == 200 else {}

    # ---- files ------------------------------------------------------------
    async def upload(self, path: Path) -> str:
        """Upload any file (image, video, mask) into ComfyUI's input dir; returns the name
        to reference from LoadImage / LoadVideo widgets.

        Files go to the top level of the input dir (some loaders only list top-level
        files) under a content-hashed name, so re-uploads are idempotent and never clash."""
        digest = hashlib.sha1(path.read_bytes()).hexdigest()[:12]
        remote_name = f"mm_{digest}{path.suffix.lower()}"
        with path.open("rb") as fh:
            r = await self._request(
                "POST", "/upload/image",
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
        tmp = dest.with_name(dest.name + ".part")
        try:
            async with self._http.stream("GET", "/view", params=params, timeout=600.0) as r:
                if r.status_code != 200:
                    raise ComfyError(f"Downloading {out.filename} from ComfyUI failed: HTTP {r.status_code}")
                with tmp.open("wb") as fh:
                    async for chunk in r.aiter_bytes():
                        fh.write(chunk)
        except httpx.HTTPError as e:
            tmp.unlink(missing_ok=True)
            raise ComfyError(f"Downloading {out.filename} from ComfyUI failed ({type(e).__name__}: {e})") from e
        tmp.replace(dest)
        return dest

    # ---- execution --------------------------------------------------------
    async def submit(self, workflow: dict[str, Any], *, front: bool = False) -> str:
        body: dict[str, Any] = {"prompt": workflow, "client_id": self.client_id}
        if front:
            body["front"] = True
        r = await self._request("POST", "/prompt", json=body)
        if r.status_code != 200:
            raise ComfyError(_format_validation_error(r))
        return r.json()["prompt_id"]

    async def cancel(self, prompt_id: str) -> None:
        """Stop *our* prompt only: drop it from the queue if pending, interrupt it if running."""
        for method, url, body in (("POST", "/queue", {"delete": [prompt_id]}),
                                  ("POST", "/interrupt", {"prompt_id": prompt_id})):
            try:
                await self._request(method, url, json=body, timeout=5.0)
            except ComfyError:
                logger.warning("cancel request %s failed", url, exc_info=True)

    async def history(self, prompt_id: str) -> dict[str, Any] | None:
        r = await self._request("GET", f"/history/{prompt_id}")
        if r.status_code != 200:
            return None
        return r.json().get(prompt_id)

    async def _is_queued(self, prompt_id: str) -> bool:
        q = await self.queue()
        items = (q.get("queue_running") or []) + (q.get("queue_pending") or [])
        return any(len(item) > 1 and item[1] == prompt_id for item in items)

    async def run(
        self,
        workflow: dict[str, Any],
        *,
        on_progress: ProgressCallback | None = None,
        cancelled: asyncio.Event | None = None,
        stage: str = "generating",
        poll_interval: float = 2.0,
        progress_node: str | None = None,
        front: bool = False,
        timeout: float | None = None,
    ) -> ExecutionResult:
        """Submit a workflow and wait for completion, streaming progress when the
        WebSocket is available and falling back to polling /history otherwise.

        - `progress_node`: only report that node's step progress (other nodes, e.g. VAE
          encoding, report their own unrelated step counts).
        - `front`: jump the queue (quick jobs like detection shouldn't wait behind a
          long generation).
        - Raises ComfyError if the prompt disappears (ComfyUI restarted) or `timeout`
          seconds pass; asyncio.CancelledError if cancelled or interrupted."""
        prompt_id = await self.submit(workflow, front=front)
        logger.info("submitted prompt %s", prompt_id)
        ws_task = asyncio.create_task(self._watch_ws(prompt_id, on_progress, stage, progress_node))
        loop = asyncio.get_running_loop()
        deadline = None if timeout is None else loop.time() + timeout
        missing = 0
        try:
            while True:
                if cancelled is not None and cancelled.is_set():
                    await self.cancel(prompt_id)
                    raise asyncio.CancelledError
                entry = await self.history(prompt_id)
                if entry is not None and entry.get("status", {}).get("completed") is not None:
                    return _parse_history(prompt_id, entry)
                if entry is None and not await self._is_queued(prompt_id):
                    missing += 1  # tolerate the gap between finishing and appearing in history
                    if missing >= 3:
                        raise ComfyError("ComfyUI lost the job (was it restarted?). Please try again.")
                else:
                    missing = 0
                if deadline is not None and loop.time() > deadline:
                    await self.cancel(prompt_id)
                    raise ComfyError(f"ComfyUI did not finish within {timeout:.0f}s; the job was cancelled.")
                await asyncio.sleep(poll_interval)
        except asyncio.CancelledError:
            await asyncio.shield(self.cancel(prompt_id))
            raise
        finally:
            ws_task.cancel()

    async def _watch_ws(
        self, prompt_id: str, on_progress: ProgressCallback | None, stage: str, progress_node: str | None
    ) -> None:
        if on_progress is None:
            return
        url = self.base_url.replace("http", "ws", 1) + f"/ws?clientId={self.client_id}"
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else None
        try:
            async with websockets.connect(url, max_size=None, open_timeout=10, additional_headers=headers) as ws:
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
    if any(kind == "execution_interrupted" for kind, _ in status.get("messages", [])):
        raise asyncio.CancelledError
    if status.get("status_str") == "error":
        detail = "unknown error"
        for kind, payload in status.get("messages", []):
            if kind == "execution_error":
                detail = (
                    f"{payload.get('node_type')} (node {payload.get('node_id')}): "
                    f"{payload.get('exception_message', '').strip()[:500]}"
                )
        raise ComfyError(f"ComfyUI execution failed in {detail}")
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
