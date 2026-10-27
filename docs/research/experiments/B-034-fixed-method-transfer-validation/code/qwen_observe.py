# /// script
# requires-python = ">=3.12"
# dependencies = ["torch", "numpy", "safetensors"]
# ///
"""Small phase/counter observations; no persistent tensor references."""
# Run: imported by qwen_runner.py in the read-only package environment.
import hashlib
import json
import time
from pathlib import Path
from typing import Final
import torch

GIB: Final = 1024**3


def file_hash(path: Path) -> str:
    """Hash files incrementally without retaining weights in memory."""
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def tensor_hash(value: torch.Tensor) -> str:
    """Hash a temporary lossless CPU view; retain only its digest."""
    return hashlib.sha256(value.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()


def observe(root: Path, phase: str) -> None:
    """Separate system/cgroup/process/allocator accounts at a synchronized boundary."""
    if torch.cuda.is_initialized():
        torch.cuda.synchronize()
    memory = {line.split(':')[0]: int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemAvailable:', 'SwapTotal:', 'SwapFree:'))}
    rss = [line for line in Path('/proc/self/status').read_text().splitlines() if line.startswith(('VmRSS:', 'RssAnon:', 'RssFile:'))]
    cgroup = Path('/sys/fs/cgroup') / Path('/proc/self/cgroup').read_text().strip().split('::')[-1].lstrip('/')
    accounts = {name: (cgroup/name).read_text() for name in ('memory.current','memory.peak','memory.events','memory.stat') if (cgroup/name).exists()}
    cuda = {}
    if torch.cuda.is_initialized():
        cuda = {'allocated':torch.cuda.memory_allocated(), 'reserved':torch.cuda.memory_reserved(), 'peak_allocated':torch.cuda.max_memory_allocated(), 'peak_reserved':torch.cuda.max_memory_reserved()}
    with (root/'environment/reports/qwen-phases.jsonl').open('a') as stream:
        stream.write(json.dumps({'utc_epoch':time.time(),'phase':phase,'memory':memory,'rss':rss,'cgroup':accounts,'cuda':cuda})+'\n')
    assert memory['MemAvailable'] >= 24*GIB and memory['SwapTotal'] == memory['SwapFree'], 'Headroom/swap guard'


def tiny_cuda(root: Path) -> torch.Tensor:
    """Real non-random CUDA operation before any large CPU weights are read."""
    anchor = torch.tensor([1.,2.],dtype=torch.float32).to('cuda')
    output = anchor + 1
    torch.cuda.synchronize()
    assert output.cpu().tolist() == [2.,3.]
    observe(root,'tiny_cuda_copy_add_sync_readback')
    return anchor
