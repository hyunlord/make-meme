"""Tests for make_meme.server tool functions.

The real make_meme.sources package is built by a separate agent, in
parallel; these tests install a small fake `make_meme.sources` module (via
sys.modules) for anything that needs search/fetch, so they stay deterministic
regardless of that package's progress.
"""

from __future__ import annotations

import json
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from mcp.types import ImageContent, TextContent

from make_meme import server


def _patch_sources(monkeypatch, fake: types.ModuleType) -> None:
    """Install ``fake`` as ``make_meme.sources`` for the duration of a test.

    ``from . import sources`` resolves via the ``make_meme`` package's own
    ``sources`` attribute before it ever consults ``sys.modules`` again, so
    once the real ``make_meme.sources`` has been imported anywhere in the
    process, patching ``sys.modules`` alone stops being enough -- the package
    attribute must be patched too.
    """

    import make_meme as make_meme_pkg

    monkeypatch.setitem(sys.modules, "make_meme.sources", fake)
    monkeypatch.setattr(make_meme_pkg, "sources", fake, raising=False)


def _json_payload(content):
    assert isinstance(content, list)
    return json.loads(content[0])


async def test_check_setup_reports_ffmpeg_and_comfyui():
    report = json.loads(await server.check_setup())
    assert report["ffmpeg"]["found"] is True
    assert report["ffprobe"]["found"] is True
    assert "comfyui" in report


async def test_load_media_from_local_video_path_registers_asset(video_with_audio):
    content = await server.load_media(str(video_with_audio))
    payload = _json_payload(content)
    assert payload["kind"] == "video"
    assert payload["id"].startswith("vid_")
    assert len(content) == 2  # json text + preview image


async def test_load_media_from_local_image_path_registers_asset(sample_image):
    content = await server.load_media(str(sample_image))
    payload = _json_payload(content)
    assert payload["kind"] == "image"
    assert payload["id"].startswith("img_")


async def test_load_media_trims_video_when_given_start_end(video_with_audio):
    content = await server.load_media(str(video_with_audio), start_sec=0.0, end_sec=1.0)
    payload = _json_payload(content)
    assert payload["meta"]["duration"] == pytest.approx(1.0, abs=0.15)
    assert payload["origin"]["trimmed_from"]


async def test_load_media_unknown_asset_id_raises_tool_error():
    with pytest.raises(server.ToolError):
        await server.load_media("vid_deadbeef")


async def test_load_media_refuses_path_in_hidden_directory(tmp_path):
    """Tool arguments can be steered by untrusted web content; a local path reaching into
    a hidden/config directory (~/.ssh-style) must be refused, not silently loaded."""

    from PIL import Image

    hidden_dir = tmp_path / ".secret"
    hidden_dir.mkdir()
    secret_file = hidden_dir / "x.png"
    Image.new("RGB", (10, 10)).save(secret_file)

    with pytest.raises(server.ToolError):
        await server.load_media(str(secret_file))


async def test_load_media_allows_a_normal_local_path(sample_image):
    # sample_image lives directly under pytest's tmp_path (not hidden, not a system
    # location) -- the safety check must not get in the way of ordinary use.
    content = await server.load_media(str(sample_image))
    assert _json_payload(content)["kind"] == "image"


async def test_inspect_media_on_video_returns_storyboard_and_segments(video_with_hard_cuts):
    content = await server.load_media(str(video_with_hard_cuts))
    asset_id = _json_payload(content)["id"]

    inspected = await server.inspect_media(asset_id, frames=4)
    payload = _json_payload(inspected)
    assert payload["id"] == asset_id
    assert "suggested_segments" in payload
    assert len(inspected) == 2


async def test_inspect_media_on_image_returns_meta_and_image(sample_image):
    content = await server.load_media(str(sample_image))
    asset_id = _json_payload(content)["id"]

    inspected = await server.inspect_media(asset_id)
    payload = _json_payload(inspected)
    assert payload["kind"] == "image"
    assert "suggested_segments" not in payload


async def test_inspect_media_unknown_asset_raises_tool_error():
    with pytest.raises(server.ToolError):
        await server.inspect_media("vid_deadbeef")


async def test_list_assets_reflects_loaded_media(video_no_audio, sample_image):
    await server.load_media(str(video_no_audio))
    await server.load_media(str(sample_image))

    all_assets = json.loads(await server.list_assets())
    assert len(all_assets) >= 2

    videos = json.loads(await server.list_assets(kind="video"))
    assert all(a["kind"] == "video" for a in videos)


