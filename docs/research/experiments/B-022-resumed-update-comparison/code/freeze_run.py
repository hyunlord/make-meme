# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""CPU-only one-time preregistration: python code/freeze_run.py ROOT."""
from pathlib import Path
import hashlib
import json
import sys
root=Path(sys.argv[1]);parent=(root/'resume_parent').resolve();producer=(root/'producer').resolve()
original=json.loads((producer/'PREREGISTERED_CODE.json').read_text())
files={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('code','configs') for p in sorted((root/folder).iterdir()) if p.suffix in ('.py','.json')}
manifest={'experiment':'B-022','producer':'B-020','resume_parent':'B-021','producer_code_sha256':hashlib.sha256((producer/'PREREGISTERED_CODE.json').read_bytes()).hexdigest(),'resume_code_sha256':hashlib.sha256((parent/'PREREGISTERED_CODE.json').read_bytes()).hexdigest(),'deadline_utc':'2026-10-24T17:10:00Z','files':files,'upstream':original['upstream'],'stage_execution':{stage.name:json.loads((stage/'configs/execution.json').read_text()) for stage in sorted((root/'stages').iterdir()) if stage.is_dir()}}
with (root/'PREREGISTERED_CODE.json').open('x') as stream:json.dump(manifest,stream,indent=2)
print(hashlib.sha256((root/'PREREGISTERED_CODE.json').read_bytes()).hexdigest())
