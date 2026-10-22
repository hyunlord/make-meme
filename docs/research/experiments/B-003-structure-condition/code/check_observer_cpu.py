"""CPU-only observer identity test against the pinned upstream unit runner."""
import ast
import json
import sys
from pathlib import Path
from types import SimpleNamespace
import torch
from vace_observe import install_input_observer
source=Path(sys.argv[1])/'diffsynth/diffusion/base_pipeline.py'
node=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='PipelineUnitRunner')
namespace={'PipelineUnit':object,'BasePipeline':object}
exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),namespace)
class WanVideoUnit_VACE:
    take_over=False
    seperate_cfg=False
    input_params=('vace_context',)
    def process(self,pipe,vace_context): return {'vace_context':vace_context}
output=Path(sys.argv[2]);output.mkdir(parents=True,exist_ok=True)
pipe=SimpleNamespace(unit_runner=namespace['PipelineUnitRunner'](),model_fn=lambda:None)
install_input_observer(pipe,output)
x=torch.arange(1*96*6*2*2).reshape(1,96,6,2,2).float();saved=x.clone();rng=torch.get_rng_state().clone()
result=pipe.unit_runner(WanVideoUnit_VACE(),pipe,{'vace_context':x},{},{})
assert len(result)==3 and result[0]['vace_context'] is x
assert torch.equal(x,saved) and torch.equal(rng,torch.get_rng_state())
record=json.loads((output/'actual_input_hashes.jsonl').read_text().splitlines()[-1])
assert set(record['slices'])=={'reference_prefix','video_inactive','video_reactive','mask_all'}
assert record['slices']['reference_prefix']['shape']==[1,96,1,2,2]
print('PASS: actual unit-runner signature, tensor identity/value and CPU RNG unchanged; four slice hashes observed. CPU synthetic wiring only.')
