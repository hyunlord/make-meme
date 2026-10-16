from __future__ import annotations

from make_meme.sources.htmlmeta import find_video_tag_src, iter_json_blobs, parse_meta_tags, walk


def test_parse_meta_tags_attribute_order_agnostic():
    html = """
    <meta property="og:title" content="Title One">
    <meta content="Title Two" property="og:description">
    <meta name="twitter:player:stream" content="https://example.com/stream.mp4">
    <meta charset="utf-8">
    """
    meta = parse_meta_tags(html)
    assert meta["og:title"] == "Title One"
    assert meta["og:description"] == "Title Two"
    assert meta["twitter:player:stream"] == "https://example.com/stream.mp4"


def test_parse_meta_tags_first_value_wins():
    html = '<meta property="og:image" content="first.jpg"><meta property="og:image" content="second.jpg">'
    assert parse_meta_tags(html)["og:image"] == "first.jpg"


def test_parse_meta_tags_single_quotes():
    html = "<meta property='og:video' content='clip.mp4'>"
    assert parse_meta_tags(html)["og:video"] == "clip.mp4"


def test_parse_meta_tags_unescapes_html_entities():
    # Regression test: Instagram/Threads CDN URLs embed signed query strings containing
    # "&", which HTML attributes serialize as "&amp;". Leaving that unescaped corrupts
    # the signature and the CDN returns 403 on download (found via live testing).
    html = (
        '<meta property="og:image" '
        'content="https://cdn.example.com/x.jpg?a=1&amp;b=2&amp;sig=abc%3D%3D">'
    )
    assert (
        parse_meta_tags(html)["og:image"] == "https://cdn.example.com/x.jpg?a=1&b=2&sig=abc%3D%3D"
    )


def test_find_video_tag_src_unescapes_html_entities():
    html = '<video src="https://example.com/clip.mp4?a=1&amp;b=2"></video>'
    assert find_video_tag_src(html) == "https://example.com/clip.mp4?a=1&b=2"


def test_iter_json_blobs_skips_invalid_json():
    html = """
    <script type="application/json">{"valid": true}</script>
    <script type="application/json">not json at all</script>
    <script type="text/javascript">{"ignored": "wrong type"}</script>
    """
    blobs = list(iter_json_blobs(html))
    assert blobs == [{"valid": True}]


def test_walk_finds_nested_dicts_in_lists():
    data = {"a": [{"b": 1}, {"c": [{"d": 2}]}]}
    nodes = list(walk(data))
    assert {"b": 1} in nodes
    assert {"d": 2} in nodes
    assert data in nodes


def test_find_video_tag_src_prefers_video_src():
    html = '<video src="direct.mp4"><source src="fallback.mp4"></video>'
    assert find_video_tag_src(html) == "direct.mp4"


def test_find_video_tag_src_falls_back_to_source_tag():
    html = '<video controls><source src="fallback.mp4" type="video/mp4"></video>'
    assert find_video_tag_src(html) == "fallback.mp4"


def test_find_video_tag_src_none_when_absent():
    assert find_video_tag_src("<p>no video here</p>") is None
