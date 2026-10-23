"""Create one new semantic reference mask; exact BLACK to WHITE, RED untouched."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image


def prepare(source: Path, target: Path, report: Path) -> None:
    assert not target.exists()
    before=np.asarray(Image.open(source).convert('RGB'))
    red=np.all(before==[255,0,0],axis=-1);black=np.all(before==0,axis=-1)
    assert before.shape==(896,512,3) and int(red.sum())==113928 and int(black.sum())==344824
    assert np.all(red|black)
    after=before.copy();after[black]=255
    assert np.array_equal(after[red],before[red]) and np.array_equal(np.all(after==[255,0,0],axis=-1),red)
    Image.fromarray(after).save(target)
    assert np.array_equal(np.asarray(Image.open(target)),after)
    report.write_text(json.dumps({'status':'PASS','red_pixels':int(red.sum()),'black_to_white_pixels':int(black.sum()),'other_pixels':0,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'target_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'red_exact':True,'RGB_reference_modified':False},indent=2)+'\n')

if __name__=='__main__':prepare(*map(Path,sys.argv[1:]))
