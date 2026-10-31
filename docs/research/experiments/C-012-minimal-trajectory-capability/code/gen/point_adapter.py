"""Shared train/inference point splatting; FP32 adapter masters, frozen backbone elsewhere."""
import torch
from torch import Tensor, nn
from point_features import PointCondition


class PointAnchorAdapter(nn.Module):
    """Permutation-invariant point MLP and four zero-initialized residual projections.

    Spatial tokens15x26; nominal time groups [0],[1..4],...,[29..32].
    Each frame's spatially normalized splat is averaged within its group: individual
    supports survive; positions are never averaged. Flatten order is T,H,W.
    """
    def __init__(self) -> None:
        super().__init__()
        # 288 patch +2 anchor bit +2 q +2 delta +4 endpoint offset +
        # 1 time +2 visibility/valid +1 motion bit +1 sigma =303.
        self.mlp = nn.Sequential(nn.Linear(303,192), nn.SiLU(), nn.Linear(192,192), nn.SiLU())
        self.projections = nn.ModuleList(nn.Linear(192,1536,bias=False) for _ in range(4))
        for projection in self.projections:
            nn.init.zeros_(projection.weight)

    def forward(self, condition: PointCondition, sigma: Tensor | float) -> Tensor:
        """Return FP32 [1,3510,192], compute once per model_fn and reuse at four blocks."""
        q = condition.positions.detach().float()
        assert q.ndim == 3 and q.shape[0] == 33 and q.shape[2] == 2
        k = q.shape[1]
        assert 1 <= k <= 16
        assert condition.patches.shape == (k,2,144)
        assert condition.anchor_valid.shape == (2,k)
        assert condition.visible.shape == condition.valid.shape == (33,k)
        assert condition.box_wh.shape == (33,2)
        assert all(p.dtype == torch.float32 for p in self.parameters()), 'FP32 master required'
        gate = condition.valid.bool() & condition.visible.bool() & torch.isfinite(q).all(-1)
        gate = gate & (q >= 0).all(-1) & (q <= 1).all(-1)
        q = torch.where(gate[...,None],q,torch.zeros_like(q))
        delta = torch.zeros_like(q)
        delta[1:] = (q[1:]-q[:-1])*(gate[1:] & gate[:-1])[...,None]
        anchor_valid = condition.anchor_valid.T.bool()
        patches = condition.patches.detach().float()*anchor_valid[...,None]
        anchors = condition.positions[[0,32]].detach().float().permute(1,0,2)
        anchors = torch.where(anchor_valid[...,None],anchors,torch.zeros_like(anchors))
        offsets = (q[:,:,None,:]-anchors[None]) * anchor_valid[None,:,:,None]
        time = torch.linspace(0,1,33,device=q.device)[:,None,None].expand(-1,k,-1)
        noise_time = torch.as_tensor(sigma,device=q.device,dtype=torch.float32).reshape(1,1,1).expand(33,k,1)
        features = torch.cat((patches.reshape(1,k,288).expand(33,-1,-1),
            anchor_valid.float()[None].expand(33,-1,-1),q,delta,offsets.flatten(2),time,
            condition.visible.float()[...,None],condition.valid.float()[...,None],
            torch.full_like(time,float(condition.motion_available)),noise_time),dim=-1)
        assert features.shape == (33,k,303) and torch.isfinite(features).all()
        with torch.autocast(device_type=q.device.type, enabled=False):
            point_features = self.mlp(features)
            y,x = torch.meshgrid((torch.arange(15,device=q.device)+.5)/15,
                                  (torch.arange(26,device=q.device)+.5)/26,indexing='ij')
            grid = torch.stack((x,y),-1).reshape(1,390,1,2)
            # ON and NULL use exactly the same endpoint-derived kernel widths.
            tau = torch.linspace(0,1,33,device=q.device)[:,None]
            boxes = condition.box_wh[[0,32]].detach().float()
            boxes = (1-tau)*boxes[0]+tau*boxes[1]
            width = torch.maximum(boxes*.08,
                                  q.new_tensor([1/26,1/15]))
            assert torch.isfinite(width).all()
            distance = (grid-q[:,None,:,:])/width[:,None,None,:]
            radius2 = distance.square().sum(-1)
            weights = torch.exp(-.5*radius2)*(radius2 <= 9)*gate[:,None,:]
            splats = torch.bmm(weights,point_features)/weights.sum(-1,keepdim=True).clamp_min(1)
            grouped = torch.cat((splats[:1],splats[1:].reshape(8,4,390,192).mean(1)),dim=0)
        return grouped.reshape(1,9*15*26,192)

    def residual(self, context: Tensor, block_index: int, hidden: Tensor, enabled: bool = True) -> Tensor:
        """Exact object bypass if disabled; projection math FP32 then cast to backbone dtype."""
        if not enabled:
            return hidden
        assert 0 <= block_index < 4 and hidden.shape[-2:] == (3510,1536)
        with torch.autocast(device_type=hidden.device.type,enabled=False):
            update = self.projections[block_index](context.float())
        return hidden + update.to(dtype=hidden.dtype)
