"""Lossless bounded tensor-tree handoff; never serialize executable objects."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import torch
from safetensors.torch import save_file,load_file


def atomic_json(path: Path, value: dict) -> None:
    temporary=path.with_suffix('.json.tmp')
    with temporary.open('x') as file:
        json.dump(value,file,indent=2);file.flush();os.fsync(file.fileno())
    os.replace(temporary,path)
    directory=os.open(path.parent,os.O_RDONLY)
    try:os.fsync(directory)
    finally:os.close(directory)


def save_tree(path: Path, tree, provenance: dict) -> None:
    tensors={}
    def flatten(value):
        if isinstance(value,torch.Tensor):
            key=f't{len(tensors)}';tensors[key]=value.detach().to('cpu',copy=True).contiguous()
            return {'tensor':key,'device':str(value.device)}
        if isinstance(value,list):return {'list':[flatten(item) for item in value]}
        if isinstance(value,dict):return {'dict':{key:flatten(item) for key,item in value.items()}}
        if value is None or isinstance(value,(str,int,float,bool)):return {'scalar':value}
        raise TypeError(type(value))
    structure=flatten(tree)
    if path.exists():raise FileExistsError(path)
    temporary=path.with_suffix('.safetensors.tmp')
    save_file(tensors,str(temporary))
    with temporary.open('rb') as file:os.fsync(file.fileno())
    restored=load_file(str(temporary))
    assert all(torch.equal(value,restored[key]) and value.dtype==restored[key].dtype for key,value in tensors.items())
    os.replace(temporary,path)
    hashes={key:{'shape':list(value.shape),'dtype':str(value.dtype),'sha256':hashlib.sha256(value.reshape(-1).view(torch.uint8).numpy().tobytes()).hexdigest()} for key,value in tensors.items()}
    atomic_json(path.with_suffix('.json'),{'structure':structure,'tensors':hashes,'file_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size,'provenance':provenance,'readback_exact':True})


def load_tree(path: Path, *, device: str | None=None):
    meta=json.loads(path.with_suffix('.json').read_text())
    assert hashlib.sha256(path.read_bytes()).hexdigest()==meta['file_sha256']
    values=load_file(str(path))
    for key,value in values.items():
        assert hashlib.sha256(value.reshape(-1).view(torch.uint8).numpy().tobytes()).hexdigest()==meta['tensors'][key]['sha256']
        assert list(value.shape)==meta['tensors'][key]['shape'] and str(value.dtype)==meta['tensors'][key]['dtype']
    def inflate(node):
        if 'tensor' in node:return values[node['tensor']].to(device or node['device'])
        if 'list' in node:return [inflate(item) for item in node['list']]
        if 'dict' in node:return {key:inflate(item) for key,item in node['dict'].items()}
        return node['scalar']
    return inflate(meta['structure']),meta
