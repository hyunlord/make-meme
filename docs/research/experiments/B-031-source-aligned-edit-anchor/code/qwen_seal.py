# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Seal already-verified inputs/code/weights once, before preregistration."""
# Run: locked Python qwen_seal.py PRIVATE_B031_ROOT, after qwen_preflight.py.
import json
import sys
from pathlib import Path
from qwen_observe import file_hash

root = Path(sys.argv[1]).resolve()
verification_path = root/'environment/model-verification.json'
verification = json.loads(verification_path.read_text())
assert verification['status'] == 'PASS'
rows = []
for item in verification['files']:
    stat = (root/'models/qwen-image-edit-2511'/item['path']).stat()
    rows.append({'path':item['path'],'bytes':stat.st_size,'mtime_ns':stat.st_mtime_ns})
freeze = {'code_sha256':{path.name:file_hash(path) for path in sorted((root/'code').glob('qwen_*.py'))},'input_contract_sha256':file_hash(root/'inputs/INPUT_CONTRACT.json'),'model_verification_sha256':file_hash(verification_path),'environment_lock_sha256':file_hash(root/'environment/ENVIRONMENT_LOCK.json'),'model_file_stats':rows,'image_attempt_limit':6,'stop_heavy_utc':'2026-10-26T20:16:41Z','hard_deadline_utc':'2026-10-26T20:46:41Z'}
with (root/'environment/image-freeze.json').open('x') as stream:
    json.dump(freeze,stream,indent=2)
print('SEALED; require parent preregistration commit/push before execution')
