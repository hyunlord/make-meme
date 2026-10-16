"""SSRF protection for outgoing requests triggered by untrusted URLs.

``source`` strings and search-candidate URLs handled by this package can
originate from untrusted content -- a page scraped by the generic/threads
fetchers, a search result, or text an LLM was tricked into treating as a
"link to fetch" (prompt injection). Without validation, a crafted URL could
make this process fetch ``http://127.0.0.1:8188`` (the local ComfyUI
server), ``http://169.254.169.254/`` (cloud instance metadata), or any other
loopback/private/link-local host, and the response would then be treated as
ordinary fetched media or thumbnail data.

Every outgoing ``httpx`` request anywhere in ``make_meme.sources`` should be
made through :func:`safe_client` (instead of constructing
``httpx.AsyncClient`` directly) together with :func:`safe_get` /
:func:`safe_stream` (instead of ``client.get``/``client.stream``). Those
re-validate every redirect hop -- ``httpx`` auto-following redirects would
otherwise bypass the check entirely, since only the *original* URL would
ever be validated. ``safe_client`` forces ``follow_redirects=False`` as a
fail-safe even for code that forgets to use ``safe_get``/``safe_stream``: a
plain ``client.get()`` on such a client just returns the redirect response
unfollowed (a confusing downstream error) rather than silently fetching
whatever a redirect points at.

Set ``MAKE_MEME_ALLOW_PRIVATE_URLS=1`` to disable the private/local-address
block entirely -- e.g. for self-hosters who intentionally point make-meme's
*own* fetchers at an internal media server. This only affects
``make_meme.sources``; it has no effect on the ComfyUI client, which talks
to a operator-configured, trusted ``COMFY_URL`` and lives outside this
package.

Known limitation: yt-dlp follows its own redirects internally once handed a
URL, so only the initial URL passed to it is validated here (see
``fetchers/ytdlp.py``) -- a malicious *redirect target* reached via yt-dlp's
own extractor logic is not re-checked. This mirrors the yt-dlp fetcher's
pre-existing trust boundary (it already executes arbitrary extractor code
for the given URL) and was accepted as a reasonable scope boundary rather
than vendoring yt-dlp's networking.
"""

from __future__ import annotations

import contextlib
import ipaddress
import logging
import os
import socket
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urlparse

import httpx

from .models import SourceError

logger = logging.getLogger(__name__)

ALLOWED_SCHEMES = {"http", "https"}
MAX_REDIRECTS = 5

# Ranges IANA special-purpose registries list but Python's ipaddress.*.is_private
# (etc.) may not cover on every version; checked in addition to the stdlib flags.
_EXTRA_BLOCKED_NETWORKS = (
    ipaddress.ip_network("100.64.0.0/10"),  # CGNAT shared address space (RFC 6598)
    ipaddress.ip_network("192.0.0.0/24"),  # IETF protocol assignments
    ipaddress.ip_network("192.0.2.0/24"),  # TEST-NET-1
    ipaddress.ip_network("198.18.0.0/15"),  # benchmarking
    ipaddress.ip_network("198.51.100.0/24"),  # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),  # TEST-NET-3
    ipaddress.ip_network("2001:db8::/32"),  # documentation
)

IpAddress = ipaddress.IPv4Address | ipaddress.IPv6Address


def allow_private_urls() -> bool:
    """Read ``MAKE_MEME_ALLOW_PRIVATE_URLS`` fresh on every call (tests monkeypatch it)."""

    return os.environ.get("MAKE_MEME_ALLOW_PRIVATE_URLS") == "1"


def _unwrap_ipv4_mapped(ip: IpAddress) -> IpAddress:
    """Unwrap an IPv4-mapped IPv6 address (``::ffff:a.b.c.d``) to its embedded IPv4Address."""

    if isinstance(ip, ipaddress.IPv6Address):
        mapped = ip.ipv4_mapped
        if mapped is not None:
            return mapped
    return ip


