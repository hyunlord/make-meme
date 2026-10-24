"""CPU-only algebra and boundary tests; no model-quality claim."""

import pytest
import torch
from pydantic import ValidationError

from fm_contract import (
    CacheBinding,
    check_parity,
    fixed_tuples,
    make_noise,
    mix_velocity,
    validate_tail_shapes,
    velocity_mse,
)


def latent() -> torch.Tensor:
    return torch.arange(16 * 2 * 2 * 2, dtype=torch.float32).reshape(16, 2, 2, 2) / 100


def test_fixed_schedule_and_cpu_noise() -> None:
    specs = fixed_tuples()
    assert tuple(s.sigma for s in specs) == (0.2, 0.5, 0.8, 0.65)
    assert tuple(s.seed for s in specs) == tuple(range(2026102401, 2026102405))
    assert tuple(s.split for s in specs) == ("train", "train", "train", "holdout")
    noises = [make_noise(latent(), s) for s in specs]
    assert all(n.device.type == "cpu" and n.dtype == torch.float32 for n in noises)
    assert torch.equal(noises[0], make_noise(latent(), specs[0]))
    assert not torch.equal(noises[0], noises[1])


def test_mixture_target_time_and_endpoints() -> None:
    z = latent()
    noise = -z
    result = mix_velocity(z, noise, 0.2)
    assert torch.equal(result.target, noise - z)
    assert torch.equal(result.z_sigma, 0.8 * z + 0.2 * noise)
    assert result.timestep.shape == (1,) and result.timestep.item() == 200
    assert torch.equal(mix_velocity(z, noise, 0).z_sigma, z)
    assert torch.equal(mix_velocity(z, noise, 1).z_sigma, noise)
    assert result.target.dtype == torch.float32


@pytest.mark.parametrize("sigma", [-0.1, 1.1, float("nan")])
def test_bad_sigma(sigma: float) -> None:
    with pytest.raises(ValueError):
        _ = mix_velocity(latent(), latent(), sigma)


def test_shape_dtype_finiteness_and_broadcast_rejected() -> None:
    z = latent()
    for bad in (z.permute(1, 0, 2, 3), z.to(torch.bfloat16), z.unsqueeze(0)):
        with pytest.raises(ValueError):
            _ = mix_velocity(bad, bad, 0.5)
    with pytest.raises(ValueError):
        _ = velocity_mse(z, z[:, :1])
    bad = z.clone()
    bad[0, 0, 0, 0] = float("nan")
    with pytest.raises(ValueError):
        _ = mix_velocity(z, bad, 0.5)


def test_frozen_head_remains_differentiable() -> None:
    head = torch.nn.Linear(2, 2).requires_grad_(False).eval()
    hidden = torch.ones(16, 2, 2, 2, requires_grad=True)
    prediction = head.forward(hidden)
    loss = velocity_mse(prediction, torch.zeros_like(prediction))
    _ = loss.backward()
    assert hidden.grad is not None and hidden.grad.abs().sum() > 0
    assert all(p.grad is None for p in head.parameters())
    assert loss.dtype == torch.float32


def test_parity_fixed_tolerance() -> None:
    z = torch.zeros_like(latent())
    assert check_parity(z, z)["passed"]
    assert not check_parity(z + 0.01, z)["passed"]
    with pytest.raises(ValueError):
        _ = check_parity(z, z, atol=0.1)


def test_e_and_e0_are_distinct() -> None:
    h = torch.zeros(1, 6, 5120)
    block_e = torch.zeros(1, 6, 5120)
    head_e = torch.zeros(1, 5120)
    validate_tail_shapes(h, block_e, head_e, 6)
    with pytest.raises(ValueError):
        validate_tail_shapes(h, head_e, block_e, 6)
    with pytest.raises(ValueError):
        validate_tail_shapes(h, block_e, head_e, 7)
    with torch.inference_mode():
        inference_h = torch.zeros_like(h)
    with pytest.raises(ValueError):
        validate_tail_shapes(inference_h, block_e, head_e, 6)


def test_cache_binding_changes_invalidate() -> None:
    binding = CacheBinding(
        tuple_id="train_0",
        sigma=0.2,
        seed=2026102401,
        noise_hash="a" * 64,
        z_y_hash="b" * 64,
        conditions_hash="c" * 64,
        model_hash="d" * 64,
        geometry_hash="e" * 64,
        code_hash="f" * 64,
    )
    for field in (
        "noise_hash",
        "z_y_hash",
        "conditions_hash",
        "model_hash",
        "geometry_hash",
        "code_hash",
    ):
        changed = binding.model_dump()
        changed[field] = "0" * 64
        with pytest.raises(ValueError):
            binding.require_same(CacheBinding.model_validate(changed))
    with pytest.raises(ValidationError):
        _ = CacheBinding.model_validate({**binding.model_dump(), "sigma": 0.5})
