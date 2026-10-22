"""Official SCAIL attention wrapper only; tiny random BF16 CUDA forward, no model."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
import torch
from torch.nn.attention import sdpa_kernel, SDPBackend

wrapper, output = Path(sys.argv[1]), Path(sys.argv[2])
spec = importlib.util.spec_from_file_location('official_scail_attention', wrapper)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
report = {'wrapper_sha256': hashlib.sha256(wrapper.read_bytes()).hexdigest(), 'torch': torch.__version__, 'cuda': torch.version.cuda, 'device': torch.cuda.get_device_name(), 'cc': list(torch.cuda.get_device_capability()), 'fa2_available': module.FLASH_ATTN_2_AVAILABLE, 'fa3_available': module.FLASH_ATTN_3_AVAILABLE, 'scope': 'Tiny random attention only; no SCAIL weights/model/video/training', 'cases': []}
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, indent=2))
torch.manual_seed(20261022)
# Official 14B heads/dim; small lengths. Actual default wrapper backend selection is unchanged.
for label, lq, lk, valid_k in [('self-full',64,64,64), ('self-key-padding',64,64,48), ('image-cross',64,32,32), ('text-cross-padding',64,80,57)]:
    q = torch.randn((1,lq,40,128),device='cuda',dtype=torch.bfloat16)
    k = torch.randn((1,lk,40,128),device='cuda',dtype=torch.bfloat16)
    v = torch.randn_like(k)
    lengths = torch.tensor([valid_k], device='cuda', dtype=torch.int32)
    started = time.monotonic()
    with torch.inference_mode():
        actual = module.flash_attention(q,k,v,k_lens=lengths,causal=False,dropout_p=0.0,window_size=(-1,-1),deterministic=False)
        with sdpa_kernel(SDPBackend.MATH):
            expected = torch.nn.functional.scaled_dot_product_attention(q.float().transpose(1,2), k[:,:valid_k].float().transpose(1,2), v[:,:valid_k].float().transpose(1,2),dropout_p=0.0,is_causal=False).transpose(1,2)
    torch.cuda.synchronize()
    delta = (actual.float()-expected).abs()
    passed = actual.shape==q.shape and bool(torch.isfinite(actual).all()) and torch.allclose(actual.float(),expected,atol=0.01,rtol=0.02)
    report['cases'].append({'case':label,'q_shape':list(q.shape),'k_shape':list(k.shape),'valid_k':valid_k,'dtype':str(actual.dtype),'finite':bool(torch.isfinite(actual).all()),'max_abs_error':float(delta.max()),'mean_abs_error':float(delta.mean()),'rmse':float(torch.sqrt(torch.mean(delta**2))),'atol':0.01,'rtol':0.02,'pass':passed,'seconds':time.monotonic()-started})
    output.write_text(json.dumps(report,indent=2))
report['all_pass']=all(row['pass'] for row in report['cases'])
report['peak_allocated']=torch.cuda.max_memory_allocated()
output.write_text(json.dumps(report,indent=2));print(json.dumps(report));assert report['all_pass']
