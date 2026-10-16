"""The real-valued MoCha RoPE must match the original complex implementation
(ComfyUI-WanVideoWrapper mocha/nodes.py, Apache-2.0), reproduced here as reference."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "make_meme" / "comfy_nodes"))
from make_meme_nodes.mocha_rope import rope_apply_mocha_real, rope_params_mocha_real


def ref_params(max_seq_len, dim, theta=10000, L_test=25, k=0, start=0):
    exponents = torch.arange(0, dim, 2, dtype=torch.float64).div(dim)
    inv = 1.0 / torch.pow(theta, exponents)
    if k > 0:
        inv[k - 1] = 0.9 * 2 * torch.pi / L_test
    freqs = torch.outer(torch.arange(start, max_seq_len), inv)
    return torch.polar(torch.ones_like(freqs), freqs)


def ref_apply(x, grid_sizes, freqs):
    n, c = x.size(2), x.size(3) // 2
    f0, f1, f2 = freqs.split([c - 2 * (c // 3), c // 3, c // 3], dim=1)
    outs = []
    for i in range(grid_sizes.size(0)):
        f, h, w = grid_sizes[i].tolist()
        seq_len = f * h * w
        x_i = torch.view_as_complex(x[i, :seq_len].reshape(seq_len, n, -1, 2))
        sf = (f - 2) // 2
        hs, ws = slice(1, 1 + h), slice(1, 1 + w)

        def blk(t, nt, hs, ws, h=h, w=w):
            return torch.cat([
                f0[t].view(nt, 1, 1, -1).expand(nt, h, w, -1),
                f1[hs].view(1, h, 1, -1).expand(nt, h, w, -1),
                f2[ws].view(1, 1, w, -1).expand(nt, h, w, -1),
            ], dim=-1)

        parts = [blk(slice(1, 1 + sf), sf, hs, ws)] * 2 + [blk(slice(1, 2), 1, hs, ws), blk(slice(0, 1), 1, hs, ws)]
        if f != 2 * sf + 2:
            parts.append(blk(slice(0, 1), 1, slice(h + 1, 2 * h + 1), slice(w + 1, 2 * w + 1)))
        fi = torch.cat(parts, dim=0).reshape(seq_len, 1, -1)
        x_i = torch.view_as_real(x_i * fi).flatten(2)
        outs.append(torch.cat([x_i, x[i, seq_len:]], dim=0))
    return torch.stack(outs).to(x.dtype)


def _freqs(fn, d=128, L=5):
    return torch.cat([
        fn(1024, d - 4 * (d // 6), L_test=L, k=0, start=-1),
        fn(1024, 2 * (d // 6), start=-1),
        fn(1024, 2 * (d // 6), start=-1),
    ], dim=1)


@pytest.mark.parametrize("f", [12, 13])  # one reference image / two reference images
def test_real_rope_matches_complex(f):
    h, w, d = 4, 6, 128
    x = torch.randn(1, f * h * w + 5, 3, d)
    g = torch.tensor([[f, h, w]])
    expected = ref_apply(x, g, _freqs(ref_params))
    got = rope_apply_mocha_real(x, g, _freqs(rope_params_mocha_real))
    assert got.dtype == x.dtype
    assert torch.allclose(got, expected, atol=1e-5)
