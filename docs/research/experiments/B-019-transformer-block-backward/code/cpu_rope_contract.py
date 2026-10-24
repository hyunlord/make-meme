"""CPU-only exact upstream function AST fixture; not full-package import/FA."""
import ast
import functools
import json
from pathlib import Path
import sys
import torch
import torch.nn.functional as F

source=Path(sys.argv[1]); output=Path(sys.argv[2])
names={'rope_params','rope_apply_ref','rope_apply_video','rope_apply_pose','rope_apply_additional_ref','rope_apply_scail'}
tree=ast.parse(source.read_text()); nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
assert {n.name for n in nodes}==names
for node in nodes:node.decorator_list=[]
namespace={'torch':torch,'F':F}
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),namespace)
generator=torch.Generator().manual_seed(20261024)
x=torch.randn(1,36,40,128,generator=generator,requires_grad=True)
freqs=torch.cat([namespace['rope_params'](8192,n) for n in (44,42,42)],dim=1)
kwargs=dict(freqs=freqs,ref_length=16,seq_length=16,pose_length=4,additional_ref_length=0,rope_T=1,rope_H=4,rope_W=4,rope_T_shift={'ref':0,'video':1,'pose':1},rope_H_shift={'ref':0,'video':0,'pose':0},rope_W_shift={'ref':0,'video':0,'pose':120})
y=namespace['rope_apply_scail'](x,**kwargs)
assert y.shape==x.shape and y.dtype==torch.float32 and torch.isfinite(y).all()
y.square().mean().backward();assert x.grad is not None and torch.isfinite(x.grad).all()
assert not torch.cuda.is_initialized()
output.write_text(json.dumps({'status':'PASS','classification':'CPU_AST_HELPER_ONLY_NOT_FA','input_shape':list(x.shape),'output_shape':list(y.shape),'freq_dtype':str(freqs.dtype),'finite_input_gradient':True,'cuda_initialized':False},indent=2))
