"""One official CoTracker3 offline pass per fixed source, no generated-video input."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import sys
import time
import numpy as np
import torch
from PIL import Image, ImageDraw


@dataclass(frozen=True, slots=True)
class Config:
    data_root: str
    tracker_code: str
    checkpoint: str
    output: str
    clips: tuple[str,...]
    selection_seed: int = 20261030
    device: str = 'cuda'


def sha(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def select_points(mask: np.ndarray, seed: int) -> np.ndarray:
    yy,xx=np.mgrid[0:mask.shape[0]:4,0:mask.shape[1]:4]
    valid=mask[yy,xx]>0
    candidates=np.stack((xx[valid],yy[valid]),axis=1).astype(np.float32)
    if not len(candidates):
        y,x=np.nonzero(mask);candidates=np.stack((x,y),axis=1).astype(np.float32)
    assert len(candidates)>0
    rng=np.random.default_rng(seed); chosen=[int(rng.integers(len(candidates)))]
    distance=np.sum((candidates-candidates[chosen[0]])**2,axis=1)
    for _ in range(min(16,len(candidates))-1):
        index=int(np.argmax(distance));chosen.append(index)
        distance=np.minimum(distance,np.sum((candidates-candidates[index])**2,axis=1))
    return candidates[chosen]


def run(config: Config, cpu_only: bool) -> None:
    sys.path.insert(0,config.tracker_code)
    from cotracker.predictor import CoTrackerPredictor
    data=Path(config.data_root);checkpoint=Path(config.checkpoint);out=Path(config.output)
    assert all(Path(v).is_absolute() for v in (config.data_root,config.tracker_code,config.checkpoint,config.output))
    assert checkpoint.stat().st_size==101890938
    assert sha(checkpoint)=='2670d4562ed69326dda775a26e54883925cd11b6fc9b24cb7aa9f8078bce7834'
    for clip in config.clips:
        for t in range(33):
            with Image.open(data/clip/'source'/f'{t:03d}.png') as im:
                assert im.mode=='RGB' and im.size==(416,240)
        with Image.open(data/clip/'mask'/'000.png') as im:
            points=select_points(np.array(im),config.selection_seed)
        assert 1<=len(points)<=16
    if cpu_only:
        print(json.dumps({'status':'CPU_PASS','clips':len(config.clips),'cuda_initialized':torch.cuda.is_initialized()}));return
    out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic()
    predictor=CoTrackerPredictor(checkpoint=None,offline=True,v2=False,window_len=60)
    state=torch.load(checkpoint,map_location='cpu',weights_only=True)
    if 'model' in state:state=state['model']
    predictor.model.load_state_dict(state,strict=True)
    predictor.eval().requires_grad_(False).to(config.device)
    receipts=[]
    with torch.inference_mode():
        for clip in config.clips:
            tick=time.monotonic();root=out/clip;root.mkdir()
            manifest=json.loads((data/clip/'manifest.json').read_text())
            images=[]
            for t in range(33):
                with Image.open(data/clip/'source'/f'{t:03d}.png') as im:images.append(np.array(im))
            with Image.open(data/clip/'mask'/'000.png') as im:first=np.array(im)
            points=select_points(first,config.selection_seed)
            queries=np.column_stack((np.zeros(len(points),np.float32),points))
            video=torch.from_numpy(np.stack(images)).permute(0,3,1,2).unsqueeze(0).float().to(config.device)
            tracks,visible=predictor(video,queries=torch.from_numpy(queries).unsqueeze(0).to(config.device),backward_tracking=False)
            q=tracks[0].cpu().numpy();v=visible[0].cpu().numpy()
            assert q.shape==(33,len(points),2) and v.dtype==np.bool_
            valid=np.isfinite(q).all(axis=-1)&(q[...,0]>=0)&(q[...,0]<=415)&(q[...,1]>=0)&(q[...,1]<=239)
            anchor_valid=np.stack((valid[0]&v[0],valid[32]&v[32]))
            boxes=np.array([r['bbox_xyxy'] if r['bbox_xyxy'] is not None else [0,0,0,0] for r in manifest['records']],np.float32)
            ids=np.array([r['source_frame_id'] for r in manifest['records']],np.int64)
            path=root/'tracks.npz'
            np.savez_compressed(path,tracks=q,visible=v,valid=valid,anchor_valid=anchor_valid,bbox=boxes,source_frame_ids=ids,queries=queries)
            with np.load(path,allow_pickle=False) as saved:assert np.array_equal(saved['tracks'],q,equal_nan=True)
            for t in (0,4,8,12,16,20,24,28,32):
                image=Image.fromarray(images[t]);draw=ImageDraw.Draw(image)
                for k,(x,y) in enumerate(q[t]):
                    if valid[t,k]:
                        color='lime' if v[t,k] else 'orange';draw.ellipse((x-2,y-2,x+2,y+2),fill=color);draw.text((x+3,y),str(k),fill=color)
                image.save(root/f'overlay-{t:03d}.jpg',quality=92)
            receipt={'clip':clip,'status':'COMPLETE','passes':1,'seconds':time.monotonic()-tick,'points':len(points),
                     'source_manifest_sha256':sha(data/clip/'manifest.json'),'tracks_sha256':sha(path),
                     'visible_count':int(v.sum()),'valid_count':int(valid.sum()),'total_samples':int(v.size),
                     'invalid_reason':'nonfinite or outside image pixel-center bounds; no mask-outside rejection',
                     'anchor_valid':anchor_valid.tolist(),'confidence':None,'confidence_reason':'public predictor API returns bool visibility, not calibrated confidence',
                     'query_seed':config.selection_seed,'track_id_meaning':'same surface point within this clip; not anatomical/shared across clips',
                     'coordinates':'integer xy pixel centers; normalized (x+0.5)/416,(y+0.5)/240',
                     'source_frame_ids':ids.tolist()}
            (root/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');receipts.append(receipt)
            print(json.dumps({'clip':clip,'status':'COMPLETE','seconds':receipt['seconds']}),flush=True)
    report={'status':'COMPLETE','seconds':time.monotonic()-started,'clips':receipts,'passes':len(receipts),
            'strict_load':True,'weights_only':True,'checkpoint_sha256':sha(checkpoint),'offline':True,'window_len':60,'v2':False,
            'code_revision':'82e02e8029753ad4ef13cf06be7f4fc5facdda4d','weight_revision':'bf55ea50d4390e1820a267f131cd6587240fb2c5'}
    (out/'tracker-receipt.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    config=Config(**json.loads(Path(sys.argv[1]).read_text()))
    run(config,'--cpu-only' in sys.argv)
