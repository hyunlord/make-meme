# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run through video_generate.py with the existing research Python.
"""Observe phase boundaries and original encoder calls without additional inference."""
from pathlib import Path
import json
import resource
import time


class StageCost:
    """Mutable accumulator for actual phase timing and host/CUDA observations."""

    def __init__(self, output: Path, torch_module) -> None:
        self.output = output
        self.torch = torch_module
        self.started = time.monotonic()
        self.events = []
        self.encoder_calls = []
        self.torch.cuda.reset_peak_memory_stats()

    def mark(self, phase: str) -> None:
        self.torch.cuda.synchronize()
        status = {}
        for line in Path('/proc/self/status').read_text().splitlines():
            if line.startswith(('VmRSS:', 'VmHWM:')):
                key, value = line.split(':', 1)
                status[key] = int(value.split()[0]) * 1024
        io = {}
        for line in Path('/proc/self/io').read_text().splitlines():
            key, value = line.split(':', 1)
            io[key] = int(value)
        self.events.append({'phase': phase, 'monotonic_seconds': time.monotonic(),
            'elapsed_seconds': time.monotonic() - self.started,
            'cuda_allocated_bytes': self.torch.cuda.memory_allocated(),
            'cuda_reserved_bytes': self.torch.cuda.memory_reserved(),
            'cuda_peak_allocated_bytes': self.torch.cuda.max_memory_allocated(),
            'cuda_peak_reserved_bytes': self.torch.cuda.max_memory_reserved(),
            'host': status, 'process_io': io})
        self.finish()

    def install_encoder_hooks(self, pipe) -> None:
        for owner, method, label in ((pipe.text_encoder, 'forward', 'text_encode'),
                                      (pipe.vae, 'encode', 'vae_condition_encode'),
                                      (pipe.vae, 'decode', 'vae_output_decode')):
            original = getattr(owner, method)
            def observed(*args, _original=original, _label=label, **kwargs):
                self.torch.cuda.synchronize()
                started = time.monotonic()
                result = _original(*args, **kwargs)
                self.torch.cuda.synchronize()
                self.encoder_calls.append({'operation': _label,
                    'elapsed_seconds': time.monotonic() - started})
                self.mark(_label + '_end')
                return result
            setattr(owner, method, observed)

    def finish(self) -> None:
        record = {'events': self.events, 'encoder_calls': self.encoder_calls,
            'host_maxrss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            'notes': 'CUDA synchronized only at phase/encoder boundaries. Process read_bytes is total actual process I/O, not isolated offload bytes. No extra forward or RNG call.',
            'isolated_offload_bytes': None}
        temporary = self.output / 'stage-cost.tmp'
        temporary.write_text(json.dumps(record, indent=2))
        temporary.replace(self.output / 'stage-cost.json')
