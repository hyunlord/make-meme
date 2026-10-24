# /// script
# requires-python = ">=3.12"
# dependencies = ["torch", "safetensors"]
# ///
"""Run existing Python code/preflight.py ROOT. No CUDA/model execution."""
from pathlib import Path
import hashlib
import json
import sys
import torch
from safetensors.torch import load_file
from artifacts import atomic_json
from resume_contract import checkpoint,ORDER
root=Path(sys.argv[1]);parent=(root/'resume_parent').resolve();producer=(root/'producer').resolve()
consumer=json.loads((root/'configs/consumer.json').read_text())
assert hashlib.sha256((parent/'artifacts/restart-020.json').read_bytes()).hexdigest()==consumer['restart_sidecar_sha256']
assert hashlib.sha256((parent/'artifacts/adapter-020.json').read_bytes()).hexdigest()==consumer['adapter20_sidecar_sha256']
tree,meta=checkpoint(parent/'artifacts/restart-020.safetensors',consumer['restart_sha256'])
path=parent/'artifacts/adapter-020.safetensors';assert hashlib.sha256(path.read_bytes()).hexdigest()==consumer['adapter20_sha256']
values=load_file(str(path),device='cpu')
assert all(torch.equal(tree['adapter'][key],values[key.replace('.','.lora_')]) for key in ORDER)
assert meta['provenance']['experiment']=='B-021'
producer_manifest=json.loads((producer/'PREREGISTERED_CODE.json').read_text())
for name,digest in producer_manifest['files'].items():assert hashlib.sha256((producer/name).read_bytes()).hexdigest()==digest,name
for name,digest in consumer['assets'].items():assert hashlib.sha256((producer/'artifacts'/name).read_bytes()).hexdigest()==digest,name
assert not torch.cuda.is_initialized()
atomic_json(root/'reports/cpu-preflight.json',{'status':'PASS','cuda_initialized':False,'producer':'B-020','resume_parent':'B-021','consumer':'B-022','restart_sha256':consumer['restart_sha256'],'adapter_sha256':consumer['adapter20_sha256'],'order':list(ORDER),'step':tree['step'],'cursor':tree['tuple_cursor'],'next_tuple':'train_2','tensor_dtype':{k:str(v.dtype) for k,v in tree['adapter'].items()},'budgets':consumer['budgets']})
print('B022 actual checkpoint CPU preflight PASS')
