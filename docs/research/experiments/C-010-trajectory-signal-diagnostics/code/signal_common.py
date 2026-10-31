"""C-010 shared helpers. Imports the preserved C-006 code; never modifies it."""
from pathlib import Path
import hashlib
import json

import torch
from torch import Tensor

CASES = (('bear', 'train'), ('dance-twirl', 'train'), ('elephant', 'validation'), ('goat', 'validation'))
# Validation noise follows C-007 (20261101 + validation index); train seeds fixed in PLAN before any run.
NOISE_SEED = {'elephant': 20261101, 'goat': 20261102, 'bear': 20261201, 'dance-twirl': 20261202}
TARGET_SIGMAS = (0.95, 0.50, 0.05)
WH = (416.0, 240.0)


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tensor_sha(t: Tensor) -> str:
    cpu = t.detach().cpu().contiguous()
    return digest_bytes(cpu.view(torch.uint8).numpy().tobytes())


def rms(x: Tensor) -> float:
    return float(x.detach().double().square().mean().sqrt()) if x.numel() else float('nan')


def cosine(a: Tensor, b: Tensor) -> float | None:
    a, b = a.detach().double().flatten(), b.detach().double().flatten()
    na, nb = a.norm(), b.norm()
    return float(a @ b / (na * nb)) if na > 1e-30 and nb > 1e-30 else None


def pair(on: Tensor, null: Tensor, select: Tensor | None = None) -> dict:
    """ON/NULL comparison inside one representation space (never across boundaries)."""
    if select is not None:
        on, null = on[select], null[select]
    d = on.double() - null.double()
    base = 0.5 * (rms(on) + rms(null))
    return {'rms_on': rms(on), 'rms_null': rms(null), 'diff_rms': rms(d),
            'rel_diff': rms(d) / base if base > 1e-30 else None, 'cosine': cosine(on, null),
            'elements': int(on.numel())}


def gate_of(condition) -> Tensor:
    """Exactly the adapter's gate."""
    q = condition.positions.detach().float()
    gate = condition.valid.bool() & condition.visible.bool() & torch.isfinite(q).all(-1)
    return gate & (q >= 0).all(-1) & (q <= 1).all(-1)


def adapter_trace(adapter, condition, sigma) -> dict:
    """Line-by-line copy of PointAnchorAdapter.forward that also returns P1..P5.

    Caller must assert trace['grouped'] equals adapter(condition, sigma) exactly.
    """
    q = condition.positions.detach().float()
    k = q.shape[1]
    gate = gate_of(condition)
    q = torch.where(gate[..., None], q, torch.zeros_like(q))
    delta = torch.zeros_like(q)
    delta[1:] = (q[1:] - q[:-1]) * (gate[1:] & gate[:-1])[..., None]
    anchor_valid = condition.anchor_valid.T.bool()
    patches = condition.patches.detach().float() * anchor_valid[..., None]
    anchors = condition.positions[[0, 32]].detach().float().permute(1, 0, 2)
    anchors = torch.where(anchor_valid[..., None], anchors, torch.zeros_like(anchors))
    offsets = (q[:, :, None, :] - anchors[None]) * anchor_valid[None, :, :, None]
    time = torch.linspace(0, 1, 33, device=q.device)[:, None, None].expand(-1, k, -1)
    noise_time = torch.as_tensor(sigma, device=q.device, dtype=torch.float32).reshape(1, 1, 1).expand(33, k, 1)
    features = torch.cat((patches.reshape(1, k, 288).expand(33, -1, -1),
        anchor_valid.float()[None].expand(33, -1, -1), q, delta, offsets.flatten(2), time,
        condition.visible.float()[..., None], condition.valid.float()[..., None],
        torch.full_like(time, float(condition.motion_available)), noise_time), dim=-1)
    with torch.autocast(device_type=q.device.type, enabled=False):
        point_features = adapter.mlp(features)
        y, x = torch.meshgrid((torch.arange(15, device=q.device) + .5) / 15,
                              (torch.arange(26, device=q.device) + .5) / 26, indexing='ij')
        grid = torch.stack((x, y), -1).reshape(1, 390, 1, 2)
        tau = torch.linspace(0, 1, 33, device=q.device)[:, None]
        boxes = condition.box_wh[[0, 32]].detach().float()
        boxes = (1 - tau) * boxes[0] + tau * boxes[1]
        width = torch.maximum(boxes * .08, q.new_tensor([1 / 26, 1 / 15]))
        distance = (grid - q[:, None, :, :]) / width[:, None, None, :]
        radius2 = distance.square().sum(-1)
        weights = torch.exp(-.5 * radius2) * (radius2 <= 9) * gate[:, None, :]
        splats = torch.bmm(weights, point_features) / weights.sum(-1, keepdim=True).clamp_min(1)
        grouped = torch.cat((splats[:1], splats[1:].reshape(8, 4, 390, 192).mean(1)), dim=0)
    return {'features': features, 'point_features': point_features, 'weights': weights, 'gate': gate,
            'width': width, 'splats': splats, 'grouped': grouped.reshape(1, 9 * 15 * 26, 192)}


