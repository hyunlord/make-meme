"""Same E/F RGB24 decoding and official center crop; no temporal resampling."""
import hashlib
import json
import subprocess
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from contracts import active_contract


def inputs(root:Path,cfg:dict) -> dict:
    from wan.utils.scail_utils import load_image_to_tensor_chw_normalized,resize_for_rectangle_crop
    def image(name):
        value=load_image_to_tensor_chw_normalized(Image.open(root/cfg[name]).convert('RGB'))
        return resize_for_rectangle_crop(value,(cfg['height'],cfg['width']),reshape_mode='center').squeeze(0)
    def video(name):
        path=root/cfg[name]
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height,avg_frame_rate,nb_frames','-of','json',str(path)]))['streams'][0]
        assert int(probe['nb_frames'])==17 and probe['avg_frame_rate']==str(cfg['fps'])+'/1'
        raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-f','rawvideo','-pix_fmt','rgb24','-'])
        array=np.frombuffer(raw,dtype=np.uint8).copy().reshape(17,probe['height'],probe['width'],3)
        value=torch.from_numpy(array).permute(0,3,1,2)
        return (resize_for_rectangle_crop(value,(cfg['height'],cfg['width']),reshape_mode='center')-127.5)/127.5
    return {'img':image('reference'),'ref_mask_img':image('reference_mask'),'pose_video':video('driver'),'driving_mask_video':video('driver_mask').permute(1,0,2,3)}


def verify_inputs(root:Path) -> dict:
    contract=active_contract(root)
    cfg=json.loads((root/'configs'/f'{contract.name}.json').read_text())
    manifest=json.loads((root/'configs/input_config_hashes.json').read_text())
    for name,digest in manifest.items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
    assert (cfg['frames'],cfg['fps'],cfg['steps'],cfg['seed'],cfg['height'],cfg['width'])==(17,contract.fps,40,20261022,contract.height,contract.width)
    assert cfg['adapter'] is None
    assert (cfg['solver'],cfg['shift'],cfg['guide_scale'],cfg['segment_overlap'])==('unipc',3.0,5.0,5)
    return cfg
