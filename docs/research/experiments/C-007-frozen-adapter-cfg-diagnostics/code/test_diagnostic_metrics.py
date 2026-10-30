"""Small CPU fixtures; never load a checkpoint or consume diagnostic forward budget."""
import torch
from torch import nn
from diagnostic_metrics import branch_metrics, cfg_metrics, ResidualObserver, geometric_support


def test_branch_balancing():
    p=torch.tensor([[[[[2.,4.]]],[[[2.,4.]]]]]); zero=torch.zeros_like(p)
    result=branch_metrics(p,zero,zero,.5,zero,torch.tensor([[[[[1.,0.]]]]]))
    assert result['mse']==10 and result['object_mse']==4 and result['background_mse']==16
    assert result['balanced_loss']==20 and result['clean_estimate']['balanced_loss']==5


def test_cfg_common_delta_and_zero():
    bp=torch.tensor([1.,2.]); bn=torch.tensor([.5,1.])
    result=cfg_metrics(bp,bn,bp+1,bn+1)
    assert result['delta_difference_rms']==0
    assert result['cfg1']['delta_rms']==result['cfg5']['delta_rms']==1
    zero=cfg_metrics(bp,bn,bp,bn)
    assert zero['delta_cosine'] is None and zero['delta_plus_norm']==0
    near=cfg_metrics(torch.zeros(2),torch.zeros(2),torch.zeros(2),torch.zeros(2))
    assert near['cfg5']['relative_change'] is None


class Fixture(nn.Module):
    def __init__(self):
        super().__init__()
        self.projections=nn.ModuleList(nn.Linear(2,3,bias=False) for _ in range(4))
        for projection in self.projections:
            with torch.no_grad(): projection.weight.fill_(.003)
    def residual(self,context,block_index,hidden,enabled=True):
        if not enabled:return hidden
        with torch.autocast(device_type=hidden.device.type,enabled=False):
            update=self.projections[block_index](context.float())
        return hidden+update.to(hidden.dtype)


def test_observer_preserves_bf16_and_rng():
    with torch.random.fork_rng(): adapter=Fixture()
    context=torch.tensor([[[1.,2.],[0.,0.],[3.,4.]]]);h=torch.ones(1,3,3,dtype=torch.bfloat16)
    expected=[adapter.residual(context,i,h) for i in range(4)]
    calls=[0]*4; handles=[]
    for i,p in enumerate(adapter.projections):
        def count(_m,_a,_o,index=i):calls[index]+=1
        handles.append(p.register_forward_hook(count))
    records=[]; rng=torch.random.get_rng_state().clone()
    with ResidualObserver(adapter,{'phase':'fixture'},records.append) as observer:
        observer.geometric_support=torch.tensor([[True,False,True]])
        for i in range(4):assert torch.equal(adapter.residual(context,i,h),expected[i])
        assert adapter.residual(context,0,h,False) is h
    assert torch.equal(rng,torch.random.get_rng_state()) and calls==[1]*4
    assert len(records)==4 and all(r['support_tokens']==2 for r in records)
    assert 'residual' not in adapter.__dict__
    for handle in handles:handle.remove()


def test_cfg_bf16_rounding_visible():
    bp=torch.tensor([1.,100.],dtype=torch.bfloat16);bn=torch.tensor([.1,.3],dtype=torch.bfloat16)
    r=cfg_metrics(bp,bn,bp+torch.tensor(.03125,dtype=torch.bfloat16),bn)
    assert r['cfg5']['base_native_minus_fp32']['rms']>0


def test_geometric_support_group_union():
    from types import SimpleNamespace
    q=torch.full((33,2,2),.5);visible=torch.zeros(33,2,dtype=torch.bool)
    visible[4,0]=True
    valid=torch.ones_like(visible);valid[:,1]=False
    c=SimpleNamespace(positions=q,visible=visible,valid=valid,box_wh=torch.ones(33,2))
    support=geometric_support(c).reshape(9,390)
    assert support[1].any() and not support[0].any() and not support[2:].any()
    class ForwardFixture(Fixture):
        def forward(self,condition,sigma):
            return torch.zeros(1,3510,2)
    with torch.random.fork_rng():adapter=ForwardFixture()
    records=[]
    with ResidualObserver(adapter,{},records.append) as observer:
        context=adapter(c,0.5)
        assert torch.equal(observer.geometric_support.reshape(9,390),support)
        h=torch.ones(1,3510,3,dtype=torch.bfloat16)
        adapter.residual(context,0,h)
    assert records[0]['support_tokens']>0 and records[0]['context_nonzero_tokens']==0
    c.valid.zero_()
    assert not geometric_support(c).any()


if __name__=='__main__':
    for test in (test_branch_balancing,test_cfg_common_delta_and_zero,test_observer_preserves_bf16_and_rng,test_cfg_bf16_rounding_visible,test_geometric_support_group_union):test()
    print('5 CPU fixtures PASS')
