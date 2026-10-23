"""Create only new B015 worker directories; immutable parent P stays outside."""
from pathlib import Path
import shutil
import sys

root,environment_root=map(Path,sys.argv[1:])
for stage in ('PROBE','S','D'):
    target=root/'stages'/stage;target.mkdir(parents=True,exist_ok=False)
    (target/'reports').mkdir()
    for name in ('code','configs'):shutil.copytree(root/name,target/name)
    for name in ('environment','models','upstream'):(target/name).symlink_to(environment_root/name,target_is_directory=True)
    for name in ('inputs','artifacts','parent_records'):(target/name).symlink_to(root/name,target_is_directory=True)
    for name in ('PREREGISTERED_CODE.json','PREREGISTERED_INPUTS.json'):shutil.copy2(root/name,target/name)
