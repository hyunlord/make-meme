# /// script
# requires-python = ">=3.12"
# dependencies = ["diffusers==0.41.0"]
# ///
"""Bind runtime to pre-registered code, environment, inputs and verified weights."""
# Run: imported by qwen_runner.py; freeze created only before preregistration.
import inspect
import importlib.metadata
import json
from pathlib import Path
from diffusers import QwenImageEditPlusPipeline
from diffusers.models.transformers import transformer_qwenimage
from diffusers.models import attention_dispatch
from qwen_observe import file_hash


def verify_freeze(root: Path) -> None:
    """Fail closed on changed code/package/input/verified-file identities."""
    freeze = json.loads((root/'environment/image-freeze.json').read_text())
    for name,digest in freeze['code_sha256'].items():
        assert file_hash(root/'code'/name) == digest, name
    assert file_hash(root/'inputs/INPUT_CONTRACT.json') == freeze['input_contract_sha256']
    assert file_hash(root/'environment/model-verification.json') == freeze['model_verification_sha256']
    assert file_hash(root/'environment/ENVIRONMENT_LOCK.json') == freeze['environment_lock_sha256']
    verification = json.loads((root/'environment/model-verification.json').read_text())
    assert verification['status'] == 'PASS' and verification['revision'] == '6f3ccc0b56e431dc6a0c2b2039706d7d26f22cb9'
    environment = json.loads((root/'environment/ENVIRONMENT_LOCK.json').read_text())
    for name,version in environment['packages'].items():
        assert importlib.metadata.version(name) == version, name
    modules = {'pipeline':inspect.getfile(QwenImageEditPlusPipeline),'transformer':inspect.getfile(transformer_qwenimage),'attention_dispatch':inspect.getfile(attention_dispatch)}
    for name,path in modules.items():
        assert file_hash(Path(path)) == environment['source_sha256'][name], name
    for row in freeze['model_file_stats']:
        stat = (root/'models/qwen-image-edit-2511'/row['path']).stat()
        assert stat.st_size == row['bytes'] and stat.st_mtime_ns == row['mtime_ns'], row['path']
