"""B020 fixed RF velocity contract, using normalized Wan VAE CTHW latents."""

import math
from dataclasses import dataclass
from typing import Annotated, ClassVar, Literal, Self, TypedDict

import torch
from pydantic import BaseModel, ConfigDict, Field, model_validator
from torch import Tensor


@dataclass(frozen=True)
class FMTuple:
    tuple_id: str
    sigma: float
    seed: int
    split: Literal["train", "holdout"]


@dataclass(frozen=True)
class FMInputs:
    z_sigma: Tensor
    target: Tensor
    noise: Tensor
    timestep: Tensor


class ParityResult(TypedDict):
    passed: bool
    max_abs: float
    atol: float
    rtol: float


def fixed_tuples() -> tuple[FMTuple, ...]:
    return (
        FMTuple("train_0", 0.2, 2026102401, "train"),
        FMTuple("train_1", 0.5, 2026102402, "train"),
        FMTuple("train_2", 0.8, 2026102403, "train"),
        FMTuple("holdout", 0.65, 2026102404, "holdout"),
    )


def _latent(value: Tensor) -> None:
    if value.ndim != 4 or value.shape[0] != 16 or min(value.shape) < 1:
        raise ValueError("Expected nonempty CTHW latent with C=16")
    if value.dtype != torch.float32 or not bool(torch.isfinite(value).all()):
        raise ValueError("Expected finite FP32 latent")


def make_noise(z_y: Tensor, spec: FMTuple) -> Tensor:
    _latent(z_y)
    if spec not in fixed_tuples():
        raise ValueError("Tuple is outside the preregistered four")
    generator = torch.Generator(device="cpu").manual_seed(spec.seed)
    return torch.randn(
        z_y.shape, generator=generator, device="cpu", dtype=torch.float32
    )


def mix_velocity(z_y: Tensor, noise: Tensor, sigma: float) -> FMInputs:
    _latent(z_y)
    _latent(noise)
    if noise.shape != z_y.shape or noise.device != z_y.device:
        raise ValueError("Noise and target must have identical shape/device")
    if not math.isfinite(sigma) or not 0 <= sigma <= 1:
        raise ValueError("Sigma must be finite and in [0,1]")
    return FMInputs(
        z_sigma=(1 - sigma) * z_y + sigma * noise,
        target=noise - z_y,
        noise=noise,
        timestep=torch.tensor([1000 * sigma], dtype=torch.float32, device=z_y.device),
    )


def velocity_mse(prediction: Tensor, target: Tensor) -> Tensor:
    _latent(prediction)
    _latent(target)
    if prediction.shape != target.shape or prediction.device != target.device:
        raise ValueError("Velocity MSE forbids broadcasting or device changes")
    return (prediction - target).square().mean()


def check_parity(
    pred: Tensor, baseline: Tensor, atol: float = 1e-3, rtol: float = 1e-3
) -> ParityResult:
    _latent(pred)
    _latent(baseline)
    if atol != 1e-3 or rtol != 1e-3:
        raise ValueError("B020 parity tolerance was fixed before execution")
    if pred.shape != baseline.shape or pred.device != baseline.device:
        raise ValueError("Parity requires exact shape/device agreement")
    return ParityResult(
        passed=bool(torch.allclose(pred, baseline, atol=atol, rtol=rtol)),
        max_abs=float((pred - baseline).abs().max()),
        atol=atol,
        rtol=rtol,
    )


def validate_tail_shapes(
    h38: Tensor, block_e0: Tensor, head_e: Tensor, expected_tokens: int
) -> None:
    if expected_tokens <= 0 or h38.shape != (1, expected_tokens, 5120):
        raise ValueError("Wrong final-block hidden shape/token count")
    if block_e0.shape != (1, 6, 5120) or head_e.shape != (1, 5120):
        raise ValueError("Block e0 and head e are distinct official inputs")
    if block_e0.dtype != torch.float32 or head_e.dtype != torch.float32:
        raise ValueError("Official time embeddings must remain FP32")
    for value in (h38, block_e0, head_e):
        if value.is_inference() or not bool(torch.isfinite(value).all()):
            raise ValueError(
                "Cache must be finite ordinary tensors, not inference tensors"
            )


Hash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class CacheBinding(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")
    tuple_id: str
    sigma: float
    seed: int
    noise_hash: Hash
    z_y_hash: Hash
    conditions_hash: Hash
    model_hash: Hash
    geometry_hash: Hash
    code_hash: Hash

    @model_validator(mode="after")
    def fixed_tuple(self) -> Self:
        if not any(
            (s.tuple_id, s.sigma, s.seed) == (self.tuple_id, self.sigma, self.seed)
            for s in fixed_tuples()
        ):
            raise ValueError("Cache tuple differs from the fixed schedule")
        return self

    def require_same(self, expected: Self) -> None:
        if self != expected:
            raise ValueError("Cache binding mismatch: recomputation required")
