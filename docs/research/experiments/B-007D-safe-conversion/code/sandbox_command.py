"""Exact nonroot Docker security boundary; only explicitly listed binds."""
from pathlib import Path

IMAGE='sha256:b19473a50fba63e5b9f171724facaaebd0ac6c5149261b99af23f1f645b45d40'


def command(name: str, output: Path, mounts: dict[str,str], script: str, args: list[str], memory_bytes: int=2*1024**3) -> list[str]:
    assert name.startswith('make-meme-b007d-') and 0<memory_bytes<=80*1024**3
    argv=['docker','run','--name='+name,'--runtime=runc','--network=none','--read-only','--user=1000:1000','--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit=64','--memory='+str(memory_bytes),'--memory-swap='+str(memory_bytes),'--cpus=2','--entrypoint=/usr/bin/env']
    for source,target in mounts.items():
        assert Path(source).exists() and source not in ('/','/home','/root',str(Path.home()),'/var/run/docker.sock')
        argv.extend(['--mount',f'type=bind,source={source},target={target},readonly'])
    argv.extend(['--mount',f'type=bind,source={output},target=/output'])
    argv.extend([IMAGE,'-i','PATH=/usr/bin:/bin','HOME=/output/home','TMPDIR=/output/tmp','PYTHONPATH=/code:/env/b007b:/env/b007a:/env/b001:/env/base','PYTHONDONTWRITEBYTECODE=1','CUDA_VISIBLE_DEVICES=','OMP_NUM_THREADS=1','OPENBLAS_NUM_THREADS=1','MKL_NUM_THREADS=1','/usr/bin/python3.12','-S',script,*args])
    return argv
