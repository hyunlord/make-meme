# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Read-only phase observations, initialized once by the bounded runner."""
# Run by runtime_infer.py; no model construction here.
from __future__ import annotations
import json
import time
from pathlib import Path
import torch

_destination: Path | None = None
_started: float = 0

def initialize(destination: Path) -> None:
    global _destination, _started
    _destination = destination
    _started = time.monotonic()

def phase(name: str) -> None:
    """Append measured process/system/CUDA memory without synchronizing kernels."""
    if _destination is None:
        return
    status = Path('/proc/self/status').read_text().splitlines()
    record = {'phase':name,'epoch':time.time(),'elapsed_seconds':time.monotonic()-_started,
              'process_memory':[line for line in status if line.startswith(('VmRSS:','VmHWM:','RssAnon:','RssFile:'))],
              'mem_available':next(line for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')),
              'cuda_initialized':torch.cuda.is_initialized()}
    if torch.cuda.is_initialized():
        record.update(cuda_allocated=torch.cuda.memory_allocated(),cuda_reserved=torch.cuda.memory_reserved(),cuda_peak_allocated=torch.cuda.max_memory_allocated())
    with _destination.open('a') as stream:
        stream.write(json.dumps(record)+'\n')
