# /// script
# requires-python = ">=3.12"
# dependencies = ["torch", "safetensors", "pydantic"]
# ///
"""Run: existing Python code/preflight.py ROOT. CPU-only actual provenance checks."""
from pathlib import Path
import hashlib
import json
import sys
import torch
from safetensors.torch import load_file
from artifacts import atomic_json
from lora_component import AdapterSchema
root=Path(sys.argv[1]);producer=(root/'producer').resolve()
def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
parent=json.loads((producer/'PREREGISTERED_CODE.json').read_text())
assert parent['experiment']=='B-020'
for name,digest in parent['files'].items():assert sha(producer/name)==digest,name
schema=AdapterSchema.model_validate_json((producer/'artifacts/adapter-initial.json').read_text())
assert schema.provenance['experiment']=='B-020'
assert schema.provenance['code_sha256']==sha(producer/'PREREGISTERED_CODE.json')
initial=producer/'artifacts/adapter-initial.safetensors'
assert sha(initial)==schema.payload_sha256
values=load_file(str(initial),device='cpu')
assert set(values)=={'q.lora_A','q.lora_B','v.lora_A','v.lora_B'}
for key,value in values.items():
    assert value.dtype==torch.float32 and torch.isfinite(value).all()
    assert list(value.shape)==([4,5120] if key.endswith('A') else [5120,4])
    if key.endswith('B'):assert torch.count_nonzero(value)==0
parameter=torch.nn.Parameter(torch.zeros(1))
optimizer=torch.optim.AdamW([parameter],lr=1e-4,weight_decay=0)
options={k:v for k,v in optimizer.param_groups[0].items() if k!='params'}
receipt=json.loads((producer/'artifacts/prefix_receipt.json').read_text())
assets={}
for row in receipt['tuples']:
    for suffix,digestkey in (('.safetensors','file_sha256'),('.json','sidecar_sha256')):
        path=producer/'artifacts'/('prefix-'+row['tuple_id']+suffix)
        assert sha(path)==row[digestkey]
        assets[path.name]=row[digestkey]
for name in ('target.safetensors','target.json','conditions.safetensors','conditions.json','conditions_receipt.json','initial_noise.pt','prefix_receipt.json','training_receipt.json','adapter-initial.safetensors','adapter-initial.json','adapter-final.safetensors','adapter-final.json'):
    assets[name]=sha(producer/'artifacts'/name)
atomic_json(root/'reports/cpu-preflight.json',{'status':'PASS','cuda_initialized':torch.cuda.is_initialized(),'producer':'B-020','consumer':'B-021','producer_code_sha256':sha(producer/'PREREGISTERED_CODE.json'),'initial_adapter_sha256':sha(initial),'initial_tensors':{k:{'sha256':hashlib.sha256(v.view(torch.uint8).numpy().tobytes()).hexdigest(),'shape':list(v.shape),'dtype':str(v.dtype),'norm':float(v.norm()),'nonzero':int(torch.count_nonzero(v))} for k,v in values.items()},'optimizer_options':options,'assets':assets,'replay_tolerance':{'atol':1e-7,'rtol':1e-5},'split_reload_off_tolerance':{'atol':1e-3,'rtol':1e-3},'budgets':{'updates':100,'train_workers':1,'evaluation_forwards':18,'evaluation_hard_cap':20,'probe':1,'sampler':1,'decode':1,'P':0,'prefix_forwards':0,'retries':0}})
print(json.dumps({'status':'PASS','options':options,'initial_sha256':sha(initial),'cuda_initialized':torch.cuda.is_initialized()}))