def frame_support(trace: dict) -> Tensor:
    """[33,390] token support per frame: gate & radius^2 <= 9 (weights > 0)."""
    return (trace['weights'] > 0).any(-1)


def group_support(fs: Tensor) -> Tensor:
    """[9*390] token support of the grouped context: any frame of the group has support."""
    g = torch.cat((fs[:1], fs[1:].reshape(8, 4, 390).any(1)), 0)
    return g.reshape(-1)


def eta(splat_on: Tensor, splat_null: Tensor) -> dict:
    """Fraction of ON/NULL splat-difference energy that survives the group mean."""
    d = splat_on.double() - splat_null.double()
    groups = [[0]] + [list(range(1 + 4 * i, 5 + 4 * i)) for i in range(8)]
    num = sum(len(g) * d[g].mean(0).square().sum() for g in groups)
    den = d.square().sum()
    num_nz = sum(len(g) * d[g].mean(0).square().sum() for g in groups[1:])
    den_nz = d[1:].square().sum()
    per_group = [float((len(g) * d[g].mean(0).square().sum() / d[g].square().sum()).sqrt())
                 if d[g].square().sum() > 0 else None for g in groups]
    return {'eta': float((num / den).sqrt()) if den > 0 else None,
            'eta_excluding_group0': float((num_nz / den_nz).sqrt()) if den_nz > 0 else None,
            'per_group': per_group}


def token_mask(loss_mask: Tensor) -> Tensor:
    """[1,1,9,30,52] soft object mask -> [3510] token weights (2x2 average, T,H,W order)."""
    pooled = torch.nn.functional.avg_pool3d(loss_mask.float(), (1, 2, 2))
    return pooled.reshape(-1)


def weighted_inner(a: Tensor, b: Tensor, mask: Tensor) -> dict:
    """Exactly balanced_loss geometry: channel mean, area-normalised object and background terms."""
    prod = (a.double() * b.double()).mean(dim=1, keepdim=True)
    m = mask.double()
    obj = float((prod * m).sum() / m.sum())
    bg = float((prod * (1 - m)).sum() / (1 - m).sum())
    return {'obj': obj, 'bg': bg, 'W': obj + bg}


def decompose(v_a: Tensor, v_b: Tensor, target: Tensor, mask: Tensor) -> dict:
    """L_A - L_B = ||delta||_W^2 - 2 <delta, e_B>_W with e_B = u* - v_B."""
    va, vb, u = v_a.double(), v_b.double(), target.double()
    delta, e_b = va - vb, u - vb
    dd, de, ee = weighted_inner(delta, delta, mask), weighted_inner(delta, e_b, mask), weighted_inner(e_b, e_b, mask)
    l_a, l_b = weighted_inner(u - va, u - va, mask), weighted_inner(e_b, e_b, mask)
    out = {}
    for part in ('obj', 'bg', 'W'):
        out[part] = {'L_A': l_a[part], 'L_B': l_b[part], 'direct_diff': l_a[part] - l_b[part],
                     'delta_sq': dd[part], 'delta_dot_e': de[part], 'e_sq': ee[part],
                     'decomposed_diff': dd[part] - 2 * de[part],
                     'weighted_cosine': de[part] / (dd[part] * ee[part]) ** .5 if dd[part] > 1e-30 and ee[part] > 1e-30 else None}
        out[part]['identity_abs_error'] = abs(out[part]['direct_diff'] - out[part]['decomposed_diff'])
    return out


def write_json(path: Path, value) -> None:
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=1, allow_nan=True, default=str))
    tmp.replace(path)