async def test_job_tools_round_trip_through_job_manager():
    jobs = server.get_jobs()

    async def work(ctx):
        return {"output_path": "/tmp/fake.mp4"}

    job = jobs.submit("demo", work)
    await jobs.wait(job.id)

    content = await server.get_job(job.id)
    payload = _json_payload(content)
    assert payload["status"] == "succeeded"

    listed = json.loads(await server.list_jobs())
    assert any(j["id"] == job.id for j in listed)

    cancel_result = json.loads(await server.cancel_job(job.id))
    assert cancel_result["cancelled"] is False  # already finished, nothing to cancel


async def test_get_job_unknown_id_raises_tool_error():
    with pytest.raises(server.ToolError):
        await server.get_job("does-not-exist")


async def test_cancel_job_unknown_id_returns_false_not_an_error():
    result = json.loads(await server.cancel_job("does-not-exist"))
    assert result == {"cancelled": False}


def test_import_optional_tool_module_logs_error_not_silent(caplog):
    import logging

    with caplog.at_level(logging.ERROR, logger="make_meme.server"):
        server._import_optional_tool_module("make_meme._does_not_exist_xyz")
    assert any(
        r.levelno == logging.ERROR and "make_meme._does_not_exist_xyz" in r.message
        for r in caplog.records
    )
    assert caplog.records[-1].exc_info is not None


# --------------------------------------------------------------------------
# Real MCP call_tool() round trips: these go through FastMCP's own result
# conversion, which is what actually broke in production ("Unable to
# serialize unknown type: ...Image") when a tool returning list[Any] didn't
# disable structured_output -- direct function calls above don't exercise
# that path at all.
# --------------------------------------------------------------------------


async def test_load_media_via_call_tool_returns_image_for_video(video_with_audio):
    result = await server.mcp.call_tool("load_media", {"source": str(video_with_audio)})
    assert isinstance(result, list)
    assert isinstance(result[0], TextContent)
    assert json.loads(result[0].text)["kind"] == "video"
    assert any(isinstance(block, ImageContent) for block in result)


async def test_load_media_via_call_tool_returns_image_for_image(sample_image):
    result = await server.mcp.call_tool("load_media", {"source": str(sample_image)})
    assert isinstance(result, list)
    assert isinstance(result[0], TextContent)
    assert json.loads(result[0].text)["kind"] == "image"
    assert any(isinstance(block, ImageContent) for block in result)


async def test_inspect_media_via_call_tool_returns_image(video_with_hard_cuts):
    loaded = await server.mcp.call_tool("load_media", {"source": str(video_with_hard_cuts)})
    asset_id = json.loads(loaded[0].text)["id"]

    result = await server.mcp.call_tool("inspect_media", {"asset_id": asset_id})
    assert isinstance(result, list)
    assert isinstance(result[0], TextContent)
    assert any(isinstance(block, ImageContent) for block in result)


async def test_search_media_via_call_tool_returns_image(monkeypatch, video_with_audio):
    _install_fake_sources_module(monkeypatch, video_with_audio)
    result = await server.mcp.call_tool("search_media", {"query": "a shiba inu"})
    assert isinstance(result, list)
    assert isinstance(result[0], TextContent)
    assert any(isinstance(block, ImageContent) for block in result)


async def test_get_job_via_call_tool_returns_image_on_success(video_with_audio):
    loaded = await server.load_media(str(video_with_audio))
    preview_path = json.loads(loaded[0])["meta"]["preview_path"]

    jobs = server.get_jobs()

    async def work(ctx):
        return {"preview_path": preview_path}

    job = jobs.submit("demo", work)
    await jobs.wait(job.id)

    result = await server.mcp.call_tool("get_job", {"job_id": job.id})
    assert isinstance(result, list)
    assert isinstance(result[0], TextContent)
    assert any(isinstance(block, ImageContent) for block in result)


# --------------------------------------------------------------------------
# Fakes for the make_meme.sources contract (built separately; see module docstring)
# --------------------------------------------------------------------------


@dataclass
class _FakeCandidate:
    index: int
    kind: str
    url: str
    provider: str
    title: str | None = None
    thumbnail_url: str | None = None
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    license: str | None = None
    source_page: str | None = None


@dataclass
class _FakeFetchedMedia:
    path: Path
    kind: str
    provider: str
    source_url: str | None = None
    title: str | None = None
    uploader: str | None = None
    duration: float | None = None
    description: str | None = None
    subtitles_excerpt: str | None = None
    license: str | None = None
    extra: dict = field(default_factory=dict)


class _FakeSourceError(Exception):
    pass


