"""Isolated B-011 stages; new cache, read-only E environment/models/inputs."""
from pathlib import Path
import shutil
import sys
root,previous=map(Path,sys.argv[1:])
(root/'artifacts').mkdir(exist_ok=True)
for stage in ('P','PROBE','S','D'):
    target=root/'stages'/stage;target.mkdir(parents=True,exist_ok=False)
    (target/'reports').mkdir()
    for name in ('code','configs'):shutil.copytree(root/name,target/name)
    for name in ('environment','models','upstream'):(target/name).symlink_to(previous/name,target_is_directory=True)
    (target/'inputs').symlink_to(root/'inputs',target_is_directory=True)
    (target/'artifacts').symlink_to(root/'artifacts',target_is_directory=True)
    for name in ('PREREGISTERED_CODE.json','PREREGISTERED_INPUTS.json'):shutil.copy2(root/name,target/name)
    shutil.copy2(previous/'configs/allowed_gpu_processes.json',target/'configs/allowed_gpu_processes.json')