def is_blocked_address(ip: IpAddress) -> bool:
    """True if ``ip`` is loopback, private, link-local, multicast, reserved, unspecified, etc."""

    ip = _unwrap_ipv4_mapped(ip)
    if (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return True
    return any(ip.version == net.version and ip in net for net in _EXTRA_BLOCKED_NETWORKS)


def _resolve_all(host: str) -> list[IpAddress]:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise SourceError(f"Could not resolve host {host!r}: {e}") from e
    addresses: list[IpAddress] = []
    for info in infos:
        raw_ip = info[4][0]
        try:
            addresses.append(ipaddress.ip_address(raw_ip))
        except ValueError:
            continue
    if not addresses:
        raise SourceError(
            f"Could not resolve host {host!r}: name resolution returned no addresses."
        )
    return addresses


def validate_url(url: str) -> None:
    """Raise :class:`SourceError` if ``url`` must not be fetched.

    Checks the scheme (http/https only) and every address the host resolves
    to (or the literal address itself, for a bare-IP URL) against the
    loopback/private/link-local/etc. ranges. A no-op when
    ``MAKE_MEME_ALLOW_PRIVATE_URLS=1`` is set.
    """

    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise SourceError(f"Refusing to fetch {url!r}: unsupported URL scheme {parsed.scheme!r}.")
    host = parsed.hostname
    if not host:
        raise SourceError(f"Refusing to fetch {url!r}: no host in URL.")

    if allow_private_urls():
        return

    try:
        addresses: list[IpAddress] = [ipaddress.ip_address(host)]
    except ValueError:
        addresses = _resolve_all(host)

    for addr in addresses:
        if is_blocked_address(addr):
            raise SourceError(
                f"Refusing to fetch {host}: it resolves to a private/local address ({addr}) "
                "(set MAKE_MEME_ALLOW_PRIVATE_URLS=1 if this is intentional)."
            )


def safe_client(**kwargs: Any) -> httpx.AsyncClient:
    """Build an ``httpx.AsyncClient`` that never auto-follows redirects.

    Always pair with :func:`safe_get`/:func:`safe_stream`, which re-validate
    each redirect hop before following it -- letting ``httpx`` auto-follow
    (``follow_redirects=True``) would validate only the first URL and then
    silently fetch wherever a redirect points.
    """

    kwargs["follow_redirects"] = False
    return httpx.AsyncClient(**kwargs)


async def safe_get(client: httpx.AsyncClient, url: str, **kwargs: Any) -> httpx.Response:
    """Like ``client.get(url)``, but validates ``url`` and every redirect hop (up to
    :data:`MAX_REDIRECTS`) before following it.
    """

    current_url = url
    hops = 0
    while True:
        validate_url(current_url)
        response = await client.get(current_url, **kwargs)
        if response.is_redirect:
            location = response.headers.get("location")
            if not location:
                return response
            hops += 1
            if hops > MAX_REDIRECTS:
                raise SourceError(f"Too many redirects (>{MAX_REDIRECTS}) fetching {url!r}.")
            current_url = str(response.url.join(location))
            continue
        return response


@contextlib.asynccontextmanager
async def safe_stream(
    client: httpx.AsyncClient, method: str, url: str, **kwargs: Any
) -> AsyncIterator[httpx.Response]:
    """Like ``client.stream(method, url)``, but validates ``url`` and every redirect hop.

    Intermediate redirect responses are read and closed immediately (their
    bodies are typically empty or tiny); only the final, non-redirect
    response is yielded with its body left unread for the caller to stream.
    """

    current_url = url
    hops = 0
    while True:
        validate_url(current_url)
        request = client.build_request(method, current_url, **kwargs)
        response = await client.send(request, stream=True)
        if response.is_redirect:
            location = response.headers.get("location")
            await response.aclose()
            if not location:
                raise SourceError(f"Redirect from {current_url!r} had no Location header.")
            hops += 1
            if hops > MAX_REDIRECTS:
                raise SourceError(f"Too many redirects (>{MAX_REDIRECTS}) fetching {url!r}.")
            current_url = str(response.url.join(location))
            continue
        try:
            yield response
        finally:
            await response.aclose()
        return
