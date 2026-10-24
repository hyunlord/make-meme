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


def verify_cache_receipt(root: Path) -> dict:
    """Bind immutable new P payload AND device/provenance sidecar before reuse."""
    producer=(root/'producer').resolve()
    receipt=json.loads((root/'artifacts/conditions_receipt.json').read_text())
    assert receipt['experiment']=='B-020' and receipt['case']==active_contract(root).name
    assert set(receipt['hashes'])=={'conditions.safetensors','conditions.json','initial_noise.pt','target.safetensors','target.json'}
    for filename,digest in receipt['hashes'].items():
        assert hashlib.sha256((root/'artifacts'/filename).read_bytes()).hexdigest()==digest,filename
    assert receipt['code_sha256']==hashlib.sha256((producer/'PREREGISTERED_CODE.json').read_bytes()).hexdigest()
    metadata=json.loads((root/'artifacts/conditions.json').read_text())
    assert metadata['provenance']['code']==json.loads((producer/'PREREGISTERED_CODE.json').read_text())
    assert metadata['provenance']['input_hashes']==json.loads((root/'configs/input_config_hashes.json').read_text())
    return receipt
