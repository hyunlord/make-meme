"""Reuse and validate immutable B031 producer, then exact copied cache bytes."""
from pathlib import Path
import importlib.util
import hashlib
import json
import sys


def parent_module(root:Path):
    binding=json.loads((root/'configs/b033_binding.json').read_text())
    parent=Path(binding['parent_worker']);code=parent/'code'
    spec=importlib.util.spec_from_file_location('b033_parent_contracts',code/'contracts.py')
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module
    sys.path.append(str(code));spec.loader.exec_module(module)
    return parent,module


def active_contract(root:Path):
    parent,module=parent_module(root)
    result=module.active_contract(parent)
    assert json.loads((root/'configs/public.json').read_text())==json.loads((parent/'configs/public.json').read_text())
    return result


def verify_cache_receipt(root:Path)->dict:
    parent,module=parent_module(root);receipt=module.verify_cache_receipt(parent)
    for name,digest in receipt['hashes'].items():
        assert hashlib.sha256((root/'artifacts'/name).read_bytes()).hexdigest()==digest
    return receipt
