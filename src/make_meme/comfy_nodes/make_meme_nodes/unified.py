"""Safety and compatibility for unified-memory NVIDIA GPUs (DGX Spark / GB10).

* Memory watchdog: GPU allocations there are system RAM that can't be swapped; running
  out froze a shared DGX Spark until it was rebooted. A thread checks MemAvailable every
  second and interrupts the running prompt (like the UI's Cancel) when it drops below
  MAKE_MEME_MIN_AVAILABLE_GB (default 6), so the job fails instead of the machine.
* sm_121: cuDNN 9.19 can't build attention plans for some shapes (SAM 3 tracking: "No
  valid execution plans built"). Such calls are retried without cuDNN (and that shape
  skips it from then on); everything else keeps ComfyUI's backend priority.
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


def sdpa_cudnn_fallback() -> bool:
    """On sm_121, retry an attention call without cuDNN when cuDNN can't build a plan for it
    (SAM 3's shapes), remembering the shape so later calls skip cuDNN directly. Other calls
    keep ComfyUI's backend priority, cuDNN first."""
    try:
        import torch

        if not (torch.cuda.is_available() and torch.cuda.get_device_capability(0) == (12, 1)):
            return False
        import comfy.ops  # type: ignore[import-not-found]
        from torch.nn.attention import SDPBackend
    except Exception:
        log.debug("cuDNN attention fallback not applicable", exc_info=True)
        return False
    original = getattr(comfy.ops, "scaled_dot_product_attention", None)
    if original is None or getattr(original, "_make_meme_wrapped", False):
        return False
    bad_shapes: set = set()

    def without_cudnn(q, k, v, *args, **kwargs):
        saved = comfy.ops.SDPA_BACKEND_PRIORITY
        comfy.ops.SDPA_BACKEND_PRIORITY = [b for b in saved if b != SDPBackend.CUDNN_ATTENTION]
        try:
            return original(q, k, v, *args, **kwargs)
        finally:
            comfy.ops.SDPA_BACKEND_PRIORITY = saved

    def sdpa(q, k, v, *args, **kwargs):
        key = (tuple(q.shape), tuple(k.shape), q.dtype)
        if key in bad_shapes:
            return without_cudnn(q, k, v, *args, **kwargs)
        try:
            return original(q, k, v, *args, **kwargs)
        except RuntimeError as e:
            if "cuDNN" not in str(e):
                raise
            bad_shapes.add(key)
            log.info("make-meme: cuDNN attention failed for %s; using another backend", key[0])
            return without_cudnn(q, k, v, *args, **kwargs)

    sdpa._make_meme_wrapped = True
    comfy.ops.scaled_dot_product_attention = sdpa
    log.info("make-meme: attention falls back from cuDNN when it can't plan a shape (sm_121)")
    return True
