# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run using the existing pinned SCAIL environment; do not install dependencies.
"""Freeze actual task files and code before any encoder or sampler worker."""
from pathlib import Path
import hashlib
import json
import sys
root=Path(sys.argv[1])
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
files={str(path.relative_to(root)):sha(path) for folder in ('code','configs') for path in sorted((root/folder).iterdir()) if path.suffix in ('.py','.json','.sh')}
files['task_manifest.json']=sha(root/'task_manifest.json')
files['PREREGISTERED_INPUTS.json']=sha(root/'PREREGISTERED_INPUTS.json')
manifest={'experiment':'B-031','deadline_utc':'2026-10-26T20:16:41Z','files':files,'upstream':json.loads((root/'configs/pinned_upstream.json').read_text()),'stage_execution':{},'stage_config_hashes':{}}
for stage in sorted((root/'stages').iterdir()):
    manifest['stage_execution'][stage.name]=json.loads((stage/'configs/execution.json').read_text())
    manifest['stage_config_hashes'][stage.name]={path.name:sha(path) for path in (stage/'configs').glob('*.json')}
with (root/'PREREGISTERED_CODE.json').open('x') as stream:json.dump(manifest,stream,indent=2)
print(sha(root/'PREREGISTERED_CODE.json'))
