"""CPU actual-cache 4/12 audit; frozen outcome is required by all new workers."""
from __future__ import annotations
from pathlib import Path
from collections.abc import Collection
from typing import TypedDict
import hashlib
import json
import sys
import torch
from safetensors.torch import load_file
from artifacts import load_tree,atomic_json
from contracts import verify_cache_receipt


class TreeNode(TypedDict, total=False):
    tensor: str
    dict: dict[str, TreeNode]
    list: list[TreeNode]
    scalar: str | int | float | bool | None
    device: str

class TensorInfo(TypedDict):
    sha256: str

class Provenance(TypedDict):
    parent_cache_sha256: str
    filter_code_sha256: str
    parent_ref_sha256: str
    filtered_ref_sha256: str

class Metadata(TypedDict):
    file_sha256: str
    structure: TreeNode
    tensors: dict[str, TensorInfo]
    provenance: Provenance

class Policy(TypedDict):
    moving_parent: str
    ALG_MOV: str
    old_cache_sha256: str
    changed_paths: list[str]
    unchanged_count: int
    filter_code_sha256: str
    original_ref_value_sha256: str
    filtered_ref_value_sha256: str
    old_filtered_metadata_sha256: str

class Receipt(TypedDict):
    hashes: dict[str, str]

class Row(TypedDict):
    location: str
    same: bool
    shape: list[int]
    dtype: str
    MOV_value_sha256: str
    STILL_value_sha256: str
    max_abs: float


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_metadata(path: Path) -> Metadata:
    # Keep the existing payload, dtype and shape validation before typed JSON use.
    _ = load_tree(path, device='cpu')
    result: Metadata = json.loads(path.with_suffix('.json').read_text())
    return result


def check_pair_leaf(name: str, moving: torch.Tensor, still: torch.Tensor, changed_paths: Collection[str]) -> bool:
    assert moving.shape==still.shape and moving.dtype==still.dtype,name
    same=torch.equal(moving,still)
    assert same == (name not in changed_paths),name
    return same


def locations(node: TreeNode, path: str='root') -> dict[str, str]:
    if 'tensor' in node:return {path:node['tensor']}
    if 'dict' in node:
        return {k:v for name,value in node['dict'].items() for k,v in locations(value,path+'.'+name).items()}
    if 'list' in node:
        return {k:v for i,value in enumerate(node['list']) for k,v in locations(value,path+'['+str(i)+']').items()}
    return {}


def main(root:Path) -> None:
    policy: Policy = json.loads((root/'configs/pair_baseline.json').read_text())
    _ = verify_cache_receipt(root)
    receipt: Receipt = json.loads((root/'artifacts/conditions_receipt.json').read_text())
    moving=root.parent/policy['moving_parent'];old=root.parent/policy['ALG_MOV']
    mov_meta=checked_metadata(moving/'artifacts/conditions.safetensors')
    still_meta=checked_metadata(root/'artifacts/conditions.safetensors')
    assert mov_meta['file_sha256']==policy['old_cache_sha256']
    assert still_meta['file_sha256']==receipt['hashes']['conditions.safetensors']
    assert mov_meta['structure']==still_meta['structure']
    mov=load_file(str(moving/'artifacts/conditions.safetensors'));still=load_file(str(root/'artifacts/conditions.safetensors'))
    paths=locations(mov_meta['structure']);assert len(paths)==16
    rows: list[Row]=[]
    for path,key in paths.items():
        same=check_pair_leaf(path,mov[key],still[key],policy['changed_paths'])
        rows.append({'location':path,'same':same,'shape':list(mov[key].shape),'dtype':str(mov[key].dtype),
          'MOV_value_sha256':mov_meta['tensors'][key]['sha256'],'STILL_value_sha256':still_meta['tensors'][key]['sha256'],
          'max_abs':float((mov[key].double()-still[key].double()).abs().max())})
    assert sum(row['same'] for row in rows)==policy['unchanged_count']==12
    new_meta=checked_metadata(root/'artifacts/filtered_reference.safetensors')
    old_meta=checked_metadata(old/'artifacts/filtered_reference.safetensors')
    new_filter=load_file(str(root/'artifacts/filtered_reference.safetensors'))
    old_filter=load_file(str(old/'artifacts/filtered_reference.safetensors'))
    new_key=locations(new_meta['structure'])['root.reference']
    old_key=locations(old_meta['structure'])['root.reference']
    assert torch.equal(new_filter[new_key],old_filter[old_key])
    assert new_meta['provenance']['parent_cache_sha256']==still_meta['file_sha256']
    assert old_meta['provenance']['parent_cache_sha256']==mov_meta['file_sha256']
    assert new_meta['provenance']['filter_code_sha256']==old_meta['provenance']['filter_code_sha256']==policy['filter_code_sha256']
    assert new_meta['provenance']['parent_ref_sha256']==old_meta['provenance']['parent_ref_sha256']==policy['original_ref_value_sha256']
    assert new_meta['provenance']['filtered_ref_sha256']==old_meta['provenance']['filtered_ref_sha256']==policy['filtered_ref_value_sha256']
    assert file_hash(old/'artifacts/filtered_reference.json')==policy['old_filtered_metadata_sha256']
    report={'experiment':'B-015','status':'PASS','changed_count':4,'unchanged_count':12,'comparison':'bit-exact controls; all four driving leaves must differ',
       'policy_sha256':file_hash(root/'configs/pair_baseline.json'),'STILL_cache_sha256':still_meta['file_sha256'],
       'MOV_cache_sha256':mov_meta['file_sha256'],'new_filtered_metadata_sha256':file_hash(root/'artifacts/filtered_reference.json'),
       'new_filtered_file_sha256':file_hash(root/'artifacts/filtered_reference.safetensors'),'old_filtered_metadata_sha256':policy['old_filtered_metadata_sha256'],
       'filtered_values_exact':True,'original_reference_value_sha256':policy['original_ref_value_sha256'],
       'filtered_reference_value_sha256':policy['filtered_ref_value_sha256'],'rows':rows}
    atomic_json(root/'reports/PAIR_AUDIT.json',report)
    atomic_json(root/'configs/pair_audit.json',report)


if __name__=='__main__':main(Path(sys.argv[1]))
