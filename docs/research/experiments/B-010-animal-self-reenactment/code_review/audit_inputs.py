"""CPU-only read-only audit and fixed-canvas Lab input sheet; no model imports."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import subprocess
from pathlib import Path
import numpy as np
import torch
import torchvision.transforms as TT
from torchvision.transforms.functional import resize
from torchvision.transforms import InterpolationMode
from PIL import Image, ImageDraw


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs',type=Path)
    parser.add_argument('helper',type=Path)
    parser.add_argument('out',type=Path)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    names=['reference.png','reference-mask.png','driver-24fps.mp4','mask-24fps.mp4']
    files={name:{'sha256':digest(args.inputs/name),'bytes':(args.inputs/name).stat().st_size} for name in names}
    namespace={'resize':resize,'InterpolationMode':InterpolationMode,'TT':TT,'np':np,'Image':Image}
    nodes=[n for n in ast.parse(args.helper.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in ('resize_for_rectangle_crop','load_image_to_tensor_chw_normalized')]
    assert len(nodes)==2
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(args.helper),'exec'),namespace)
    tensors={};decoded={};metadata={}
    for name,key in [('reference.png','img'),('reference-mask.png','ref_mask_img')]:
        with Image.open(args.inputs/name) as im:
            assert im.size==(512,896)
            rgb=im.convert('RGB')
            value=namespace['load_image_to_tensor_chw_normalized'](rgb)
            tensors[key]=namespace['resize_for_rectangle_crop'](value,(896,512),reshape_mode='center').squeeze(0)
    for name,key in [('driver-24fps.mp4','pose_video'),('mask-24fps.mp4','driving_mask_video')]:
        path=args.inputs/name
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=width,height,avg_frame_rate,nb_read_frames,duration','-of','json',str(path)]))['streams'][0]
        assert (probe['width'],probe['height'],probe['avg_frame_rate'],probe['nb_read_frames'])==(512,896,'24/1','17')
        raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-f','rawvideo','-pix_fmt','rgb24','-'])
        array=np.frombuffer(raw,dtype=np.uint8).copy().reshape(17,896,512,3)
        decoded[key]=array;metadata[name]=probe
        value=(namespace['resize_for_rectangle_crop'](torch.from_numpy(array).permute(0,3,1,2),(896,512),reshape_mode='center')-127.5)/127.5
        tensors[key]=value.permute(1,0,2,3) if key=='driving_mask_video' else value
    source_hashes=[]
    for folder in ('driver','mask'):
        paths=sorted((args.inputs/folder).glob('*.png'))
        assert [p.name for p in paths]==[f'{i:03d}.png' for i in range(17)]
        for path in paths:
            with Image.open(path) as im:assert im.size==(512,896)
            source_hashes.append({'name':f'{folder}/{path.name}','sha256':digest(path)})
    sheet=Image.new('RGB',(6*256,3*480),'#222222')
    reference=Image.new('RGB',(512,480),'#222222')
    for i,name in enumerate(('reference.png','reference-mask.png')):
        with Image.open(args.inputs/name) as im:reference.paste(im.resize((256,448)),(i*256,24))
        ImageDraw.Draw(reference).text((i*256+4,4),name,fill='white')
    reference.save(args.out/'reference.png')
    for index in range(17):
        tile=Image.new('RGB',(256,480),'#222222')
        tile.paste(Image.fromarray(decoded['pose_video'][index]).resize((128,224)),(0,24))
        tile.paste(Image.fromarray(decoded['driving_mask_video'][index]).resize((128,224)),(128,24))
        with Image.open(args.inputs/f'driver/{index:03d}.png') as im:tile.paste(im.resize((128,224)),(0,252))
        with Image.open(args.inputs/f'mask/{index:03d}.png') as im:tile.paste(im.resize((128,224)),(128,252))
        ImageDraw.Draw(tile).text((4,4),f'f{index}: decoded / PNG below',fill='white')
        sheet.paste(tile,((index%6)*256,(index//6)*480))
    sheet.save(args.out/'all17-source-mask.png')
    report={'files':files,'source_frame_hashes':source_hashes,'video_metadata':metadata,'helper_sha256':digest(args.helper),'mask_quality':'PARTIAL_UNRESOLVED: thin paws/tail/floor reflection boundaries retained, no mask modification','geometry':'All inputs512x896; exact upstream center resize/crop remains same output geometry; RGB and masks identical transform; order0..16','source_samples_seconds':[i/24 for i in range(17)],'tensor_hashes':{k:{'shape':list(v.shape),'dtype':str(v.dtype),'sha256':hashlib.sha256(v.contiguous().numpy().tobytes()).hexdigest()} for k,v in tensors.items()},'model_execution':'NOT_RUN; CPU input operations only'}
    (args.out/'audit.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
