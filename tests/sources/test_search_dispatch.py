from __future__ import annotations

import importlib

import pytest

from make_meme.sources.base import Registry
from make_meme.sources.models import Candidate, SourceError

# NOTE: `make_meme.sources.__init__` does `from .search import search as search`, which
# rebinds the `search` *attribute* on the `make_meme.sources` package to the function --
# so `import make_meme.sources.search as x` (attribute-walk form) would actually hand back
# that function, not this subpackage. `importlib.import_module` goes through `sys.modules`
# instead and reliably returns the real module.
search_module = importlib.import_module("make_meme.sources.search")


class FakeProvider:
    def __init__(
        self,
        name,
        kinds,
        results=None,
        results_by_query=None,
        error=None,
        requires_key=None,
        license_safe=False,
        calls=None,
    ):
        self.name = name
        self.kinds = kinds
        self.license_safe = license_safe
        self.requires_key = requires_key
        self._results = results or []
        self._results_by_query = results_by_query
        self._error = error
        self.calls = calls if calls is not None else []

    async def search(self, query, kind, n):
        self.calls.append((query, kind, n))
        if self._error is not None:
            raise self._error
        if self._results_by_query is not None:
            return self._results_by_query.get(query, [])[:n]
        return self._results[:n]


def _candidate(url, kind="video", **kwargs):
    return Candidate(index=0, kind=kind, url=url, provider="x", **kwargs)


def _use_registry(monkeypatch, *providers):
    registry = Registry()
    for p in providers:
        registry.register_search_provider(p)
    monkeypatch.setattr(search_module, "get_registry", lambda: registry)
    return registry


@pytest.mark.asyncio
async def test_video_defaults_try_youtube_then_web_to_fill_n(monkeypatch):
    youtube = FakeProvider("youtube", {"video"}, results=[_candidate("https://yt/1")])
    web = FakeProvider(
        "web",
        {"video", "image"},
        results=[_candidate("https://web/1"), _candidate("https://web/2")],
    )
    _use_registry(monkeypatch, youtube, web)

    results = await search_module.search("newjeans", "video", n=3)
    assert [c.url for c in results] == ["https://yt/1", "https://web/1", "https://web/2"]
    assert youtube.calls == [("newjeans", "video", 3)]
    assert web.calls == [("newjeans", "video", 2)]


@pytest.mark.asyncio
async def test_dedupes_by_url_across_providers(monkeypatch):
    youtube = FakeProvider("youtube", {"video"}, results=[_candidate("https://dup/1")])
    web = FakeProvider(
        "web", {"video"}, results=[_candidate("https://dup/1"), _candidate("https://web/2")]
    )
    _use_registry(monkeypatch, youtube, web)

    results = await search_module.search("q", "video", n=5)
    assert [c.url for c in results] == ["https://dup/1", "https://web/2"]


@pytest.mark.asyncio
async def test_reindexes_1_through_n_in_final_order(monkeypatch):
    youtube = FakeProvider("youtube", {"video"}, results=[_candidate("a"), _candidate("b")])
    _use_registry(monkeypatch, youtube)

    results = await search_module.search("q", "video", n=5)
    assert [c.index for c in results] == [1, 2]


@pytest.mark.asyncio
async def test_image_license_safe_uses_openverse_only(monkeypatch):
    openverse = FakeProvider(
        "openverse",
        {"image"},
        results=[_candidate("https://ov/1", kind="image")],
        license_safe=True,
    )
    web = FakeProvider(
        "web", {"image", "video"}, results=[_candidate("https://web/1", kind="image")]
    )
    _use_registry(monkeypatch, openverse, web)

    results = await search_module.search("shiba inu", "image", n=5, license_safe=True)
    assert [c.url for c in results] == ["https://ov/1"]
    assert web.calls == []


@pytest.mark.asyncio
async def test_image_not_license_safe_prefers_web_falls_back_to_openverse_on_error(monkeypatch):
    web = FakeProvider("web", {"image", "video"}, error=SourceError("rate limited"))
    openverse = FakeProvider(
        "openverse", {"image"}, results=[_candidate("https://ov/1", kind="image")]
    )
    _use_registry(monkeypatch, web, openverse)

    results = await search_module.search("shiba inu", "image", n=5, license_safe=False)
    assert [c.url for c in results] == ["https://ov/1"]


@pytest.mark.asyncio
async def test_explicit_provider_forces_single_provider(monkeypatch):
    youtube = FakeProvider("youtube", {"video"}, results=[_candidate("https://yt/1")])
    web = FakeProvider("web", {"video"}, results=[_candidate("https://web/1")])
    _use_registry(monkeypatch, youtube, web)

    results = await search_module.search("q", "video", n=5, provider="web")
    assert [c.url for c in results] == ["https://web/1"]
    assert youtube.calls == []


