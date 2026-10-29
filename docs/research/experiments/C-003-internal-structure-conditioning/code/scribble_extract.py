"""One full-frame official FP32 scribble pass; existing guarded Python environment."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import sys
import time
import numpy as np
import torch
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))


@dataclass(frozen=True, slots=True)
class Config:
    source_dir: str
    weights: str
    output: str
    device: str = 'cuda'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(config: Config, cpu_only: bool) -> None:
    paths = [Path(config.source_dir)/f'{i:03d}.png' for i in range(33)]
    for path in paths:
        assert path.is_absolute() and path.is_file()
        with Image.open(path) as im:
            assert im.mode == 'RGB' and im.size == (832,480)
    weight = Path(config.weights)
    assert weight.is_absolute() and weight.stat().st_size == 17173511
    assert sha(weight) == 'c686ced2a666b4850b4bb6ccf0748031c3eda9f822de73a34b8979970d90f0c6'
    if cpu_only:
        print(json.dumps({'status':'CPU_PASS','source_count':33,'cuda_initialized':torch.cuda.is_initialized(),'model_imported':'scribble_model' in sys.modules}))
        return
    from scribble_model import ContourInference
    output = Path(config.output)
    assert output.is_absolute()
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    model = ContourInference(3, 1, n_residual_blocks=3, sigmoid=True)
    weights = torch.load(weight, map_location='cpu', weights_only=True)
    model.load_state_dict(weights, strict=True)
    model.eval().requires_grad_(False).to(device=config.device, dtype=torch.float32)
    records = []
    with torch.inference_mode(), torch.autocast(device_type='cuda', enabled=False):
        for i, path in enumerate(paths):
            tick = time.monotonic()
            with Image.open(path) as im:
                rgb = np.array(im)
            tensor = torch.from_numpy(rgb).permute(2,0,1).unsqueeze(0).float().div(255).to(config.device)
            raw = model(tensor)
            assert raw.dtype == torch.float32 and torch.isfinite(raw).all()
            gray = (raw.squeeze(1)*255).clip(0,255).cpu().numpy().astype(np.uint8)[0]
            assert gray.shape == (480,832)
            target = output/f'{i:03d}.png'
            Image.fromarray(gray).save(target)
            records.append({'index':i,'source_sha256':sha(path),'raw_sha256':sha(target),
                            'minimum':int(gray.min()),'maximum':int(gray.max()),
                            'mean':float(gray.mean()),'seconds':time.monotonic()-tick})
            print(json.dumps({'frame_complete':i,'seconds':records[-1]['seconds']}), flush=True)
    receipt = {'status':'COMPLETE','frames':33,'completed_extraction_passes':1,
               'elapsed_seconds':time.monotonic()-started,'device':config.device,'dtype':'float32',
               'strict_load':True,'weights_only':True,'residual_blocks':3,'input':'full-frame RGB / 255',
               'output':'official sigmoid * 255 clip uint8; no inversion or threshold',
               'weights_sha256':sha(weight),'weights_bytes':weight.stat().st_size,
               'repository_revision':'63512cbbe4e3a98e1636356ef2230da84649f617',
               'source_revision':'48eb44f1c4be87cc65a98bff985a26976841e9f3',
               'state_dict_keys':{k:list(v.shape) for k,v in weights.items()},'records':records}
    (output/'extraction.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'status':'COMPLETE','elapsed_seconds':receipt['elapsed_seconds']}))


if __name__ == '__main__':
    run(Config(**json.loads(Path(sys.argv[1]).read_text())), '--cpu-only' in sys.argv)
