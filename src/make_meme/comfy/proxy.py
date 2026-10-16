"""Token-checking reverse proxy for exposing a ComfyUI to the internet (e.g. from a free
Kaggle/Colab GPU through a Cloudflare quick tunnel). ComfyUI itself has no auth: anyone
with its URL can run workflows and read/write its input/output files.

    make-meme comfy proxy --upstream http://127.0.0.1:8188 --port 8189   # prints a token

Clients send `Authorization: Bearer <token>` (make-meme does this when COMFY_TOKEN is
set); a browser can use `?token=<token>` once, which sets a cookie.
Requires the optional dependency: pip install "make-meme-mcp[remote]".
"""

from __future__ import annotations

import asyncio
import hmac
import logging
import secrets

log = logging.getLogger("make_meme.proxy")

HOP_HEADERS = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers",
               "transfer-encoding", "upgrade", "host", "content-length", "authorization", "cookie"}
COOKIE = "make_meme_token"


def new_token() -> str:
    return secrets.token_urlsafe(24)


def build_app(upstream: str, token: str):
    from aiohttp import ClientSession, WSMsgType, web

    upstream = upstream.rstrip("/")

    def authorized(request) -> bool:
        supplied = ""
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            supplied = auth[7:]
        supplied = supplied or request.query.get("token", "") or request.cookies.get(COOKIE, "")
        return bool(supplied) and hmac.compare_digest(supplied, token)

    async def proxy(request):
        if not authorized(request):
            return web.Response(status=401, text="make-meme proxy: missing or wrong token\n")
        session: ClientSession = request.app["session"]
        query = [(k, v) for k, v in request.query.items() if k != "token"]
        url = upstream + request.path
        headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP_HEADERS}

        if request.headers.get("Upgrade", "").lower() == "websocket":
            client_ws = web.WebSocketResponse(max_msg_size=0)
            await client_ws.prepare(request)
            async with session.ws_connect(url.replace("http", "ws", 1), params=query, max_msg_size=0) as up:
                async def pump(src, dst):
                    async for msg in src:
                        if msg.type == WSMsgType.TEXT:
                            await dst.send_str(msg.data)
                        elif msg.type == WSMsgType.BINARY:
                            await dst.send_bytes(msg.data)
                        else:
                            break
                tasks = [asyncio.create_task(pump(client_ws, up)), asyncio.create_task(pump(up, client_ws))]
                await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for t in tasks:
                    t.cancel()
            return client_ws

        async with session.request(request.method, url, params=query, headers=headers,
                                   data=request.content if request.can_read_body else None,
                                   allow_redirects=False) as up:
            resp = web.StreamResponse(status=up.status, headers={
                k: v for k, v in up.headers.items() if k.lower() not in HOP_HEADERS})
            if request.query.get("token"):
                resp.set_cookie(COOKIE, token, httponly=True, secure=True, samesite="Strict")
            await resp.prepare(request)
            async for chunk in up.content.iter_chunked(1 << 16):
                await resp.write(chunk)
            await resp.write_eof()
            return resp

    async def on_startup(app):
        app["session"] = ClientSession()

    async def on_cleanup(app):
        await app["session"].close()

    app = web.Application(client_max_size=1 << 31)
    app.router.add_route("*", "/{tail:.*}", proxy)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app


def serve(upstream: str, port: int, token: str, host: str = "127.0.0.1") -> None:
    try:
        from aiohttp import web
    except ImportError as e:
        raise SystemExit('The proxy needs aiohttp: pip install "make-meme-mcp[remote]"') from e
    web.run_app(build_app(upstream, token), host=host, port=port, print=lambda *_: None)