@pytest.mark.asyncio
async def test_explicit_unknown_provider_raises(monkeypatch):
    _use_registry(monkeypatch, FakeProvider("web", {"video"}))
    with pytest.raises(SourceError, match="Unknown search provider"):
        await search_module.search("q", "video", provider="nope")


@pytest.mark.asyncio
async def test_explicit_provider_wrong_kind_raises(monkeypatch):
    _use_registry(monkeypatch, FakeProvider("openverse", {"image"}))
    with pytest.raises(SourceError, match="does not support"):
        await search_module.search("q", "video", provider="openverse")


@pytest.mark.asyncio
async def test_provider_requiring_missing_api_key_is_skipped(monkeypatch):
    keyed = FakeProvider(
        "keyed", {"video"}, results=[_candidate("https://keyed/1")], requires_key="SOME_API_KEY"
    )
    fallback = FakeProvider("fallback", {"video"}, results=[_candidate("https://fallback/1")])
    _use_registry(monkeypatch, keyed, fallback)
    monkeypatch.setattr(
        search_module, "_default_provider_names", lambda kind, license_safe: ["keyed", "fallback"]
    )
    monkeypatch.delenv("SOME_API_KEY", raising=False)

    results = await search_module.search("q", "video", n=5)
    assert [c.url for c in results] == ["https://fallback/1"]
    assert keyed.calls == []


@pytest.mark.asyncio
async def test_all_providers_failing_raises_source_error_with_hints(monkeypatch):
    web = FakeProvider("web", {"video"}, error=SourceError("down"))
    _use_registry(monkeypatch, web)
    monkeypatch.setattr(
        search_module, "_default_provider_names", lambda kind, license_safe: ["web"]
    )

    with pytest.raises(SourceError, match="down"):
        await search_module.search("q", "video")


@pytest.mark.asyncio
async def test_unsupported_kind_raises():
    with pytest.raises(SourceError, match="Unsupported search kind"):
        await search_module.search("q", "audio")


@pytest.mark.asyncio
async def test_n_zero_returns_empty_list():
    assert await search_module.search("q", "video", n=0) == []


def test_shorten_query_drops_last_word():
    assert search_module._shorten_query("a b c") == "a b"
    assert search_module._shorten_query("a b") == "a"


def test_shorten_query_gives_up_at_one_word():
    assert search_module._shorten_query("a") is None
    assert search_module._shorten_query("") is None


@pytest.mark.asyncio
async def test_zero_results_retries_with_progressively_shortened_query(monkeypatch):
    target = _candidate("https://ov/1", kind="image")
    provider = FakeProvider(
        "openverse",
        {"image"},
        license_safe=True,
        results_by_query={
            "shiba inu dog standing full body": [],
            "shiba inu dog standing full": [],
            "shiba inu dog standing": [],
            "shiba inu dog": [target],
        },
    )
    _use_registry(monkeypatch, provider)

    results = await search_module.search(
        "shiba inu dog standing full body", "image", n=5, license_safe=True
    )
    assert [c.url for c in results] == ["https://ov/1"]
    assert provider.calls == [
        ("shiba inu dog standing full body", "image", 5),
        ("shiba inu dog standing full", "image", 5),
        ("shiba inu dog standing", "image", 5),
        ("shiba inu dog", "image", 5),
    ]


@pytest.mark.asyncio
async def test_shortening_stops_at_one_word_and_raises_with_hint(monkeypatch):
    provider = FakeProvider("web", {"video"}, results_by_query={})  # always empty
    _use_registry(monkeypatch, provider)
    monkeypatch.setattr(
        search_module, "_default_provider_names", lambda kind, license_safe: ["web"]
    )

    with pytest.raises(SourceError, match="shorter or less specific"):
        await search_module.search("one two three", "video", n=5)

    assert provider.calls == [
        ("one two three", "video", 5),
        ("one two", "video", 5),
        ("one", "video", 5),
    ]


@pytest.mark.asyncio
async def test_provider_error_is_not_retried_with_shortened_query(monkeypatch):
    provider = FakeProvider("web", {"video"}, error=SourceError("rate limited"))
    _use_registry(monkeypatch, provider)
    monkeypatch.setattr(
        search_module, "_default_provider_names", lambda kind, license_safe: ["web"]
    )

    with pytest.raises(SourceError, match="rate limited"):
        await search_module.search("one two three", "video", n=5)

    # A real failure isn't a shortened-query problem -- only one call, no retries.
    assert provider.calls == [("one two three", "video", 5)]
