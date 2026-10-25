"""Freeze source/config/input bindings before any encoder or sampler worker."""
from pathlib import Path
import hashlib
import json
import sys
root=Path(sys.argv[1]);producer=(root/'producer').resolve()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
original=json.loads((producer/'PREREGISTERED_CODE.json').read_text())
files={str(p.relative_to(root)):sha(p) for folder in ('code','configs') for p in sorted((root/folder).iterdir()) if p.suffix in ('.py','.json')}
manifest={'experiment':'B-025','producer':'B-024','producer_code_sha256':sha(producer/'PREREGISTERED_CODE.json'),'deadline_utc':'2026-10-25T15:10:00Z','files':files,'upstream':original['upstream'],'producer_receipt_sha256':sha(producer/'artifacts/conditions_receipt.json'),'stage_execution':{},'stage_config_hashes':{}}
for stage in sorted((root/'stages').iterdir()):
    manifest['stage_execution'][stage.name]=json.loads((stage/'configs/execution.json').read_text())
    manifest['stage_config_hashes'][stage.name]={p.name:sha(p) for p in (stage/'configs').glob('*.json')}
with (root/'PREREGISTERED_CODE.json').open('x') as stream:json.dump(manifest,stream,indent=2)
print(sha(root/'PREREGISTERED_CODE.json'))
