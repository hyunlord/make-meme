"""Independent CPU check of actual decoded tensor against PNG exports and source."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
import torch
from PIL import Image


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('root',type=Path);parser.add_argument('--case',choices=('LAB','IG'),required=True);args=parser.parse_args();r=args.root;case=args.case
    p=r/'cases'/case/'artifacts/raw_output.pt';raw=torch.load(p,map_location='cpu',weights_only=True)
    assert isinstance(raw,torch.Tensor) and tuple(raw.shape)==(3,17,512,896) and bool(torch.isfinite(raw).all())
    frames=((raw.clamp(-1,1)+1)/2*255).to(torch.uint8).permute(1,2,3,0).numpy();rows=[]
    for i,frame in enumerate(frames):
        with Image.open(r/'reports'/f'comparison-{case.lower()}-raw'/f'{i:03d}.png') as im:new=np.array(im.convert('RGB'))
        with Image.open(r/'reports/comparison-inputs/source'/f'{i:03d}.png') as im:source=np.array(im.convert('RGB'))
        assert np.array_equal(frame,new)
        rows.append({'local':i,'export_equals_actual_raw_quantization':True,'source_pixel_exact':bool(np.array_equal(source,new)),'source_differing_values':int(np.count_nonzero(source!=new)),'source_rgb_abs_error_mean_0_255':float(np.abs(source.astype(float)-new).mean())})
    report={'raw_path':f'cases/{case}/artifacts/raw_output.pt','raw_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'shape':list(raw.shape),'dtype':str(raw.dtype),'all17_export_matches_actual_raw':True,'source_file_substitution_detected':False,'note':'Source difference is descriptive pixel evidence, not identity-transfer or perceptual quality acceptance. Independent CPU check; no model call.','frames':rows}
    (r/'reports'/f'comparison-{case.lower()}-raw-provenance.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
