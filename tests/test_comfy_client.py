"""ComfyClient against a fake ComfyUI (httpx.MockTransport): completion, errors,
interruption, lost prompts, targeted cancel, auth header."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from make_meme.comfy.client import ComfyClient, ComfyError


class FakeComfy:
    def __init__(self, history_after: int = 1, entry: dict | None = None, queued: bool = True):
        self.calls: list[tuple[str, str, dict]] = []
        self.polls = 0
        self.history_after = history_after
        self.entry = entry if entry is not None else {
            "status": {"status_str": "success", "completed": True, "messages": []},
            "outputs": {"17": {"images": [{"filename": "a_00002_.png", "subfolder": "", "type": "output"},
                                          {"filename": "a_00001_.png", "subfolder": "", "type": "output"}]}},
        }
        self.queued = queued

    def handler(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content and request.method == "POST" else {}
        self.calls.append((request.method, request.url.path, body))
        path = request.url.path
        if path == "/prompt":
            return httpx.Response(200, json={"prompt_id": "p1"})
        if path.startswith("/history/"):
            self.polls += 1
            return httpx.Response(200, json={"p1": self.entry} if self.polls >= self.history_after else {})
        if path == "/queue" and request.method == "GET":
            items = [[0, "p1", {}, {}, []]] if self.queued else []
            return httpx.Response(200, json={"queue_running": items, "queue_pending": []})
        if path in ("/queue", "/interrupt"):
            return httpx.Response(200)
        return httpx.Response(404)


def _client(fake: FakeComfy, **kw) -> ComfyClient:
    return ComfyClient("http://comfy.test", transport=httpx.MockTransport(fake.handler), **kw)


async def test_run_success_and_front_flag():
    fake = FakeComfy(history_after=2)
    res = await _client(fake).run({"1": {}}, poll_interval=0, front=True)
    assert [o.filename for o in res.outputs] == ["a_00002_.png", "a_00001_.png"]
    prompt = next(c for c in fake.calls if c[1] == "/prompt")
    assert prompt[2]["front"] is True


async def test_execution_error_is_readable():
    fake = FakeComfy(entry={"status": {"status_str": "error", "completed": False, "messages": [
        ["execution_error", {"node_type": "WanVideoSampler", "node_id": "15", "exception_message": "OOM\n"}]]}})
    with pytest.raises(ComfyError, match="WanVideoSampler \\(node 15\\): OOM"):
        await _client(fake).run({}, poll_interval=0)


async def test_interrupted_prompt_raises_cancelled_not_error():
    fake = FakeComfy(entry={"status": {"status_str": "error", "completed": False, "messages": [
        ["execution_interrupted", {"prompt_id": "p1"}]]}})
    with pytest.raises(asyncio.CancelledError):
        await _client(fake).run({}, poll_interval=0)


async def test_lost_prompt_detected():
    fake = FakeComfy(history_after=10**9, queued=False)
    with pytest.raises(ComfyError, match="lost the job"):
        await _client(fake).run({}, poll_interval=0)


async def test_cancel_targets_only_our_prompt():
    fake = FakeComfy(history_after=10**9)
    ev = asyncio.Event()
    ev.set()
    with pytest.raises(asyncio.CancelledError):
        await _client(fake).run({}, poll_interval=0, cancelled=ev)
    posted = {c[1]: c[2] for c in fake.calls if c[0] == "POST"}
    assert posted["/queue"] == {"delete": ["p1"]}
    assert posted["/interrupt"] == {"prompt_id": "p1"}


async def test_timeout_cancels_and_raises():
    fake = FakeComfy(history_after=10**9)
    with pytest.raises(ComfyError, match="did not finish"):
        await _client(fake).run({}, poll_interval=0.01, timeout=0.05)
    assert any(c[1] == "/interrupt" for c in fake.calls)


async def test_connection_errors_become_comfy_errors():
    def boom(request):
        raise httpx.ConnectError("refused")

    c = ComfyClient("http://127.0.0.1:1", transport=httpx.MockTransport(boom))
    with pytest.raises(ComfyError, match="Is ComfyUI running"):
        await c.object_info()


async def test_token_header_sent():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"devices": []})

    await ComfyClient("http://x", token="s3cret", transport=httpx.MockTransport(handler)).system_stats()
    assert seen["auth"] == "Bearer s3cret"


async def test_run_recipe_drops_page_cache_only_on_unified_memory(monkeypatch, tmp_path):
    from make_meme.pipelines import runtime

    class Fake:
        def __init__(self, vram, ram):
            self.base_url = f"fake://{vram}-{ram}"
            self.dropped = 0
            self._stats = {"system": {"ram_total": ram}, "devices": [{"type": "cuda", "vram_total": vram}]}

        async def system_stats(self):
            return self._stats

        async def drop_cache(self):
            self.dropped += 1

        async def upload(self, path):
            return path.name

        async def run(self, workflow, **kw):
            return "ok"

    from make_meme.recipes.loader import get_recipe

    recipe = get_recipe("sam3_detect")
    spark, desktop = Fake(122 << 30, 122 << 30), Fake(24 << 30, 64 << 30)
    for client in (spark, desktop):
        await runtime.run_recipe(client, recipe, media={"image": tmp_path / "x.png"}, values={}, profile="cuda")
    assert spark.dropped == 1 and desktop.dropped == 0
