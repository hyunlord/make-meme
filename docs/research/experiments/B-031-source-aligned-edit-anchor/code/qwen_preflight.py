# /// script
# requires-python = ">=3.12"
# dependencies = ["torch", "diffusers==0.41.0", "transformers==5.20.1"]
# ///
"""CPU-only pinned model/package integrity report before image attempts."""
# Run: locked Python qwen_preflight.py PRIVATE_B031_ROOT
import hashlib
import importlib.metadata
import inspect
import json
import sys
from pathlib import Path
from diffusers import QwenImageEditPlusPipeline
from diffusers.models.transformers import transformer_qwenimage
from diffusers.models import attention_dispatch
from qwen_observe import file_hash
from qwen_contract import ImageContract

root = Path(sys.argv[1]).resolve()
model = root/'models/qwen-image-edit-2511'
entries = json.loads((root/'environment/model-tree.json').read_text())
files = [item for item in entries if item['type']=='file']
assert sum(item['size'] for item in files) < 70*1024**3
verified = []
for item in files:
    path = model/item['path']
    assert path.stat().st_size == item['size'], path.name
    digest = file_hash(path)
    if 'lfs' in item:
        assert digest == item['lfs']['oid'], path.name
    else:
        payload = path.read_bytes()
        git_hash = hashlib.sha1(b'blob '+str(len(payload)).encode()+b'\x00'+payload).hexdigest()
        assert git_hash == item['oid'], path.name
    verified.append({'path':item['path'],'bytes':item['size'],'sha256':digest})
report = {'revision':'6f3ccc0b56e431dc6a0c2b2039706d7d26f22cb9','total_bytes':sum(item['size'] for item in files),'files':verified,'status':'PASS'}
(root/'environment/model-verification.json').write_text(json.dumps(report,indent=2))
modules = {'pipeline':inspect.getfile(QwenImageEditPlusPipeline),'transformer':inspect.getfile(transformer_qwenimage),'attention_dispatch':inspect.getfile(attention_dispatch)}
versions = {name:importlib.metadata.version(name) for name in ['torch','diffusers','transformers','accelerate','huggingface-hub','safetensors','pydantic','numpy','pillow']}
lock = {'packages':versions,'source_sha256':{key:file_hash(Path(value)) for key,value in modules.items()},'pipeline_signature':str(inspect.signature(QwenImageEditPlusPipeline.__call__)),'attention_backend':'native','reuse_policy':'separate venv plus read-only existing package sites; no package upgrade','model_revision':report['revision']}
(root/'environment/ENVIRONMENT_LOCK.json').write_text(json.dumps(lock,indent=2))
contract = ImageContract.model_validate_json((root/'inputs/INPUT_CONTRACT.json').read_text())
contract.check_order()
for case in contract.cases:
    contract.checked_images(root,case)
print(json.dumps({'status':'PASS','files':len(verified),'total_bytes':report['total_bytes'],'versions':versions}))
