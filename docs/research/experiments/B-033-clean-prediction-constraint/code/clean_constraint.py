"""One clean-prediction seam; no model, CFG or UniPC history changes."""
from pathlib import Path
import json
import torch
import torch.nn.functional as F
from wan.utils.fm_solvers_unipc import FlowUniPCMultistepScheduler


def latent_mask(edit: torch.Tensor) -> torch.Tensor:
    assert list(edit.shape)==[17,512,896] and edit.dtype==torch.float32
    assert bool(torch.isfinite(edit).all()) and float(edit.min())>=0 and float(edit.max())<=1
    groups=torch.stack([edit[0],*[edit[i:i+4].amax(0) for i in (1,5,9,13)]])
    spatial=F.max_pool2d(groups[:,None],8,8)
    dilated=F.max_pool2d(spatial,3,1,1)
    return dilated[:,0][None,None].contiguous()


def mix_clean(clean:torch.Tensor,source:torch.Tensor,mask:torch.Tensor)->torch.Tensor:
    assert source.ndim==4 and mask.ndim==5 and list(mask.shape[:2])==[1,1]
    assert clean.ndim in (4,5)
    src=source if clean.ndim==4 else source[None]
    free=mask[0] if clean.ndim==4 else mask
    assert src.shape==clean.shape and tuple(free.shape[-3:])==tuple(clean.shape[-3:])
    src=src.to(device=clean.device,dtype=clean.dtype);free=free.to(device=clean.device,dtype=clean.dtype)
    mixed=free*clean+(1-free)*src
    return torch.where(free==0,src,torch.where(free==1,clean,mixed))


class CleanConstraintScheduler(FlowUniPCMultistepScheduler):
    def bind(self,source:torch.Tensor,mask:torch.Tensor,trace:Path|None=None)->None:
        assert self.predict_x0 and self.config.prediction_type=='flow_prediction'
        assert not self.config.thresholding and self.solver_p is None
        assert self.config.lower_order_final and float(self.sigmas[-1])==0
        assert bool(torch.isfinite(source).all()) and bool(torch.isfinite(mask).all())
        assert float(mask.min())>=0 and float(mask.max())<=1
        self.source=source;self.free=mask;self.trace=trace;self.constraint_calls=0

    def convert_model_output(self,model_output:torch.Tensor,*,sample:torch.Tensor)->torch.Tensor:
        clean=super().convert_model_output(model_output,sample=sample)
        if not hasattr(self,'source'):
            return clean
        result=mix_clean(clean,self.source,self.free)
        assert result.dtype==clean.dtype and bool(torch.isfinite(result).all())
        self.constraint_calls+=1
        if self.trace is not None:
            delta=(result-clean).float()
            row={'step_index':self.step_index,'sigma':float(self.sigmas[self.step_index]),'dtype':str(clean.dtype),'shape':list(clean.shape),'device':str(clean.device),'finite':True,'delta_rms':float(delta.square().mean().sqrt()),'delta_max':float(delta.abs().max()),'conversion_calls':self.constraint_calls}
            with self.trace.open('a') as stream:stream.write(json.dumps(row)+'\n')
        return result
