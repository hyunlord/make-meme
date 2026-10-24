"""CPU/meta module fixture; bypasses only package initializers in this process.

This is not proof of the full wan package import; T5's package initializer calls
CUDA current_device. Actual S still checks canonical loaded-class/file globals.
No fake package is ever installed in a GPU worker.
"""
from pathlib import Path
from types import ModuleType
import hashlib
import inspect
import json
import sys
import torch

root=Path(sys.argv[1])
sys.path.insert(0,str(root/'code'))
from contracts import verify_cache_receipt
from artifacts import load_tree
receipt=verify_cache_receipt(root)
_,meta=load_tree(root/'artifacts/conditions.safetensors',device='cpu')
assert len(meta['tensors'])==16
for name,relative in (('wan','wan'),('wan.modules','wan/modules')):
    package=ModuleType(name);package.__path__=[str(root/'upstream'/relative)];sys.modules[name]=package
import importlib
original=importlib.import_module('wan.modules.model_scail2')
with torch.device('meta'):old=original.SCAIL2Model.from_config(str(root/'upstream/configs/config-14b.json'))
old_state={k:(list(v.shape),str(v.dtype)) for k,v in old.state_dict().items()};del old
from rope_runtime import install
patched=install(root)
actual=importlib.import_module('wan.modules.model_scail2')
assert actual.SCAIL2Model is patched.SCAIL2Model
with torch.device('meta'):new=actual.SCAIL2Model.from_config(str(root/'upstream/configs/config-14b.json'))
new_state={k:(list(v.shape),str(v.dtype)) for k,v in new.state_dict().items()}
assert old_state==new_state
assert Path(inspect.getfile(type(new))).resolve()==(root/'patched/model_scail2.py').resolve()
assert new.forward.__globals__['rope_apply_scail'] is patched.rope_apply_scail
assert not torch.cuda.is_initialized()
report={'status':'PASS','scope':'CPU_META_ONLY_MODULE_FIXTURE_NOT_FULL_PACKAGE_IMPORT','package_initializers_bypassed_in_fixture_only':True,'state_keys':len(new_state),'parameter_count':sum(p.numel() for p in new.parameters()),'state_shape_dtype_exact':True,'actual_canonical_class_match':True,'actual_forward_globals_match':True,'patched_module_sha256':hashlib.sha256((root/'patched/model_scail2.py').read_bytes()).hexdigest(),'parent_cache_sha256':meta['file_sha256'],'parent_16_leaf_integrity':'PASS','cuda_initialized':False}
(root/'reports/cpu-module-parent-audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
