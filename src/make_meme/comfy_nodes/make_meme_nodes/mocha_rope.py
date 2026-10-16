"""Real-valued drop-in replacements for MoCha's complex RoPE helpers.

Frequencies are stored as a float32 tensor of shape [L, dim/2, 2] holding (cos, sin)
instead of a complex128 tensor of shape [L, dim/2]. `torch.cat(..., dim=1)` and
`.to(device)` in the caller keep working unchanged.
"""

from __future__ import annotations

import torch


def rope_params_mocha_real(max_seq_len, dim, theta=10000, L_test=25, k=0, start=0):
    assert dim % 2 == 0
    exponents = torch.arange(0, dim, 2, dtype=torch.float64).div(dim)
    inv_theta_pow = 1.0 / torch.pow(theta, exponents)
    if k > 0:
        inv_theta_pow[k - 1] = 0.9 * 2 * torch.pi / L_test
    angles = torch.outer(torch.arange(start, max_seq_len, dtype=torch.float64), inv_theta_pow)
    return torch.stack([angles.cos(), angles.sin()], dim=-1).to(torch.float32)


def _axis(freqs: torch.Tensor, rows: slice, shape: tuple[int, int, int], axis: int) -> torch.Tensor:
    part = freqs[rows]
    view = [1, 1, 1, part.shape[1], 2]
    view[axis] = part.shape[0]
    return part.view(*view).expand(*shape, part.shape[1], 2)


def _block(f0, f1, f2, t_rows: slice, h_rows: slice, w_rows: slice, n_t: int, h: int, w: int):
    shape = (n_t, h, w)
    return torch.cat(
        [_axis(f0, t_rows, shape, 0), _axis(f1, h_rows, shape, 1), _axis(f2, w_rows, shape, 2)], dim=-2
    )


def rope_apply_mocha_real(x, grid_sizes, freqs):
    n, c = x.size(2), x.size(3) // 2
    s1 = c - 2 * (c // 3)
    s2 = c // 3
    f0, f1, f2 = freqs.split([s1, s2, s2], dim=1)

    outputs = []
    for i in range(grid_sizes.size(0)):
        f, h, w = grid_sizes[i].tolist()
        seq_len = f * h * w
        sf = (f - 2) // 2
        hs, ws = slice(1, 1 + h), slice(1, 1 + w)

        repeat_freqs = _block(f0, f1, f2, slice(1, 1 + sf), hs, ws, sf, h, w)
        mask_freqs = _block(f0, f1, f2, slice(1, 2), hs, ws, 1, h, w)
        img_freqs = _block(f0, f1, f2, slice(0, 1), hs, ws, 1, h, w)
        parts = [repeat_freqs, repeat_freqs, mask_freqs, img_freqs]
        if f != 2 * sf + 2:  # second reference image gets offset spatial positions
            parts.append(
                _block(f0, f1, f2, slice(0, 1), slice(h + 1, 2 * h + 1), slice(w + 1, 2 * w + 1), 1, h, w)
            )
        freqs_i = torch.cat(parts, dim=0).reshape(seq_len, 1, c, 2).to(x.device)

        xr = x[i, :seq_len].to(torch.float32).reshape(seq_len, n, c, 2)
        a, b = xr[..., 0], xr[..., 1]
        cos, sin = freqs_i[..., 0], freqs_i[..., 1]
        rotated = torch.stack([a * cos - b * sin, a * sin + b * cos], dim=-1).flatten(2)
        outputs.append(torch.cat([rotated, x[i, seq_len:].to(torch.float32)], dim=0))

    return torch.stack(outputs).to(x.dtype)
