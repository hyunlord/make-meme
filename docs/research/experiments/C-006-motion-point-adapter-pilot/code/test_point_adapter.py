"""CPU contract tests; no model download, VAE, tracker, or GPU execution."""
from dataclasses import replace
import unittest
import torch
from point_adapter import PointAnchorAdapter
from point_features import PointCondition, make_null, retarget_endpoints, sample_anchor_patches


def fixture(k: int = 3) -> PointCondition:
    generator = torch.Generator().manual_seed(123)
    return PointCondition(torch.randn(k,2,144,generator=generator),
        torch.ones(2,k,dtype=torch.bool),torch.rand(33,k,2,generator=generator)*.6+.2,
        torch.ones(33,k,dtype=torch.bool),torch.ones(33,k,dtype=torch.bool),
        torch.full((33,2),.5))


class AdapterContract(unittest.TestCase):
    def setUp(self) -> None:
        torch.manual_seed(19)
        torch.set_num_threads(2)
        self.adapter = PointAnchorAdapter()

    def test_zero_projection_and_actual_bypass(self) -> None:
        context = self.adapter(fixture(),.5)
        hidden = torch.randn(1,3510,1536,dtype=torch.bfloat16)
        self.assertTrue(torch.equal(self.adapter.residual(context,0,hidden),hidden))
        self.assertIs(self.adapter.residual(None,-99,hidden,enabled=False),hidden)
        self.assertLess(sum(p.numel() for p in self.adapter.parameters()),3_000_000)

    def test_null_independent_of_all_middle_data(self) -> None:
        original = fixture()
        q = original.positions.clone(); q[1:32] = float('nan')
        boxes = original.box_wh.clone(); boxes[1:32] = float('nan')
        visible = original.visible.clone(); visible[1:32] = False
        valid = original.valid.clone(); valid[1:32] = False
        poisoned = replace(original,positions=q,box_wh=boxes,visible=visible,valid=valid)
        a,b = make_null(original),make_null(poisoned)
        for name in ('positions','visible','valid','box_wh'):
            self.assertTrue(torch.equal(getattr(a,name),getattr(b,name)),name)
        self.assertTrue(torch.equal(self.adapter(a,.2),self.adapter(b,.2)))
        # Kernel width cannot leak actual middle bbox information into ON either.
        self.assertTrue(torch.equal(self.adapter(original,.2),
                                   self.adapter(replace(original,box_wh=boxes),.2)))

    def test_null_single_endpoint_fallback(self) -> None:
        c=fixture(); flags=c.anchor_valid.clone(); flags[1]=False
        null=make_null(replace(c,anchor_valid=flags))
        self.assertTrue(torch.equal(null.positions,c.positions[:1].expand(33,-1,-1)))
        self.assertTrue(null.valid.all()); self.assertFalse(null.motion_available)
        null=make_null(replace(c,anchor_valid=torch.zeros_like(flags)))
        self.assertFalse(null.valid.any()); self.assertEqual(null.positions.count_nonzero(),0)

    def test_permutation_and_gating(self) -> None:
        c=fixture(); order=torch.tensor([2,0,1])
        shuffled=replace(c,patches=c.patches[order],anchor_valid=c.anchor_valid[:,order],
            positions=c.positions[:,order],visible=c.visible[:,order],valid=c.valid[:,order])
        torch.testing.assert_close(self.adapter(c,.4),self.adapter(shuffled,.4),atol=2e-7,rtol=2e-6)
        with torch.no_grad(): self.adapter.projections[0].weight.normal_()
        empty=self.adapter(replace(c,visible=torch.zeros_like(c.visible)),.4)
        self.assertEqual(empty.count_nonzero(),0)
        hidden=torch.zeros(1,3510,1536)
        self.assertEqual(self.adapter.residual(empty,0,hidden).count_nonzero(),0)

    def test_patch_centers_invalid_and_endpoint_separation(self) -> None:
        latents=torch.zeros(2,16,1,30,52)
        y,x=torch.meshgrid(torch.arange(30),torch.arange(52),indexing='ij')
        latents[0]=x+100*y;latents[1]=latents[0]+10000
        xy=torch.tensor([[(10.5/52,12.5/30)],[(10.5/52,12.5/30)]])
        patches=sample_anchor_patches(latents,xy,torch.ones(2,1,dtype=torch.bool))
        expected=latents[0,0,0,11:14,9:12].reshape(-1)
        torch.testing.assert_close(patches[0,0,:9],expected,atol=.001,rtol=0)
        torch.testing.assert_close(patches[0,1,:9],expected+10000,atol=.002,rtol=0)
        xy[1]=float('nan')
        masked=sample_anchor_patches(latents,xy,torch.ones(2,1,dtype=torch.bool))
        self.assertTrue(torch.isfinite(masked).all());self.assertEqual(masked[:,1].count_nonzero(),0)

    def test_retarget_identity(self) -> None:
        c=fixture()
        torch.testing.assert_close(retarget_endpoints(c.positions,c.positions[[0,32]],torch.ones(2,2)),
                                   c.positions,atol=1e-7,rtol=1e-6)

    def test_time_support_flatten_and_width(self) -> None:
        c=fixture(1); q=torch.zeros_like(c.positions)
        q[:]=torch.tensor([(5.5)/26,(6.5)/15])
        q[2]=torch.tensor([(20.5)/26,(6.5)/15])
        vis=torch.zeros_like(c.visible);vis[[0,1,2]]=True
        c=replace(c,positions=q,visible=vis,box_wh=torch.zeros_like(c.box_wh))
        with torch.no_grad():
            for p in self.adapter.mlp.parameters():p.zero_()
            self.adapter.mlp[2].bias.fill_(1)
        context=self.adapter(c,.5).reshape(9,15,26,192)
        value=torch.nn.functional.silu(torch.tensor(1.))
        torch.testing.assert_close(context[0,6,5,0],value)
        torch.testing.assert_close(context[1,6,5,0],value/4)
        torch.testing.assert_close(context[1,6,20,0],value/4)
        self.assertEqual(context[1,6,12,0],0) # no average-position splat
        self.assertEqual(context[0,6,9,0],0) # outside fixed 3-sigma radius
        self.assertLess(context[0,6,6,0],value) # max(1,sumw), not normalized to 1
        self.assertEqual(context[2:].count_nonzero(),0)

    def test_fp32_master_two_step_gradient_and_frozen_backbone(self) -> None:
        frozen=torch.nn.Linear(1536,1,bias=False).requires_grad_(False)
        before=frozen.weight.detach().clone()
        opt=torch.optim.SGD(self.adapter.parameters(),lr=.01)
        for step in range(2):
            opt.zero_grad(set_to_none=True)
            with torch.autocast('cpu',dtype=torch.bfloat16):
                context=self.adapter(fixture(),.5)
                hidden=self.adapter.residual(context,0,torch.zeros(1,3510,1536,dtype=torch.bfloat16))
                loss=(frozen(hidden[:,390:780])-1).square().mean()
            loss.backward()
            mlp_grad=sum(float(p.grad.abs().sum()) for p in self.adapter.mlp.parameters())
            self.assertGreater(float(self.adapter.projections[0].weight.grad.abs().sum()),0)
            if step==0:self.assertEqual(mlp_grad,0)
            else:self.assertGreater(mlp_grad,0)
            self.assertTrue(all(p.dtype==torch.float32 for p in self.adapter.parameters()))
            opt.step()
        self.assertIsNone(frozen.weight.grad);self.assertTrue(torch.equal(before,frozen.weight))


if __name__=='__main__':
    unittest.main(verbosity=2)
