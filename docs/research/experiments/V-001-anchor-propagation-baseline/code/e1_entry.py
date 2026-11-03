"""Run the pinned official IC-LoRA CLI with observational V-001 accounting.

The probe retains the full sigma grid and exits only after the first Euler
update, at entry to the next denoiser call. No second forward or decode occurs.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import resource
import subprocess
import sys
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import torch
    from ltx_core.model.transformer import X0Model
    from ltx_core.types import LatentState
    from ltx_pipelines.utils.types import DenoisedLatentResult, Denoiser, VideoAudio


class ProbeComplete(Exception):
    """Expected exit after one completed step, before the second forward."""


PROMPT = (
    "Two dogs dancing in the same room: a large black Labrador Retriever and a "
    "slender grey Italian Greyhound. Keep their identities, body sizes and the "
    "original background. Stable camera."
)


@dataclass(frozen=True, slots=True)
class EntryConfig:
    mode: str
    receipt: Path
    official_args: list[str]
    output: Path


def validate_config(path: Path) -> EntryConfig:
    data = json.loads(path.read_text())
    if set(data) != {"mode", "receipt", "official_args", "output"}:
        message = "Expected exactly mode, receipt, official_args, output"
        raise ValueError(message)
    config = EntryConfig(data["mode"], Path(data["receipt"]), data["official_args"], Path(data["output"]))
    if config.mode not in ("probe", "generate"):
        message = "Unapproved mode"
        raise ValueError(message)
    parser = argparse.ArgumentParser(add_help=False)
    for name in ("distilled-checkpoint-path", "spatial-upsampler-path", "gemma-root",
                 "height", "width", "num-frames", "frame-rate", "seed", "prompt", "output-path"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--lora", nargs=2, required=True)
    parser.add_argument("--video-conditioning", nargs=2, required=True)
    parser.add_argument("--image", nargs=3, required=True)
    flags = [value for value in config.official_args if value.startswith("--")]
    if len(flags) != len(set(flags)):
        message = "Repeated official options are forbidden"
        raise ValueError(message)
    values = parser.parse_args(config.official_args)
    if (values.height, values.width, values.frame_rate) != ("576", "1024", "24"):
        message = "E1 must use 1024x576 at 24fps"
        raise ValueError(message)
    if values.num_frames not in ("49", "73") or values.seed not in ("20261103", "20261104"):
        message = "Unapproved frame count or seed"
        raise ValueError(message)
    if config.mode == "probe" and (values.num_frames, values.seed) != ("73", "20261103"):
        message = "The sole E1 probe uses 73 frames and first seed"
        raise ValueError(message)
    if values.prompt != PROMPT or values.lora[1] != "1.0" or values.video_conditioning[1] != "1.0":
        message = "Prompt or conditioning strength changed"
        raise ValueError(message)
    if values.image[1:] != ["0", "1.0"] or Path(values.output_path) != config.output:
        message = "Anchor frame/strength or declared output mismatch"
        raise ValueError(message)
    for output in (config.receipt, config.output):
        if not output.is_absolute() or output.exists() or not output.parent.is_dir():
            message = "Output/receipt must be new absolute paths with existing parents"
            raise ValueError(message)
    files = [values.distilled_checkpoint_path, values.spatial_upsampler_path,
             values.lora[0], values.video_conditioning[0], values.image[0]]
    for filename in files:
        item = Path(filename)
        if not item.is_absolute() or not item.is_file() or item.stat().st_size == 0:
            raise FileNotFoundError(filename)
    gemma = Path(values.gemma_root)
    if not gemma.is_absolute() or not gemma.is_dir():
        raise FileNotFoundError(values.gemma_root)
    index_path = gemma / "model.safetensors.index.json"
    shards = set(json.loads(index_path.read_text())["weight_map"].values())
    for filename in ["config.json", "tokenizer.json", "tokenizer_config.json", *shards]:
        if not (gemma / filename).is_file():
            raise FileNotFoundError(filename)
    for filename, is_depth in ((values.image[0], False), (values.video_conditioning[0], True)):
        completed = subprocess.run(
            ["/usr/bin/ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
             "-show_entries", "stream=width,height,nb_read_frames,r_frame_rate", "-of", "json", filename],
            check=True, capture_output=True, text=True,
        )
        info = json.loads(completed.stdout)["streams"][0]
        if (info["width"], info["height"]) != (1024, 576):
            message = "Anchor and depth input dimensions must be 1024x576"
            raise ValueError(message)
        if is_depth:
            count = int(info["nb_read_frames"])
            numerator, denominator = map(int, info["r_frame_rate"].split("/"))
            if count not in (49, 73) or count < int(values.num_frames) or numerator != 24 * denominator:
                message = "Depth must contain the requested 49/73-frame prefix at 24fps"
                raise ValueError(message)
    return config


@dataclass(slots=True)  # Mutable execution accounting only.
class StepAccounting:
    probe: bool
    synchronize: Callable[[], None]
    now: Callable[[], float] = time.monotonic
    calls: int = 0
    completed: int = 0
    first_started: float | None = None
    first_seconds: float | None = None

    def before_step(self, step_index: int) -> None:
        if step_index > 0:
            self.completed += 1
        if self.calls == 1:
            self.synchronize()
            if self.first_started is None:
                message = "First-step timer was not started"
                raise RuntimeError(message)
            self.first_seconds = self.now() - self.first_started
            if self.probe:
                raise ProbeComplete
        if self.calls == 0:
            self.synchronize()
            self.first_started = self.now()
        self.calls += 1

    def finish_stage(self) -> None:
        self.synchronize()
        self.completed += 1


@dataclass(slots=True)
class RunReceipt:
    mode: str
    status: str = "STARTED"
    command: list[str] = field(default_factory=list)
    grids: list[list[float]] = field(default_factory=list)
    elapsed_seconds: float | None = None
    first_step_seconds: float | None = None
    denoiser_calls: int = 0
    scheduler_steps_completed: int = 0
    peak_rss_kib: int = 0
    cuda_peak_allocated_bytes: int = 0
    cuda_peak_reserved_bytes: int = 0
    estimate_73_linear_stage2_seconds: float | None = None
    estimate_73_quadratic_stage2_seconds: float | None = None
    estimate_49_conservative_seconds: float | None = None
    estimate_excludes_unmeasured_decode: bool = True


def write_receipt(path: Path, receipt: RunReceipt) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(asdict(receipt), indent=2) + "\n")
    temporary.replace(path)


def install_observer(accounting: StepAccounting, receipt: RunReceipt) -> Callable[[], None]:
    from ltx_pipelines.utils.blocks import diffusion_stage
    from ltx_pipelines.utils.denoisers import SimpleDenoiser

    original = diffusion_stage.euler_denoising_loop

    def observed_loop(
        sigmas: torch.Tensor,
        video_state: LatentState | None,
        audio_state: LatentState | None,
        transformer: X0Model,
        denoiser: Denoiser,
    ) -> VideoAudio[LatentState]:
        if not isinstance(denoiser, SimpleDenoiser):
            message = "Expected the official distilled SimpleDenoiser"
            raise RuntimeError(message)
        receipt.grids.append(sigmas.detach().cpu().tolist())

        def observed_denoiser(
            model: X0Model,
            video: LatentState | None,
            audio: LatentState | None,
            grid: torch.Tensor,
            step_index: int,
        ) -> VideoAudio[DenoisedLatentResult]:
            accounting.before_step(step_index)
            return denoiser(model, video, audio, grid, step_index)

        result = original(
            sigmas=sigmas, video_state=video_state, audio_state=audio_state,
            transformer=transformer, denoiser=observed_denoiser,
        )
        accounting.finish_stage()
        return result

    diffusion_stage.euler_denoising_loop = observed_loop

    def restore() -> None:
        diffusion_stage.euler_denoising_loop = original

    return restore


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--cpu-only", action="store_true")
    args = parser.parse_args()
    config = validate_config(args.config)
    if args.cpu_only:
        if "torch" in sys.modules or "ltx_pipelines" in sys.modules:
            message = "CPU validation imported model packages"
            raise RuntimeError(message)
        print(json.dumps({"status": "CPU_VALIDATED", "torch_imported": False, "mode": config.mode}))
        return
    receipt = RunReceipt(mode=config.mode, command=config.official_args)
    write_receipt(config.receipt, receipt)
    started = time.monotonic()
    import torch
    from ltx_pipelines import ic_lora

    accounting = StepAccounting(config.mode == "probe", torch.cuda.synchronize)
    restore = install_observer(accounting, receipt)
    previous_argv = sys.argv
    sys.argv = ["ltx_pipelines.ic_lora", *config.official_args]
    receipt.status = "FAILED"
    try:
        ic_lora.main()
        if config.mode == "probe":
            message = "Probe unexpectedly reached generation completion"
            raise RuntimeError(message)
        if accounting.calls != 11 or accounting.completed != 11 or [len(grid) for grid in receipt.grids] != [9, 4]:
            message = "Generation did not complete the official 8+3 steps"
            raise RuntimeError(message)
        if not config.output.is_file() or config.output.stat().st_size == 0:
            message = "Official generation output is absent or empty"
            raise RuntimeError(message)
        receipt.status = "GENERATED"
    except ProbeComplete:
        if config.mode != "probe" or accounting.calls != 1 or accounting.completed != 1:
            message = "Invalid probe termination"
            raise RuntimeError(message)
        receipt.status = "PROBE_COMPLETE"
    finally:
        restore()
        sys.argv = previous_argv
        receipt.elapsed_seconds = time.monotonic() - started
        receipt.first_step_seconds = accounting.first_seconds
        receipt.denoiser_calls = accounting.calls
        receipt.scheduler_steps_completed = accounting.completed
        receipt.peak_rss_kib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        receipt.cuda_peak_allocated_bytes = torch.cuda.max_memory_allocated()
        receipt.cuda_peak_reserved_bytes = torch.cuda.max_memory_reserved()
        if receipt.status == "PROBE_COMPLETE" and accounting.first_seconds is not None:
            setup = receipt.elapsed_seconds - accounting.first_seconds
            receipt.estimate_73_linear_stage2_seconds = setup + 20 * accounting.first_seconds
            receipt.estimate_73_quadratic_stage2_seconds = setup + 56 * accounting.first_seconds
            receipt.estimate_49_conservative_seconds = setup + 56 * 0.7 * accounting.first_seconds
        write_receipt(config.receipt, receipt)


if __name__ == "__main__":
    main()
