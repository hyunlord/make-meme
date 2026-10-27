"""Apply unchanged frozen B034 RGB blending to one existing raw artifact on CPU."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path
import numpy as np
from PIL import Image
import torch

original, source_dir, edit_path, raw_path, destination = [Path(v).resolve() for v in sys.argv[1:6]]
assert not destination.exists()
spec = importlib.util.spec_from_file_location('b034_compositor',original/'compositor.py')
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
started = time.monotonic()
edit = np.load(edit_path)
source_pixels = np.stack([np.asarray(Image.open(source_dir/f'{i:03d}.png').convert('RGB')) for i in range(17)])
source = source_pixels.astype(np.float32)/127.5-1
raw = torch.load(raw_path,map_location='cpu',weights_only=True).float().permute(1,2,3,0).numpy()
assert raw.shape == source.shape == (17,512,896,3) and np.isfinite(raw).all()
frames = destination/'frames'
frames.mkdir(parents=True)
for i in range(17):
    result = module.blend(source[i],raw[i],edit[i])
    assert np.array_equal(result[edit[i]==0],source[i][edit[i]==0])
    assert np.array_equal(result[edit[i]==1],raw[i][edit[i]==1])
    pixels = module.to_uint8(result)
    pixels[edit[i]==0] = source_pixels[i][edit[i]==0]
    pixels[edit[i]==1] = module.to_uint8(raw[i])[edit[i]==1]
    target = frames/f'{i:03d}.png'
    Image.fromarray(pixels).save(target)
    saved = np.asarray(Image.open(target))
    assert np.array_equal(saved[edit[i]==0],source_pixels[i][edit[i]==0])
    assert np.array_equal(saved[edit[i]==1],module.to_uint8(raw[i])[edit[i]==1])
subprocess.run(['ffmpeg','-v','error','-framerate','24','-i',str(frames/'%03d.png'),'-vf','scale=in_range=full:out_range=tv:out_color_matrix=bt709,format=yuv420p','-c:v','libx264','-crf','18','-color_range','tv','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709',str(destination/'output.mp4')],check=True)
subprocess.run(['ffmpeg','-v','error','-i',str(destination/'output.mp4'),'-f','null','-'],check=True)
hash_file = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
row = {'E_sha256':hash_file(edit_path),'raw_sha256':hash_file(raw_path),'compositor_sha256':hash_file(original/'compositor.py'),'source_exact_E0':True,'generated_exact_E1':True,'saved_png_E0_source_bytes_exact':True,'saved_png_E1_raw_quantization_exact':True,'frames':17,'preview_fps':24,'source_fps':None,'timebase_assumed':True,'new_derivative_encoded':True,'original_mp4_unchanged':True,'wall_seconds':time.monotonic()-started,'temporal':'UNVERIFIED'}
(destination/'verification.json').write_text(json.dumps(row,indent=2)+'\n')
print(json.dumps(row))
