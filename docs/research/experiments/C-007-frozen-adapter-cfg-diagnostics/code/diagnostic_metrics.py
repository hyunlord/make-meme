"""Detached FP32 summaries; native BF16 model arithmetic is never replaced."""
from collections.abc import Callable
from typing import TypeAlias
import torch
from torch import Tensor

Json: TypeAlias = str | int | float | bool | None | list['Json'] | dict[str, 'Json']
Record: TypeAlias = dict[str, Json]
NEAR_ZERO = 1e-12


def rms(x: Tensor) -> float:
    return float(x.detach().float().square().mean().sqrt())


def difference(x: Tensor, y: Tensor) -> Record:
    d=x.detach().float()-y.detach().float()
    return {'rms':rms(d),'max_abs':float(d.abs().max())}


def _errors(pred: Tensor, target: Tensor, mask: Tensor) -> Record:
    error=(pred.detach().float()-target.detach().float()).square().mean(1,keepdim=True)
    m=mask.detach().float()
    assert m.shape==error.shape and torch.isfinite(m).all() and (m>=0).all() and (m<=1).all()
    obj=m.sum(); bg=(1-m).sum()
    assert obj>0 and bg>0
    o=float((error*m).sum()/obj); b=float((error*(1-m)).sum()/bg)
    return {'mse':float(error.mean()),'object_mse':o,'background_mse':b,'balanced_loss':o+b}


def branch_metrics(pred: Tensor, target: Tensor, z: Tensor, sigma: float | Tensor,
                   z0: Tensor, mask: Tensor) -> Record:
    """Data-noised states only; channel-mean errors match C006 balanced_loss."""
    result=_errors(pred,target,mask)
    clean=z.detach().float()-torch.as_tensor(sigma,device=z.device).float()*pred.detach().float()
    result['clean_estimate']=_errors(clean,z0,mask)
    return result


def _ratio(numerator: float, denominator: float) -> float | None:
    return numerator/denominator if denominator>NEAR_ZERO else None


def cfg_metrics(bp: Tensor, bn: Tensor, ap: Tensor, an: Tensor) -> Record:
    """All four inputs must share one pre-step state; native expressions keep dtype."""
    bp,bn,ap,an=(x.detach() for x in (bp,bn,ap,an))
    dp=ap.float()-bp.float(); dn=an.float()-bn.float()
    np_=float(torch.linalg.vector_norm(dp)); nn_=float(torch.linalg.vector_norm(dn))
    cosine=float((dp*dn).sum()/(np_*nn_)) if min(np_,nn_)>NEAR_ZERO else None
    result={'delta_plus_rms':rms(dp),'delta_minus_rms':rms(dn),'delta_difference_rms':rms(dp-dn),
            'delta_plus_norm':np_,'delta_minus_norm':nn_,'delta_cosine':cosine,'near_zero_threshold':NEAR_ZERO}
    for w in (1,5):
        # CFG1 actually returns positive directly; CFG5 follows installed separate-branch expression.
        b_native=bp if w==1 else bn+w*(bp-bn)
        a_native=ap if w==1 else an+w*(ap-an)
        b32=bp.float() if w==1 else bn.float()+w*(bp.float()-bn.float())
        a32=ap.float() if w==1 else an.float()+w*(ap.float()-an.float())
        delta=w*dp+(1-w)*dn
        result[f'cfg{w}']={'delta_rms':rms(delta),'delta_norm':float(torch.linalg.vector_norm(delta)),
            'base_rms':rms(b32),'relative_change':_ratio(rms(delta),rms(b32)),
            'base_native_minus_fp32':difference(b_native,b32),'adapter_native_minus_fp32':difference(a_native,a32),
            'actual_delta_minus_fp32_formula':difference(a_native.float()-b_native.float(),delta),
            'fp32_algebra_error':difference(a32-b32,delta),'native_dtype':str(b_native.dtype)}
    return result


def _tensor_stats(x: Tensor) -> Record:
    x=x.detach().float()
    norms=torch.linalg.vector_norm(x,dim=-1).reshape(-1)
    return {'rms':rms(x),'norm':float(torch.linalg.vector_norm(x)),
            'token_norm_p50':float(torch.quantile(norms,.5)),
            'token_norm_p95':float(torch.quantile(norms,.95)),'token_norm_max':float(norms.max())}


