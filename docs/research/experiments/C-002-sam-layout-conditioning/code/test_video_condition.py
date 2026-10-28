# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run: existing research Python test_video_condition.py /absolute/frameref.py
"""Bounded CPU contracts; plain assertions avoid installing a test dependency."""
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import sys
import numpy as np
from PIL import Image
import torch
import video_generate as video


def test_conditions(root: Path, helper: Path) -> None:
    # Given distinct anchors and 33 binary RGB layout images.
    layout=root/'layout';layout.mkdir()
    for i in range(33):
        array=np.full((480,832,3),255,dtype=np.uint8)
        array[100:110,i:i+3]=0
        Image.fromarray(array).save(layout/f'{i:03d}.png')
    for name,color in [('start',(20,40,60)),('end',(60,40,20))]:
        Image.new('RGB',(832,480),color).save(root/f'{name}.png')
    base=dict(upstream=root,weights=root,tokenizer=root,helper=helper,
        helper_sha256=hashlib.sha256(helper.read_bytes()).hexdigest(),
        start_anchor=root/'start.png',end_anchor=root/'end.png',output=root/'output',prompt='fixed')
    # When all three modes construct their actual inputs.
    outputs={mode:video.condition(video.Config(**base,condition_mode=mode,
        layout_dir=None if mode=='endpoint' else layout)) for mode in ('endpoint','layout_mov','layout_still')}
    # Then only the expected middle RGB changes; G and anchors remain identical.
    for mode,(frames,masks,receipt) in outputs.items():
        assert frames[0].tobytes()==Image.open(root/'start.png').tobytes()
        assert frames[32].tobytes()==Image.open(root/'end.png').tobytes()
        assert receipt['mask_pixel_sha256']==outputs['endpoint'][2]['mask_pixel_sha256']
        for i in range(1,32):
            if mode=='endpoint':assert frames[i].getextrema()==((127,127),)*3
            else:assert frames[i].tobytes()==Image.open(layout/f'{i if mode=="layout_mov" else 0:03d}.png').tobytes()
    assert len(set(outputs['layout_mov'][2]['rgb_pixel_sha256'][1:32]))==31
    assert len(set(outputs['layout_still'][2]['rgb_pixel_sha256'][1:32]))==1
    # Given invalid layout channel/range; When consumed; Then reject before weights.
    Image.new('RGB',(832,480),(127,127,127)).save(layout/'001.png')
    try:video.condition(video.Config(**base,condition_mode='layout_mov',layout_dir=layout))
    except AssertionError:pass
    else:raise AssertionError('Non-binary layout accepted')


def test_tensor_observation() -> None:
    # Given real noncontiguous BF16 values and a fixed RNG state.
    tensor=torch.arange(24,dtype=torch.bfloat16).reshape(2,3,4).transpose(0,1)
    before=tensor.clone();rng=torch.get_rng_state().clone()
    # When collecting the byte-level observation.
    result=video.tensor_summary(tensor)
    # Then source bytes and RNG are preserved, with exact BF16 hash.
    assert result['sha256']==hashlib.sha256(tensor.contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()
    assert result['shape']==[3,2,4] and result['dtype']=='torch.bfloat16' and result['finite']
    assert torch.equal(before,tensor) and torch.equal(rng,torch.get_rng_state())


if __name__=='__main__':
    with TemporaryDirectory() as folder:test_conditions(Path(folder),Path(sys.argv[1]))
    test_tensor_observation()
    print('PASS: endpoint/MOV/STILL, unchanged G/anchors, invalid layout, BF16 byte hash and RNG preservation')
