"""Private CPU paired driving review: raw RGB PNGs, exact input canvases, native24fps comparison."""
from __future__ import annotations
import argparse
import hashlib
import json
import secrets
import shutil
import subprocess
from pathlib import Path
import numpy as np
import torch
from torchvision.utils import make_grid
from PIL import Image, ImageDraw, ImageOps


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decode(path: Path) -> np.ndarray:
    data=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=width,height,avg_frame_rate,nb_read_frames','-of','json',str(path)]))['streams'][0]
    assert (data['width'],data['height'],data['avg_frame_rate'],data['nb_read_frames'])==(512,896,'24/1','17')
    raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-f','rawvideo','-pix_fmt','rgb24','-'])
    return np.frombuffer(raw,dtype=np.uint8).copy().reshape(17,896,512,3)


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs',type=Path,help='Unchanged B013 LAB_MOV inputs')
    parser.add_argument('old_mov',type=Path,help='B013 LAB_MOV artifacts')
    parser.add_argument('old_still',type=Path,help='B013 LAB_STILL artifacts')
    parser.add_argument('old_review',type=Path,help='Verified B013 raw-derived PNG directory')
    parser.add_argument('alg',type=Path,help='Completed B014 pilot artifacts')
    parser.add_argument('out',type=Path)
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    for folder in ['frames','blind-frames','baseline-mov-raw','baseline-still-raw','alg-raw']:
        (args.out/folder).mkdir()
    source=decode(args.inputs/'driver-24fps.mp4')
    with Image.open(args.inputs/'reference.png') as im:reference=im.convert('RGB')
    assert reference.size==(512,896)
    labels=('B013 LAB_MOV','B013 LAB_STILL','LAB_MOV_ALG')
    folders=('baseline-mov-raw','baseline-still-raw','alg-raw')
    roots=(args.old_mov,args.old_still,args.alg)
    raw_frames=[];encoded_frames=[];provenance=[]
    for case_index,(label,folder,root) in enumerate(zip(labels,folders,roots)):
        if case_index < 2:
            old_folder=args.old_review/('lab-mov-raw' if case_index==0 else 'lab-still-raw')
            loaded=[]
            for index in range(17):
                with Image.open(old_folder/f'{index:03d}.png') as im:
                    assert im.size==(512,896)
                    loaded.append(np.array(im.convert('RGB')))
                shutil.copyfile(old_folder/f'{index:03d}.png',args.out/folder/f'{index:03d}.png')
            pixels=np.stack(loaded)
        else:
            raw=torch.load(root/'raw_output.pt',map_location='cpu',weights_only=True)
            assert isinstance(raw,torch.Tensor) and list(raw.shape)==[3,17,896,512] and bool(torch.isfinite(raw).all())
            value=raw[None].clamp(-1,1)
            pixels=(torch.stack([make_grid(u,nrow=1,normalize=True,value_range=(-1,1)) for u in value.unbind(2)],dim=1).permute(1,2,3,0)*255).to(torch.uint8).numpy()
            for index in range(17):Image.fromarray(pixels[index]).save(args.out/folder/f'{index:03d}.png')
        raw_frames.append(pixels);encoded_frames.append(decode(root/'output.mp4'))
        provenance.append({'case':label,'raw_sha256':sha(root/'raw_output.pt'),'mp4_sha256':sha(root/'output.mp4')})
    blind_indices=[0,2]
    secrets.SystemRandom().shuffle(blind_indices)
    (args.out/'blind-mapping.json').write_text(json.dumps({'A':labels[blind_indices[0]],'B':labels[blind_indices[1]],'disclosure':'Keep private until both observations saved; not independent human blinding'},indent=2)+'\n')
    video_path=args.out/'source-reference-baseline-alg.mp4'
    command=['ffmpeg','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s','2560x928','-framerate','24','-i','pipe:0','-frames:v','17','-c:v','libx264','-pix_fmt','yuv420p',str(video_path)]
    with subprocess.Popen(command,stdin=subprocess.PIPE) as encoder:
        assert encoder.stdin is not None
        for index in range(17):
            images=[Image.fromarray(source[index]),reference,*[Image.fromarray(v[index]) for v in raw_frames]]
            panel=Image.new('RGB',(1280,480),'#222222');draw=ImageDraw.Draw(panel)
            for col,(im,label) in enumerate(zip(images,('SOURCE','ACTUAL LAB REF',*labels))):
                panel.paste(im.resize((256,448)),(col*256,24));draw.text((col*256+3,4),f'f{index} {label}',fill='white')
            panel.save(args.out/'frames'/f'{index:03d}.png')
            blind=Image.new('RGB',(1280,480),'#222222');draw=ImageDraw.Draw(blind)
            blind_images=[images[0],images[1],images[3],images[blind_indices[0]+2],images[blind_indices[1]+2]]
            for col,(im,label) in enumerate(zip(blind_images,('SOURCE','ACTUAL LAB REF','STILL CONTROL','A','B'))):
                blind.paste(im.resize((256,448)),(col*256,24));draw.text((col*256+3,4),f'f{index} {label}',fill='white')
            blind.save(args.out/'blind-frames'/f'{index:03d}.png')
            video=Image.new('RGB',(2560,928),'#222222');draw=ImageDraw.Draw(video)
            for col,(im,label) in enumerate(zip([images[0],reference,*[Image.fromarray(v[index]) for v in encoded_frames]],('SOURCE','ACTUAL LAB REF',*labels))):
                video.paste(im,(col*512,32));draw.text((col*512+4,5),label,fill='white')
            encoder.stdin.write(video.tobytes())
        encoder.stdin.close()
        assert encoder.wait()==0
    for folder,prefix in [('frames',''),('blind-frames','blind-')]:
        for name,indices in [('selected',(0,12,14,16)),('group-00-04',range(0,5)),('group-05-08',range(5,9)),('group-09-12',range(9,13)),('group-13-16',range(13,17))]:
            board=Image.new('RGB',(1280,len(indices)*480),'#222222')
            for row,index in enumerate(indices):
                with Image.open(args.out/folder/f'{index:03d}.png') as tile:board.paste(tile,(0,row*480))
            board.save(args.out/f'{prefix}{name}.png')
    sheet=Image.new('RGB',(1280,6*240),'#222222')
    for index in range(17):
        with Image.open(args.out/'frames'/f'{index:03d}.png') as tile:sheet.paste(tile.resize((426,160)),((index%3)*426,(index//3)*240))
    sheet.save(args.out/'all17.png')
    shutil.copyfile(Path(__file__).with_name('review-template.html'),args.out/'review.html')
    report={'frames':17,'fps':24,'duration_seconds':17/24,'sample_span_seconds':16/24,'source_indices':[7,23],'temporal_quality':'UNVERIFIED','cases':provenance,'source_sha256':sha(args.inputs/'driver-24fps.mp4'),'actual_reference_sha256':sha(args.inputs/'reference.png'),'raw_png_method':'B013 existing PNG files copied byte-for-byte; only new ALG tensor uses same upstream clamp/make_grid/mul255/uint8','video_method':'Existing MP4 decode then five-column encode, streaming temporary RGB; no retiming/warp/interpolation','archive_optimization':'No saved full-resolution video-collage PNGs or duplicate four-cell frames; primary full17 panels/rawPNGs/grouped sheets retained','ui_controls_qa':'NOT_RUN','tool_sha256':{name:sha(Path(__file__).with_name(name)) for name in ('output_review.py','review-template.html','check_review_ui.py')}}
    (args.out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
