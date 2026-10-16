from __future__ import annotations

import pytest

from make_meme.sources.fetchers.ytdlp import YtDlpFetcher, map_ytdlp_error

FETCHER = YtDlpFetcher()


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "https://www.tiktok.com/@user/video/1234567890",
        "https://vm.tiktok.com/ZMabcdefg/",
        "https://www.instagram.com/reel/ABC123xyz/",
        "https://www.instagram.com/p/ABC123xyz/",
        "https://x.com/user/status/1234567890",
        "https://twitter.com/user/status/1234567890",
        "https://www.reddit.com/r/aww/comments/abc123/title/",
    ],
)
def test_can_handle_supported_sites(url):
    assert FETCHER.can_handle(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "https://www.threads.net/@user/post/ABC123",
        "https://www.threads.com/@user/post/ABC123",
        "https://example.com/some/random/page",
        "/local/file.mp4",
        "not a url",
    ],
)
def test_can_handle_rejects_unsupported(url):
    assert FETCHER.can_handle(url) is False


@pytest.mark.parametrize(
    "message,expected_fragment",
    [
        ("ERROR: [youtube] abc: Sign in to confirm your age", "MAKE_MEME_COOKIES_FROM_BROWSER"),
        (
            "ERROR: Private video. Sign in if you've been granted access",
            "MAKE_MEME_COOKIES_FROM_BROWSER",
        ),
        ("This video has been removed by the uploader", "removed"),
        ("ERROR: Video unavailable", "no longer available"),
        ("ERROR: This video is not available in your country (geo blocked)", "geo-blocked"),
        ("HTTP Error 429: Too Many Requests", "Rate-limited"),
        ("ERROR: some totally novel failure mode", "Could not download"),
    ],
)
def test_map_ytdlp_error_is_actionable(message, expected_fragment):
    assert expected_fragment.lower() in map_ytdlp_error(message).lower()
