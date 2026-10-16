"""GET /make_meme/stats: a cheap read-only endpoint make_meme.perf polls for device/process
memory usage while a generation runs.

Importing this module must never fail outside ComfyUI (no ``aiohttp``, no ``server``
module available in a plain Python/test environment) -- :func:`register_route` guards
both imports and is a no-op when they're missing.
"""

from __future__ import annotations

import logging
import sys

log = logging.getLogger("make_meme_nodes")


def collect_stats() -> dict:
    """Best-effort device/process/system memory snapshot. Never raises; missing values are null."""

    stats: dict = {
        "device": None,
        "allocated_bytes": None,
        "driver_allocated_bytes": None,
        "max_allocated_bytes": None,
        "process_rss_bytes": None,
        "system_total_bytes": None,
        "system_available_bytes": None,
    }

    try:
        import torch

        if torch.backends.mps.is_available():
            stats["device"] = "mps"
            try:
                stats["allocated_bytes"] = int(torch.mps.current_allocated_memory())
            except Exception:
                log.debug("torch.mps.current_allocated_memory() failed", exc_info=True)
            try:
                stats["driver_allocated_bytes"] = int(torch.mps.driver_allocated_memory())
            except Exception:
                log.debug("torch.mps.driver_allocated_memory() failed", exc_info=True)
        elif torch.cuda.is_available():
            stats["device"] = "cuda"
            try:
                stats["allocated_bytes"] = int(torch.cuda.memory_allocated())
            except Exception:
                log.debug("torch.cuda.memory_allocated() failed", exc_info=True)
            try:
                stats["max_allocated_bytes"] = int(torch.cuda.max_memory_allocated())
            except Exception:
                log.debug("torch.cuda.max_memory_allocated() failed", exc_info=True)
        else:
            stats["device"] = "cpu"
    except Exception:
        log.debug("torch unavailable while collecting device stats", exc_info=True)

    try:
        import psutil

        stats["process_rss_bytes"] = int(psutil.Process().memory_info().rss)
        vm = psutil.virtual_memory()
        stats["system_total_bytes"] = int(vm.total)
        stats["system_available_bytes"] = int(vm.available)
    except Exception:
        log.debug("psutil unavailable; falling back to resource.getrusage", exc_info=True)
        try:
            import resource

            usage = resource.getrusage(resource.RUSAGE_SELF)
            # ru_maxrss is bytes on macOS, KiB on Linux.
            scale = 1 if sys.platform == "darwin" else 1024
            stats["process_rss_bytes"] = int(usage.ru_maxrss) * scale
        except Exception:
            log.debug("resource.getrusage also failed; process_rss_bytes stays null", exc_info=True)

    return stats


def register_route() -> None:
    """Register ``GET /make_meme/stats`` on ComfyUI's PromptServer, if running inside it.

    No-ops (does not raise) when ``aiohttp``/``server`` aren't importable, which is the
    case for every environment except an actual ComfyUI process.
    """

    try:
        from aiohttp import web
        from server import PromptServer  # type: ignore[import-not-found]
    except ImportError:
        return

    @PromptServer.instance.routes.get("/make_meme/stats")
    async def _make_meme_stats(request):
        try:
            return web.json_response(collect_stats())
        except Exception:
            log.exception("failed to collect make-meme stats")
            return web.json_response({"error": "failed to collect stats"}, status=500)
