"""Safety and compatibility for unified-memory NVIDIA GPUs (DGX Spark / GB10).

* Memory watchdog: GPU allocations there are system RAM that can't be swapped; running
  out froze a shared DGX Spark until it was rebooted. A thread checks MemAvailable every
  second and interrupts the running prompt (like the UI's Cancel) when it drops below
  MAKE_MEME_MIN_AVAILABLE_GB (default 6), so the job fails instead of the machine.
* SAM 3 on sm_121: cuDNN 9.19 can't build attention plans for SAM 3's shapes ("No valid
  execution plans built"). Only while a SAM 3 node runs, cuDNN is dropped from ComfyUI's
  SDPA backend priority; other models keep their fastest backend.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path

log = logging.getLogger("make_meme_nodes")


def mem_available_bytes() -> int | None:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except OSError:
        return None
    return None


def is_unified_cuda() -> bool:
    try:
        import torch

        if not torch.cuda.is_available():
            return False
        total = torch.cuda.get_device_properties(0).total_memory
        ram = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
        return abs(total - ram) / ram < 0.05
    except Exception:
        log.debug("could not tell whether the GPU uses unified memory", exc_info=True)
        return False


def _watch(min_bytes: int, interval: float) -> None:
    import comfy.model_management as mm  # type: ignore[import-not-found]

    tripped_at = 0.0
    while True:
        time.sleep(interval)
        avail = mem_available_bytes()
        if avail is None or avail >= min_bytes or time.time() - tripped_at < 10:
            continue
        tripped_at = time.time()
        log.error("make-meme: only %.1f GB memory left on a unified-memory GPU; interrupting the running "
                  "prompt to keep the machine responsive", avail / 2**30)
        mm.interrupt_current_processing(True)


def start_memory_watchdog() -> bool:
    if not is_unified_cuda():
        return False
    min_gb = float(os.environ.get("MAKE_MEME_MIN_AVAILABLE_GB", "6"))
    threading.Thread(target=_watch, args=(int(min_gb * 2**30), 1.0), daemon=True,
                     name="make-meme-memory-watchdog").start()
    log.info("make-meme: unified-memory watchdog on (interrupts below %.0f GB available)", min_gb)
    return True


def sam3_without_cudnn() -> bool:
    """Wrap SAM 3 nodes so cuDNN attention is skipped only while they run (sm_121)."""
    try:
        import torch

        if not (torch.cuda.is_available() and torch.cuda.get_device_capability(0) == (12, 1)):
            return False
        import comfy.ops  # type: ignore[import-not-found]
        from comfy_extras import nodes_sam3  # type: ignore[import-not-found]
        from torch.nn.attention import SDPBackend
    except Exception:
        log.debug("SAM 3 cuDNN workaround not applicable", exc_info=True)
        return False

    def wrap(cls) -> None:
        original = cls.__dict__.get("execute")
        if original is None or getattr(original, "_make_meme_wrapped", False):
            return
        func = original.__func__ if isinstance(original, classmethod) else original

        def execute(klass, *args, **kwargs):
            saved = getattr(comfy.ops, "SDPA_BACKEND_PRIORITY", None)
            if saved:
                comfy.ops.SDPA_BACKEND_PRIORITY = [b for b in saved if b != SDPBackend.CUDNN_ATTENTION]
            try:
                return func(klass, *args, **kwargs)
            finally:
                if saved:
                    comfy.ops.SDPA_BACKEND_PRIORITY = saved

        execute._make_meme_wrapped = True
        cls.execute = classmethod(execute)

    wrapped = 0
    for name in dir(nodes_sam3):
        obj = getattr(nodes_sam3, name)
        if isinstance(obj, type) and name.startswith("SAM3_") and "execute" in obj.__dict__:
            wrap(obj)
            wrapped += 1
    log.info("make-meme: SAM 3 nodes skip cuDNN attention on sm_121 (%d wrapped)", wrapped)
    return wrapped > 0
