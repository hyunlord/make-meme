# /// script
# requires-python = ">=3.12"
# dependencies = ["torch", "safetensors", "diffusers"]
# ///
"""Executed tiny official SCAIL constructor/load fixture; no pretrained weights."""
# Run: PYTHONPATH=CODE:UPSTREAM python runtime_loader_fixture.py OUTPUT_DIRECTORY
from pathlib import Path
import json,os,sys
import torch
from safetensors.torch import save_file
from wan.modules.model_scail2 import SCAIL2Model
import runtime_loader

root=Path(sys.argv[1]);root.mkdir(parents=True,exist_ok=True)
torch.manual_seed(20261022)
model=SCAIL2Model(model_type='i2v',dim=128,ffn_dim=256,num_heads=1,num_layers=1,freq_dim=32)
model.save_config(root)
state=model.state_dict();save_file(state,str(root/'tiny.safetensors'))
policy=runtime_loader.parameter_dtype
runtime_loader.parameter_dtype=lambda name: state[name].dtype
os.environ['B007B_LOADER_REPORT']=str(root/'source-loader.json')
exact=runtime_loader.load_model(str(root/'config.json'),str(root/'tiny.safetensors'))
assert all(torch.equal(exact.state_dict()[k],v) for k,v in state.items())
assert torch.equal(exact.freqs,model.freqs)
runtime_loader.parameter_dtype=policy
os.environ['B007B_LOADER_REPORT']=str(root/'mixed-loader.json')
mixed=runtime_loader.load_model(str(root/'config.json'),str(root/'tiny.safetensors'))
assert all(torch.equal(mixed.state_dict()[k],v.to(policy(k))) for k,v in state.items())
assert mixed.img_emb.proj[0].weight.dtype==mixed.img_emb.proj[4].weight.dtype==torch.float32
assert all(p.dtype==torch.float32 for p in mixed.time_embedding.parameters())
assert all(p.dtype==torch.float32 for p in mixed.time_projection.parameters())
assert all(p.dtype==torch.float32 for p in mixed.head.parameters())
with torch.no_grad(),torch.autocast('cpu',dtype=torch.bfloat16):
    image=mixed.img_emb(torch.randn(1,4,1280))
with torch.no_grad():
    time=mixed.time_embedding(torch.randn(1,32))
    projection=mixed.time_projection(time)
    head=mixed.head(torch.randn(1,4,128),time)
assert all(bool(torch.isfinite(t).all()) for t in (image,time,projection,head))
error=max(float((v.float()-mixed.state_dict()[k].float()).abs().max()) for k,v in state.items())
report={'scope':'random tiny actual SCAIL modules; no pretrained/full video forward','same_dtype_values_exact':True,'same_dtype_rope_exact':True,'mixed_cast_exact':True,'max_bf16_cast_abs_error':error,'img_emb_norm_dtype':'float32','img_emb_output_shape':list(image.shape),'time_output_shape':list(time.shape),'head_output_shape':list(head.shape),'islands_finite':True,'parameter_count':sum(p.numel() for p in model.parameters())}
(root/'fixture_result.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
