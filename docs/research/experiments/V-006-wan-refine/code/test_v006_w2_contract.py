# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run: python test_v006_w2_contract.py WAN_PIPELINE.py V006_SCENE_CONFIG.json
"""Execute the unchanged input-video unit with CPU-only temporal shape doubles.

This is a model-free contract fixture, not a VAE or inference quality test.
The fake VAE uses the inspected Wan VAE temporal rule 1 + (T - 1) // 4.
"""
from __future__ import annotations

import ast
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace


@dataclass(frozen=True, slots=True)
class ShapeTensor:
    frames: int

    def to(self, **kwargs: str) -> ShapeTensor:
        return self


class ShapeMismatch(RuntimeError):
    """Expected mismatch from the actual unit's add_noise boundary."""

    def __init__(self, clean: int, noise: int) -> None:
        self.clean = clean
        self.noise = noise
        super().__init__(f"input temporal length {clean} != noise length {noise}")


class ShapeVAE:
    def encode(self, video: ShapeTensor, **kwargs: str | bool | tuple[int, int]) -> ShapeTensor:
        return ShapeTensor(1 + (video.frames - 1) // 4)


class ShapeScheduler:
    training = False
    timesteps = (1,)

    def add_noise(self, clean: ShapeTensor, noise: ShapeTensor, **kwargs: int) -> ShapeTensor:
        if clean.frames != noise.frames:
            raise ShapeMismatch(clean.frames, noise.frames)
        return clean


class ShapePipe:
    vae = ShapeVAE()
    scheduler = ShapeScheduler()
    device = "cpu"
    torch_dtype = "bf16"

    def load_models_to_device(self, names: tuple[str, ...]) -> None:
        assert names == ("vae",)

    def preprocess_video(self, frames: list[int]) -> ShapeTensor:
        return ShapeTensor(len(frames))


class ShapeTorch:
    @staticmethod
    def concat(tensors: list[ShapeTensor], dim: int) -> ShapeTensor:
        assert dim == 2
        return ShapeTensor(sum(tensor.frames for tensor in tensors))


def main() -> None:
    pipeline_path, scene_path = (Path(value) for value in sys.argv[1:])
    source = pipeline_path.read_bytes()
    config = json.loads(scene_path.read_text())
    frame_count = config["refine_window"]["frames"]
    reference_count = len(config["variants"]["W2"]["refs"])
    assert frame_count > 0 and (frame_count - 1) % 4 == 0
    assert reference_count > 1
    tree = ast.parse(source)
    unit = next(node for node in tree.body
                if isinstance(node, ast.ClassDef) and node.name == "WanVideoUnit_InputVideoEmbedder")
    method = next(node for node in unit.body
                  if isinstance(node, ast.FunctionDef) and node.name == "process")
    # Keep the upstream body byte-for-byte semantically unchanged; annotations
    # are removed because importing the pipeline would import model libraries.
    for argument in method.args.args:
        argument.annotation = None
    method.returns = None
    executable = ast.Module(body=[method], type_ignores=[])
    namespace = {"torch": ShapeTorch}
    exec(compile(ast.fix_missing_locations(executable), str(pipeline_path), "exec"), namespace)
    process = namespace["process"]
    reports = []
    for refs in (1, reference_count):
        noise_length = 1 + (frame_count - 1) // 4 + refs
        # Given: real method, inspected VAE temporal rule, single/two refs.
        try:
            # When: execute the original InputVideoEmbedder.process body.
            result = process(
                SimpleNamespace(onload_model_names=("vae",)), ShapePipe(),
                list(range(frame_count)), ShapeTensor(noise_length), True,
                (1, 1), (1, 1), list(range(refs)), False, None, None,
            )
        except ShapeMismatch as error:
            # Then: only the requested multiple-reference case is incompatible.
            assert refs == reference_count
            assert error.clean == 1 + (frame_count - 1) // 4 + 1
            assert error.noise == noise_length
            reports.append({"refs": refs, "input_T": error.clean,
                            "noise_T": error.noise, "status": "EXPECTED_SHAPE_MISMATCH"})
        else:
            assert refs == 1 and result["latents"].frames == noise_length
            reports.append({"refs": refs, "input_T": noise_length,
                            "noise_T": noise_length, "status": "SINGLE_REFERENCE_CONTROL_PASS"})
    print(json.dumps({"fixture": "CPU_SHAPE_DOUBLE_NOT_MODEL_EXECUTION",
                      "source_sha256": hashlib.sha256(source).hexdigest(),
                      "source_method_line": method.lineno,
                      "frames": frame_count, "cases": reports,
                      "status": "PASS", "models_loaded": 0, "gpu_calls": 0}, indent=2))


if __name__ == "__main__":
    main()
