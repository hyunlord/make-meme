"""Two explicit case contracts; no shape, FPS, device or integrity gate removed."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
from typing import Literal

@dataclass(frozen=True, slots=True)
class CaseContract:
    name: Literal['official', 'lab', 'self', 'real']
    height: int
    width: int
    fps: int
    color: Literal['BLUE', 'RED']

    @property
    def latent_shape(self) -> list[int]:
        return [16, 5, self.height // 8, self.width // 8]

    @property
    def decoded_shape(self) -> list[int]:
        return [3, 17, self.height, self.width]


def case_contract(name: str) -> CaseContract:
    match name:
        case 'real':
            return CaseContract('real',512,896,30,'RED')
        case 'official':
            return CaseContract('official', 512, 896, 16, 'BLUE')
        case 'lab':
            return CaseContract('lab', 896, 512, 24, 'RED')
        case 'self':
            return CaseContract('self', 896, 512, 24, 'RED')
        case _:
            raise AssertionError('Only preregistered official/lab cases are supported')


def active_contract(root: Path) -> CaseContract:
    return case_contract(json.loads((root/'configs/active_case.json').read_text())['name'])


def verify_parent_receipt(root: Path) -> dict:
    producer=root/'producer'
    receipt=json.loads((producer/'artifacts/conditions_receipt.json').read_text())
    assert receipt['experiment']=='B-024' and receipt['case']=='real'
    for filename,digest in receipt['hashes'].items():
        assert hashlib.sha256((producer/'artifacts'/filename).read_bytes()).hexdigest()==digest,filename
    return receipt


def verify_cache_receipt(root: Path) -> dict:
    parent=verify_parent_receipt(root)
    receipt=json.loads((root/'artifacts/conditions_receipt.json').read_text())
    execution=json.loads((root/'configs/execution.json').read_text())
    assert receipt['experiment']=='B-025' and receipt['reference_id']==execution['reference_id']
    assert set(receipt['hashes'])=={'conditions.safetensors','conditions.json','initial_noise.pt'}
    for filename,digest in receipt['hashes'].items():
        assert hashlib.sha256((root/'artifacts'/filename).read_bytes()).hexdigest()==digest,filename
    assert receipt['code_sha256']==hashlib.sha256((root/'PREREGISTERED_CODE.json').read_bytes()).hexdigest()
    metadata=json.loads((root/'artifacts/conditions.json').read_text())
    assert metadata['provenance']['parent_cache_sha256']==parent['hashes']['conditions.safetensors']
    assert metadata['provenance']['builder_sha256']==hashlib.sha256((root/'code/phase_encode.py').read_bytes()).hexdigest()
    original=json.loads((root/'producer/artifacts/conditions.json').read_text())
    assert original['structure']==metadata['structure']
    assert receipt['hashes']['initial_noise.pt']==parent['hashes']['initial_noise.pt']
    experiment=(root/'experiment').resolve()
    pair=json.loads((experiment/'reports/pair-conditions.json').read_text());assert pair['status']=='PASS'
    from pair_contract import pair_changes
    lab=json.loads((experiment/'cases/LAB/artifacts/conditions.json').read_text())
    ig=json.loads((experiment/'cases/IG/artifacts/conditions.json').read_text())
    assert pair_changes(lab['tensors'],ig['tensors'])==set(pair['changed_pair_leaves'])
    assert pair['case_hashes'][execution['reference_id']]==metadata['file_sha256']
    return receipt
