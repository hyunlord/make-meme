"""Copy frozen execution code into two isolated cases; preserve prepared inputs."""
from pathlib import Path
import shutil
import sys
root,previous=map(Path,sys.argv[1:])
for case in ('MOV','STILL'):
    target=root/'cases'/case
    assert (target/'inputs').is_dir()
    (target/'reports').mkdir(exist_ok=True);(target/'artifacts').mkdir(exist_ok=True)
    shutil.copytree(root/'code',target/'code')
    shutil.copytree(root/'configs'/case,target/'configs')
    shutil.copy2(previous/'configs/allowed_gpu_processes.json',target/'configs/allowed_gpu_processes.json')
    for name in ('environment','models','upstream'):(target/name).symlink_to(previous/name,target_is_directory=True)
    for name in ('PREREGISTERED_CODE.json','PREREGISTERED_INPUTS.json'):shutil.copy2(root/name,target/name)
    for stage in ('P','PROBE','S','D'):
        worker=target/'stages'/stage;(worker/'reports').mkdir(parents=True)
        for name in ('code','configs'):shutil.copytree(target/name,worker/name)
        for name in ('environment','models','upstream','inputs','artifacts'):(worker/name).symlink_to(target/name,target_is_directory=True)
        for name in ('PREREGISTERED_CODE.json','PREREGISTERED_INPUTS.json'):shutil.copy2(root/name,worker/name)
