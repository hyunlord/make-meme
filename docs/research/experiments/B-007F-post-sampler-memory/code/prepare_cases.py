"""Create isolated case roots, preserving E source/environment/assets read-only."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
from runtime_patch import patch


def prepare(previous: Path, root: Path) -> None:
    for case in ('official','lab'):
        target=root/'cases'/case
        target.mkdir(parents=True,exist_ok=False)
        (target/'reports').mkdir()
        (target/'outputs').mkdir()
        for name in ('code','configs'):
            shutil.copytree(root/name,target/name)
        for name in ('environment','models','inputs'):
            (target/name).symlink_to(previous/name,target_is_directory=True)
        shutil.copytree(previous/'upstream',target/'upstream',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        source=(previous/'upstream/wan/scail.py').read_text()
        changed=patch(source)
        (target/'upstream/wan/scail.py').write_text(changed)
        for name in ('PREREGISTERED_INPUTS.json','PREREGISTERED_CODE.json'):
            shutil.copy2(root/name,target/name)
        shutil.copy2(previous/'configs/allowed_gpu_processes.json',target/'configs/allowed_gpu_processes.json')
        manifest={str(path.relative_to(target/'upstream')):hashlib.sha256(path.read_bytes()).hexdigest() for path in (target/'upstream').rglob('*.py')}
        (target/'reports/source_hashes.json').write_text(json.dumps(manifest,indent=2))
    print('Two isolated case roots prepared; no models loaded')

if __name__=='__main__':
    prepare(Path(sys.argv[1]),Path(sys.argv[2]))