def _install_fake_sources_module(monkeypatch, video_path: Path) -> types.ModuleType:
    fake = types.ModuleType("make_meme.sources")

    async def fake_search(query, kind="video", n=8, provider=None, license_safe=False):
        return [
            _FakeCandidate(
                index=1, kind=kind, url="https://example.com/video", provider="fake", title="Fake result"
            )
        ]

    async def fake_fetch(source, dest_dir):
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / "fetched.mp4"
        dest.write_bytes(video_path.read_bytes())
        return _FakeFetchedMedia(path=dest, kind="video", provider="fake", source_url=source, title="Fake video")

    async def fake_build_candidate_grid(candidates):
        from PIL import Image

        return Image.new("RGB", (64, 64), color="black")

    fake.search = fake_search
    fake.fetch = fake_fetch
    fake.build_candidate_grid = fake_build_candidate_grid
    fake.SourceError = _FakeSourceError
    fake.Candidate = _FakeCandidate
    fake.FetchedMedia = _FakeFetchedMedia

    _patch_sources(monkeypatch, fake)
    return fake


async def test_search_media_then_load_media_by_search_ref(monkeypatch, video_with_audio):
    _install_fake_sources_module(monkeypatch, video_with_audio)

    search_result = await server.search_media("a shiba inu", kind="video")
    payload = _json_payload(search_result)
    search_id = payload["search_id"]
    assert search_id
    assert len(search_result) == 2  # json text + grid image

    content = await server.load_media(f"{search_id}:1")
    loaded = _json_payload(content)
    assert loaded["kind"] == "video"
    assert loaded["origin"]["provider"] == "fake"


async def test_load_media_unknown_search_session_raises_tool_error():
    with pytest.raises(server.ToolError):
        await server.load_media("deadbeefcafe:1")


async def test_load_media_dedupes_by_url(monkeypatch, video_with_audio):
    fake = _install_fake_sources_module(monkeypatch, video_with_audio)
    fetch_calls: list[str] = []
    original_fetch = fake.fetch

    async def counting_fetch(source, dest_dir):
        fetch_calls.append(source)
        return await original_fetch(source, dest_dir)

    fake.fetch = counting_fetch

    url = "https://example.com/dedupe-me.mp4"
    first = await server.load_media(url)
    first_id = _json_payload(first)["id"]
    assert len(fetch_calls) == 1

    second = await server.load_media(url)
    second_id = _json_payload(second)["id"]
    assert len(fetch_calls) == 1, "a second load_media for the same URL must not re-fetch"
    assert second_id == first_id


async def test_load_media_copies_fetched_file_instead_of_moving_it(monkeypatch, video_with_audio):
    fake = _install_fake_sources_module(monkeypatch, video_with_audio)
    captured_paths: list[Path] = []
    original_fetch = fake.fetch

    async def capturing_fetch(source, dest_dir):
        media = await original_fetch(source, dest_dir)
        captured_paths.append(media.path)
        return media

    fake.fetch = capturing_fetch

    await server.load_media("https://example.com/copy-me.mp4")
    assert len(captured_paths) == 1
    # move=False: sources.fetch()'s own on-disk cache for this URL must survive so it can
    # still hit on a later call, even though we also now dedupe at the asset-store level.
    assert captured_paths[0].is_file()


async def test_search_media_propagates_source_error_as_tool_error(monkeypatch):
    fake = types.ModuleType("make_meme.sources")

    async def failing_search(*args, **kwargs):
        raise _FakeSourceError("provider is down")

    fake.search = failing_search
    fake.fetch = lambda *a, **k: None
    fake.build_candidate_grid = lambda *a, **k: None
    fake.SourceError = _FakeSourceError
    _patch_sources(monkeypatch, fake)

    with pytest.raises(server.ToolError):
        await server.search_media("anything")


async def test_load_media_fetch_failure_raises_tool_error_not_traceback(monkeypatch):
    fake = types.ModuleType("make_meme.sources")

    async def failing_fetch(source, dest_dir):
        raise _FakeSourceError(f"could not fetch {source}")

    fake.search = lambda *a, **k: []
    fake.fetch = failing_fetch
    fake.build_candidate_grid = lambda *a, **k: None
    fake.SourceError = _FakeSourceError
    _patch_sources(monkeypatch, fake)

    with pytest.raises(server.ToolError):
        await server.load_media("https://example.com/does-not-exist")


async def test_search_media_with_incomplete_sources_backend_raises_tool_error(monkeypatch):
    fake = types.ModuleType("make_meme.sources")  # missing all required attrs
    _patch_sources(monkeypatch, fake)

    with pytest.raises(server.ToolError):
        await server.search_media("anything")


async def test_load_media_refuses_hidden_dirs(tmp_path):
    from mcp.server.fastmcp.exceptions import ToolError
    from PIL import Image

    from make_meme import server

    secret = tmp_path / ".secret"
    secret.mkdir()
    Image.new("RGB", (8, 8)).save(secret / "x.png")
    with pytest.raises(ToolError, match="hidden directory"):
        await server.load_media(str(secret / "x.png"))
    Image.new("RGB", (8, 8)).save(tmp_path / "ok.png")
    out = await server.load_media(str(tmp_path / "ok.png"))
    assert "img_" in out[0]
