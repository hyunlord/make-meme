# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run using the existing pinned SCAIL environment; do not install dependencies.
"""Fixed public-data contract and strict receipt verification for each task pair."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json

@dataclass(frozen=True, slots=True)
class CaseContract:
    name: str
    height: int
    width: int
    fps: int
    color: str

    @property
    def latent_shape(self) -> list[int]:
        return [16, 5, self.height // 8, self.width // 8]

    @property
    def decoded_shape(self) -> list[int]:
        return [3, 17, self.height, self.width]


def case_contract(name: str) -> CaseContract:
    assert name == 'public'
    return CaseContract('public', 512, 896, 24, 'RED')


def active_contract(root: Path) -> CaseContract:
    return case_contract(json.loads((root/'configs/active_case.json').read_text())['name'])


def verify_producer_cache_receipt(root: Path) -> dict:
    receipt=json.loads((root/'artifacts/conditions_receipt.json').read_text())
    execution=json.loads((root/'configs/execution.json').read_text())
    assert receipt['experiment']=='B-027' and receipt['reference_id']==execution['reference_id']
    assert set(receipt['hashes'])=={'conditions.safetensors','conditions.json','initial_noise.pt'}
    for filename,digest in receipt['hashes'].items():
        assert hashlib.sha256((root/'artifacts'/filename).read_bytes()).hexdigest()==digest,filename
    assert receipt['code_sha256']==hashlib.sha256((root/'PREREGISTERED_CODE.json').read_bytes()).hexdigest()
    metadata=json.loads((root/'artifacts/conditions.json').read_text())
    import torch
    noise=torch.load(root/'artifacts/initial_noise.pt',map_location='cpu',weights_only=True)
    digest=hashlib.sha256(noise.contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()
    assert digest==metadata['tensors']['t0']['sha256']==metadata['provenance']['initial_noise_sha256']
    assert metadata['provenance']['config']==json.loads((root/'configs/public.json').read_text())
    assert metadata['provenance']['reference_id']==execution['reference_id']
    experiment=(root/'experiment').resolve()
    pair=json.loads((experiment/'reports/pair-conditions.json').read_text());assert pair['status']=='PASS'
    from pair_contract import pair_changes
    first=json.loads((experiment/'cases/R1/artifacts/conditions.json').read_text())
    second=json.loads((experiment/'cases/R2/artifacts/conditions.json').read_text())
    assert first['structure']==second['structure']
    assert pair_changes(first['tensors'],second['tensors'])==set(pair['changed_pair_leaves'])
    assert pair['case_hashes'][execution['reference_id']]==metadata['file_sha256']
    assert (experiment/'cases/R1/artifacts/initial_noise.pt').read_bytes()==(experiment/'cases/R2/artifacts/initial_noise.pt').read_bytes()
    return receipt


def verify_cache_receipt(root: Path) -> dict:
    """Validate both B027 parents and exact two-leaf consumer derivation."""
    from crossover import CLIP_KEYS, sha
    binding=json.loads((root/'configs/cache_binding.json').read_text())
    row=Path(binding['row_worker']);donor=Path(binding['clip_worker'])
    for parent in (row,donor):verify_producer_cache_receipt(parent)
    receipt=json.loads((root/'artifacts/conditions_receipt.json').read_text())
    assert receipt['experiment']=='B-030' and set(receipt['expected_changed'])==CLIP_KEYS
    for path,digest in receipt['parents'].items():assert sha(Path(path))==digest
    for name,digest in receipt['hashes'].items():assert sha(root/'artifacts'/name)==digest
    a=json.loads((row/'artifacts/conditions.json').read_text())
    b=json.loads((donor/'artifacts/conditions.json').read_text())
    c=json.loads((root/'artifacts/conditions.json').read_text())
    assert c['structure']==a['structure']==b['structure']
    assert set(c['tensors'])==set(a['tensors'])=={f't{i}' for i in range(16)}
    changed={key for key in c['tensors'] if c['tensors'][key]!=a['tensors'][key]}
    assert changed==CLIP_KEYS
    for key in c['tensors']:
        expected=b if key in CLIP_KEYS else a
        assert c['tensors'][key]==expected['tensors'][key]
    assert (root/'artifacts/initial_noise.pt').read_bytes()==(row/'artifacts/initial_noise.pt').read_bytes()==(donor/'artifacts/initial_noise.pt').read_bytes()
    assert json.loads((root/'configs/public.json').read_text())==json.loads((row/'configs/public.json').read_text())
    provenance=dict(c['provenance']);cross=provenance.pop('crossover')
    assert provenance==a['provenance']
    assert cross['row_sha256']==a['file_sha256'] and cross['clip_donor_sha256']==b['file_sha256']
    return receipt