def _region(hidden: Tensor, residual: Tensor, cast: Tensor, effective: Tensor, selection: Tensor | None) -> Record:
    arrays=(hidden,residual,cast,effective)
    if selection is not None:
        if not bool(selection.any()):return {'tokens':0,'hidden':None,'residual_fp32':None,'residual_cast':None,'effective_update':None,'residual_hidden_ratio':None,'effective_hidden_ratio':None}
        arrays=tuple(x[selection] for x in arrays)
    h,r,c,e=arrays
    return {'tokens':h.numel()//h.shape[-1],'hidden':_tensor_stats(h),'residual_fp32':_tensor_stats(r),
            'residual_cast':_tensor_stats(c),'effective_update':_tensor_stats(e),
            'residual_hidden_ratio':_ratio(rms(r),rms(h)),'effective_hidden_ratio':_ratio(rms(e),rms(h))}


def geometric_support(condition) -> Tensor:
    """Exact C006 gate/kernel support, with nominal temporal-group union; no MLP."""
    q=condition.positions.detach().float()
    gate=condition.valid.bool() & condition.visible.bool() & torch.isfinite(q).all(-1)
    gate=gate & (q>=0).all(-1) & (q<=1).all(-1)
    q=torch.where(gate[...,None],q,torch.zeros_like(q))
    y,x=torch.meshgrid((torch.arange(15,device=q.device)+.5)/15,
                       (torch.arange(26,device=q.device)+.5)/26,indexing='ij')
    grid=torch.stack((x,y),-1).reshape(1,390,1,2)
    tau=torch.linspace(0,1,33,device=q.device)[:,None]
    boxes=condition.box_wh[[0,32]].detach().float()
    boxes=(1-tau)*boxes[0]+tau*boxes[1]
    width=torch.maximum(boxes*.08,q.new_tensor([1/26,1/15]))
    radius2=((grid-q[:,None,:,:])/width[:,None,None,:]).square().sum(-1)
    weights=torch.exp(-.5*radius2)*(radius2<=9)*gate[:,None,:]
    support=(weights>0).any(-1)
    grouped=torch.cat((support[:1],support[1:].reshape(8,4,390).any(1)),dim=0)
    return grouped.reshape(1,3510)


class ResidualObserver:
    """Capture each existing projection once, return original residual result unchanged.

    A forward prehook computes exact gate/kernel support without evaluating the MLP.
    Enter before adapter.forward so support belongs to the current PointCondition.
    Metadata is copied per record so callers may update branch/sigma between calls.
    """
    def __init__(self, adapter, metadata: Record, callback: Callable[[Record], None]) -> None:
        self.adapter=adapter; self.metadata=metadata; self.callback=callback
        self.geometric_support=None
        self.handles=[]; self.captured=None; self.original=None; self.had_instance=False; self.saved_instance=None

    def __enter__(self) -> 'ResidualObserver':
        self.original=self.adapter.residual
        self.had_instance='residual' in self.adapter.__dict__
        self.saved_instance=self.adapter.__dict__.get('residual')
        def capture_support(_module, args, kwargs):
            condition=args[0] if args else kwargs['condition']
            self.geometric_support=geometric_support(condition)
        self.handles.append(self.adapter.register_forward_pre_hook(capture_support,with_kwargs=True))
        for index,projection in enumerate(self.adapter.projections):
            def capture(_module,_inputs,output,index=index):
                self.captured=(index,output.detach())
            self.handles.append(projection.register_forward_hook(capture))
        def observe(context,block_index,hidden,enabled=True):
            self.captured=None
            try:
                output=self.original(context,block_index,hidden,enabled)
                if enabled:
                    assert self.captured is not None and self.captured[0]==block_index
                    residual=self.captured[1]
                    assert self.geometric_support is not None, 'Enter observer before adapter.forward'
                    support=self.geometric_support
                    assert support.shape==hidden.shape[:-1]
                    cast=residual.to(hidden.dtype)
                    effective=output.detach().float()-hidden.detach().float()
                    record={**self.metadata,'block_index':block_index,'dit_block_index':26+block_index,
                            'support_definition':'exact visible/valid finite inbounds gate; Gaussian weights>0 and radius2<=9; temporal group union',
                            'context_nonzero_tokens':int((context.detach().abs().sum(-1)>0).sum()),
                            'support_tokens':int(support.sum()),'full':_region(hidden,residual,cast,effective,None),
                            'support':_region(hidden,residual,cast,effective,support)}
                    self.callback(record)
                return output
            finally:
                self.captured=None
        self.adapter.residual=observe
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        for handle in self.handles:handle.remove()
        self.handles.clear(); self.captured=None; self.geometric_support=None
        if self.had_instance:self.adapter.residual=self.saved_instance
        else:delattr(self.adapter,'residual')
        self.original=None; self.saved_instance=None
