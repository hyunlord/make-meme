"""Two explicit case contracts; no shape, FPS, device or integrity gate removed."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
from typing import Literal

@dataclass(frozen=True, slots=True)
class CaseContract:
    name: Literal['official', 'lab', 'self']
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


def expected_calls(root: Path) -> int:
    settings=json.loads((root/'configs/rope_h.json').read_text())
    assert settings['ALG'] is False and settings['reference_h_override']==120
    assert settings['steps']==40 and settings['expected_calls']==80
    return settings['expected_calls']


def verify_cache_receipt(root: Path) -> dict:
    """Bind original B013 P to its own immutable code/input/exit receipts."""
    binding=json.loads((root/'configs/parent_binding.json').read_text())
    assert binding['experiment']=='B-013' and binding['case']=='LAB_MOV'
    digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest(root/'configs/parent_code.json')==binding['parent_code_sha256']
    assert digest(root/'configs/parent_inputs.json')==binding['parent_inputs_sha256']
    assert digest(root/'artifacts/conditions_receipt.json')==binding['cache_receipt_sha256']
    assert set(binding['records'])=={'p_result.json','p_process.json','pair.json','lineage.json'}
    for name,sha in binding['records'].items():assert digest(root/'parent_records'/name)==sha
    parent_code=json.loads((root/'configs/parent_code.json').read_text())
    parent_inputs=json.loads((root/'configs/parent_inputs.json').read_text())
    assert parent_code['experiment']=='B-013'
    assert parent_inputs==json.loads((root/'configs/input_config_hashes.json').read_text())
    result=json.loads((root/'parent_records/p_result.json').read_text())
    process=json.loads((root/'parent_records/p_process.json').read_text())
    assert result['status']=='COMPLETED' and result['stage']=='P'
    assert result['condition_receipt_sha256']==binding['cache_receipt_sha256']
    assert process['reason']=='service_exit' and process['returncode']==0 and 'MainPID=0' in process['final_service']
    receipt=json.loads((root/'artifacts/conditions_receipt.json').read_text())
    assert receipt['experiment']=='B-013' and receipt['case']==active_contract(root).name
    assert set(receipt['hashes'])=={'conditions.safetensors','conditions.json','initial_noise.pt'}
    for filename,sha in receipt['hashes'].items():assert digest(root/'artifacts'/filename)==sha,filename
    assert receipt['code_sha256']==binding['parent_code_sha256']
    metadata=json.loads((root/'artifacts/conditions.json').read_text())
    assert metadata['provenance']['code']==parent_code
    assert metadata['provenance']['input_hashes']==parent_inputs
    pair=json.loads((root/'parent_records/pair.json').read_text())
    lineage=json.loads((root/'parent_records/lineage.json').read_text())
    assert pair['status']==lineage['status']=='PASS'
    assert pair['code_manifest_sha256']==lineage['code_manifest_sha256']==binding['parent_code_sha256']
    assert pair['case_cache_sha256']['LAB_MOV']==lineage['cases']['LAB_MOV']['cache_sha256']==receipt['hashes']['conditions.safetensors']
    return receipt
