"""Fresh B034 producer contract shared unchanged by BASE and STEP."""
from dataclasses import dataclass
from pathlib import Path
import hashlib,json

@dataclass(frozen=True,slots=True)
class CaseContract:
    name:str='public'
    height:int=512
    width:int=896
    fps:int=24
    @property
    def latent_shape(self):return [16,5,64,112]
    @property
    def decoded_shape(self):return [3,17,512,896]

def active_contract(root:Path)->CaseContract:
    assert json.loads((root/'configs/active_case.json').read_text())['name']=='public'
    return CaseContract()

def verify_cache_receipt(root:Path)->dict:
    receipt=json.loads((root/'artifacts/conditions_receipt.json').read_text())
    assert receipt['experiment']=='B-034' and receipt['reference_id']=='R1'
    for name,digest in receipt['hashes'].items():assert hashlib.sha256((root/'artifacts'/name).read_bytes()).hexdigest()==digest,name
    meta=json.loads((root/'artifacts/conditions.json').read_text())
    assert meta['provenance']['config']==json.loads((root/'configs/public.json').read_text())
    assert len(meta['tensors'])==16
    import torch
    noise=torch.load(root/'artifacts/initial_noise.pt',map_location='cpu',weights_only=True)
    assert hashlib.sha256(noise.contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()==meta['tensors']['t0']['sha256']==meta['provenance']['initial_noise_sha256']
    producer=json.loads(((root/'experiment').resolve()/'ENC_FREEZE.json').read_text())
    assert receipt['code_sha256']==producer['receipt_sha256']
    return receipt
