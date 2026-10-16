from __future__ import annotations

from pathlib import Path

import pytest

from make_meme.sources import dispatcher
from make_meme.sources.base import Registry
from make_meme.sources.models import FetchedMedia, SourceError


class FakeFetcher:
    def __init__(self, name, priority, *, handles=True, result=None, error=None, calls=None):
        self.name = name
        self.priority = priority
        self._handles = handles
        self._result = result
        self._error = error
        self.calls = calls if calls is not None else []

    def can_handle(self, source: str) -> bool:
        return self._handles(source) if callable(self._handles) else self._handles

    async def fetch(self, source: str, dest_dir: Path) -> FetchedMedia:
        self.calls.append(source)
        if self._error is not None:
            raise self._error
        return self._result


def _use_registry(monkeypatch, *fetchers):
    registry = Registry()
    for f in fetchers:
        registry.register_fetcher(f)
    monkeypatch.setattr(dispatcher, "get_registry", lambda: registry)
    return registry


@pytest.mark.asyncio
async def test_tries_fetchers_in_priority_order(monkeypatch, tmp_path):
    order = []

    class Tracking(FakeFetcher):
        async def fetch(self, source, dest_dir):
            order.append(self.name)
            return await super().fetch(source, dest_dir)

    media = FetchedMedia(path=tmp_path / "x.mp4", kind="video", provider="low", source_url="s")
    low = Tracking("low", priority=0, result=media)
    high = Tracking("high", priority=50, result=media)
    _use_registry(monkeypatch, high, low)  # registered out of order on purpose

    result = await dispatcher.fetch("https://example.com/v", tmp_path)
    assert order == ["low"]
    assert result is media


@pytest.mark.asyncio
async def test_falls_through_to_next_fetcher_on_failure(monkeypatch, tmp_path):
    media = FetchedMedia(path=tmp_path / "x.mp4", kind="video", provider="second", source_url="s")
    first = FakeFetcher("first", priority=0, error=SourceError("nope"))
    second = FakeFetcher("second", priority=10, result=media)
    _use_registry(monkeypatch, first, second)

    result = await dispatcher.fetch("https://example.com/v", tmp_path)
    assert result is media
    assert first.calls == ["https://example.com/v"]
    assert second.calls == ["https://example.com/v"]


@pytest.mark.asyncio
async def test_unexpected_exception_also_falls_through(monkeypatch, tmp_path):
    media = FetchedMedia(path=tmp_path / "x.mp4", kind="video", provider="second", source_url="s")
    first = FakeFetcher("first", priority=0, error=RuntimeError("boom"))
    second = FakeFetcher("second", priority=10, result=media)
    _use_registry(monkeypatch, first, second)

    result = await dispatcher.fetch("https://example.com/v", tmp_path)
    assert result is media


@pytest.mark.asyncio
async def test_aggregates_errors_when_all_fetchers_fail(monkeypatch, tmp_path):
    first = FakeFetcher("first", priority=0, error=SourceError("reason one"))
    second = FakeFetcher("second", priority=10, error=SourceError("reason two"))
    _use_registry(monkeypatch, first, second)

    with pytest.raises(SourceError) as excinfo:
        await dispatcher.fetch("https://example.com/v", tmp_path)
    assert "reason one" in str(excinfo.value)
    assert "reason two" in str(excinfo.value)


@pytest.mark.asyncio
async def test_no_fetcher_can_handle_raises_actionable_error(monkeypatch, tmp_path):
    _use_registry(monkeypatch, FakeFetcher("none", priority=0, handles=False))

    with pytest.raises(SourceError, match="Don't know how to fetch"):
        await dispatcher.fetch("weird://thing", tmp_path)


@pytest.mark.asyncio
async def test_can_handle_exception_is_treated_as_no_match(monkeypatch, tmp_path):
    def boom(source):
        raise RuntimeError("can_handle exploded")

    media = FetchedMedia(path=tmp_path / "x.mp4", kind="video", provider="good", source_url="s")
    broken = FakeFetcher("broken", priority=0, handles=boom)
    good = FakeFetcher("good", priority=10, result=media)
    _use_registry(monkeypatch, broken, good)

    result = await dispatcher.fetch("https://example.com/v", tmp_path)
    assert result is media


@pytest.mark.asyncio
async def test_caching_hit_skips_fetchers_entirely(monkeypatch, tmp_path):
    cached_file = tmp_path / "cached.mp4"
    cached_file.write_bytes(b"data")
    media = FetchedMedia(
        path=cached_file, kind="video", provider="fetcher", source_url="https://example.com/v"
    )
    fetcher = FakeFetcher("fetcher", priority=0, result=media)
    _use_registry(monkeypatch, fetcher)

    first = await dispatcher.fetch("https://example.com/v", tmp_path)
    assert first == media
    assert len(fetcher.calls) == 1

    second = await dispatcher.fetch("https://example.com/v", tmp_path)
    assert second == media
    assert len(fetcher.calls) == 1  # not called again -- served from the sidecar cache


@pytest.mark.asyncio
async def test_cache_ignored_if_underlying_file_was_removed(monkeypatch, tmp_path):
    cached_file = tmp_path / "cached.mp4"
    cached_file.write_bytes(b"data")
    media = FetchedMedia(
        path=cached_file, kind="video", provider="fetcher", source_url="https://example.com/v"
    )
    fetcher = FakeFetcher("fetcher", priority=0, result=media)
    _use_registry(monkeypatch, fetcher)

    await dispatcher.fetch("https://example.com/v", tmp_path)
    cached_file.unlink()

    await dispatcher.fetch("https://example.com/v", tmp_path)
    assert len(fetcher.calls) == 2


@pytest.mark.asyncio
async def test_local_path_handling_via_direct_fetcher(tmp_path):
    """Integration check with the real built-in registry: a plain local file path round-trips."""

    local_file = tmp_path / "clip.mp4"
    local_file.write_bytes(b"not really a video")
    media = await dispatcher.fetch(str(local_file), tmp_path / "dest")
    assert media.kind == "video"
    assert media.provider == "direct"
    assert media.path == local_file
    assert media.source_url is None


@pytest.mark.asyncio
async def test_local_path_missing_file_raises_actionable_error(tmp_path):
    with pytest.raises(SourceError):
        await dispatcher.fetch(str(tmp_path / "does-not-exist.mp4"), tmp_path / "dest")
