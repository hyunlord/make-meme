"""POST /make_meme/drop_cache: evict model files from the Linux page cache.

On unified-memory GPUs (DGX Spark / GB10) the page cache and GPU allocations share the
same RAM, and the CUDA driver doesn't reclaim cached file pages: after downloading or
loading ~60 GB of models, cudaMalloc (even creating a CUDA context) failed with "out of
memory" while `free` showed 110 GB "available". Dropping the whole cache needs root;
evicting files you can read doesn't (posix_fadvise DONTNEED), and model files are what
fills it. make-meme calls this before each run on such machines. No-op elsewhere.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

log = logging.getLogger("make_meme_nodes")


def drop_file_cache(roots: list[Path]) -> dict:
    files = size = 0
    if not hasattr(os, "posix_fadvise"):
        return {"files": 0, "bytes": 0, "supported": False}
    for root in roots:
        for path in Path(root).rglob("*"):
            try:
                if not path.is_file() or path.stat().st_size < 1 << 20:
                    continue
                fd = os.open(path, os.O_RDONLY)
                try:
                    os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
                finally:
                    os.close(fd)
                files += 1
                size += path.stat().st_size
            except OSError:
                log.debug("could not drop cache for %s", path, exc_info=True)
    return {"files": files, "bytes": size, "supported": True}


def _mem_free() -> int | None:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemFree:"):
                return int(line.split()[1]) * 1024
    except OSError:
        return None
    return None


def register_route() -> None:
    try:
        from aiohttp import web
        from server import PromptServer  # type: ignore[import-not-found]
    except ImportError:
        return

    @PromptServer.instance.routes.post("/make_meme/drop_cache")
    async def _make_meme_drop_cache(request):
        try:
            import folder_paths  # type: ignore[import-not-found]

            before = _mem_free()
            result = drop_file_cache([Path(folder_paths.models_dir)])
            result.update({"mem_free_before": before, "mem_free_after": _mem_free()})
            return web.json_response(result)
        except Exception:
            log.exception("failed to drop model file cache")
            return web.json_response({"error": "failed to drop cache"}, status=500)
