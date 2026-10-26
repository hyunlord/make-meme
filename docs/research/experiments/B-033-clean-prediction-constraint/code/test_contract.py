"""Four bounded CPU contract checks against the actual pinned scheduler."""
import json
import torch
from clean_constraint import CleanConstraintScheduler,latent_mask,mix_clean
from wan.utils.fm_solvers_unipc import FlowUniPCMultistepScheduler


def trajectory(kind):
    scheduler=kind(num_train_timesteps=1000,shift=1,use_dynamic_shifting=False)
    scheduler.set_timesteps(4,device='cpu',shift=3)
    x=torch.arange(32,dtype=torch.float32).reshape(2,1,4,4)/32
    return scheduler,x


def test_off_and_one():
    base,x=trajectory(FlowUniPCMultistepScheduler);off,y=trajectory(CleanConstraintScheduler);one,z=trajectory(CleanConstraintScheduler)
    one.bind(torch.zeros_like(z),torch.ones(1,1,1,4,4))
    for t in base.timesteps:
        x=base.step(x*.1,t,x,return_dict=False)[0];y=off.step(y*.1,t,y,return_dict=False)[0];z=one.step(z*.1,t,z,return_dict=False)[0]
        assert torch.equal(x,y) and torch.equal(x,z)


def test_zero_history():
    scheduler,x=trajectory(CleanConstraintScheduler);source=torch.full_like(x,.25)
    scheduler.bind(source,torch.zeros(1,1,1,4,4))
    for t in scheduler.timesteps:
        x=scheduler.step(x*.1,t,x,return_dict=False)[0]
        assert bool(torch.isfinite(x).all())
        assert all(value is None or torch.equal(value,source) for value in scheduler.model_outputs)
    assert scheduler.constraint_calls==4


def test_mask_axes():
    edit=torch.zeros(17,512,896);edit[4,64:72,80:88]=1
    mask=latent_mask(edit)
    assert list(mask.shape)==[1,1,5,64,112] and mask.dtype==torch.float32
    assert float(mask.sum())==9 and float(mask[0,0,1].sum())==9
    assert float(mask[0,0,0].sum())==0


def test_final_endpoints():
    x=torch.arange(32,dtype=torch.float32).reshape(2,1,4,4);source=x+3;original=x.clone()
    assert torch.equal(mix_clean(x,source,torch.zeros(1,1,1,4,4)),source)
    assert torch.equal(mix_clean(x,source,torch.ones(1,1,1,4,4)),x)
    assert torch.equal(x,original)

if __name__=='__main__':
    for test in (test_off_and_one,test_zero_history,test_mask_axes,test_final_endpoints):test()
    print(json.dumps({'status':'PASS','tests':4,'scope':'small CPU fixtures, not full-model equivalence'}))
