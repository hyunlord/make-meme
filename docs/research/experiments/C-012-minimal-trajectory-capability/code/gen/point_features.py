"""Endpoint-only point features. Coordinates are (pixel index + .5) / image size."""
from dataclasses import dataclass, replace
import torch
from torch import Tensor
from torch.nn import functional as F


@dataclass(frozen=True, slots=True)
class PointCondition:
    patches: Tensor  # K,2,144; independently encoded endpoints only
    anchor_valid: Tensor  # 2,K bool
    positions: Tensor  # 33,K,2 normalized xy pixel centers
    visible: Tensor  # 33,K bool: actual tracker result, not confidence
    valid: Tensor  # 33,K bool
    box_wh: Tensor  # 33,2 endpoint-interpolated normalized bbox width/height
    motion_available: bool = True

    def to(self, device: torch.device | str) -> 'PointCondition':
        return replace(self, **{name: getattr(self, name).to(device) for name in
            ('patches', 'anchor_valid', 'positions', 'visible', 'valid', 'box_wh')})


def sample_anchor_patches(latents: Tensor, endpoints: Tensor, anchor_valid: Tensor) -> Tensor:
    """Read 3x3 latent-pixel offsets; invalid anchors become exact zero, no temporal slicing.

    latents: 2,16,1,30,52 from TWO independent VAE encodes.
    endpoints: 2,K,2; returns K,2,144 channel-major patch vectors.
    align_corners=False uses normalized pixel centers; out-of-image offsets zero-pad.
    """
    assert latents.shape == (2,16,1,30,52)
    assert endpoints.ndim == 3 and endpoints.shape[0] == 2 and endpoints.shape[-1] == 2
    assert anchor_valid.shape == endpoints.shape[:2]
    xy = endpoints.detach().float()
    usable = anchor_valid.bool() & torch.isfinite(xy).all(-1) & (xy >= 0).all(-1) & (xy <= 1).all(-1)
    xy = torch.where(usable[...,None], xy, torch.zeros_like(xy))
    dy, dx = torch.meshgrid(torch.arange(-1,2,device=xy.device), torch.arange(-1,2,device=xy.device), indexing='ij')
    offsets = torch.stack((dx/52,dy/30),-1).reshape(1,1,9,2)
    grid = (xy[:,:,None,:] + offsets)*2-1
    sampled = F.grid_sample(latents[:,:,0].detach().float(), grid, mode='bilinear', padding_mode='zeros', align_corners=False)
    patches = sampled.permute(2,0,1,3).reshape(xy.shape[1],2,144)
    return patches * usable.T[:,:,None]


def make_null(condition: PointCondition) -> PointCondition:
    """Endpoint-only NULL. Never inspect intermediate coordinates, gates, or bbox values.

    Both usable endpoints: linear path. One usable endpoint: constant fallback.
    Neither usable: zero location and gates. Endpoint visibility/validity are ANDed
    with anchor validity. Intermediate gates are derived solely from endpoint bits.
    """
    q = condition.positions[[0,32]].detach().float()
    gate = (condition.anchor_valid.bool() & condition.visible[[0,32]].bool()
            & condition.valid[[0,32]].bool() & torch.isfinite(q).all(-1)
            & (q >= 0).all(-1) & (q <= 1).all(-1))
    q = torch.where(gate[...,None], q, torch.zeros_like(q))
    start = torch.where(gate[0,:,None],q[0],q[1])
    end = torch.where(gate[1,:,None],q[1],q[0])
    tau = torch.linspace(0,1,33,device=q.device)[:,None,None]
    positions = (1-tau)*start + tau*end
    positions = torch.where((gate[0] & gate[1])[None,:,None], positions, start[None])
    active = gate.any(0)[None,:].expand(33,-1).clone()
    boxes = condition.box_wh[[0,32]].detach().float()
    box_wh = (1-tau[:,0])*boxes[0]+tau[:,0]*boxes[1]
    return replace(condition, positions=positions, visible=active, valid=active.clone(),
                   box_wh=box_wh, motion_available=False)


def retarget_endpoints(source: Tensor, target_endpoints: Tensor, bbox_ratios: Tensor) -> Tensor:
    """Fixed endpoint 2D diagonal approximation, NOT semantic/3D retargeting.

    source33,K,2; target_endpoints2,K,2; bbox_ratios2,2 (target/source wh).
    Equal endpoint coordinates and unit ratios recover the complete source track.
    """
    assert source.shape[0] == 33 and target_endpoints.shape == (2,source.shape[1],2)
    assert bbox_ratios.shape == (2,2)
    tau = torch.linspace(0,1,33,device=source.device,dtype=source.dtype)[:,None,None]
    first = target_endpoints[0]+bbox_ratios[0]*(source-source[0])
    last = target_endpoints[1]+bbox_ratios[1]*(source-source[-1])
    return (1-tau)*first+tau*last
