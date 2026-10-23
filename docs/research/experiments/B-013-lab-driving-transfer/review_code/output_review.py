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
    parser.add_argument('inputs',type=Path,help='LAB_MOV inputs, read only')
    parser.add_argument('old_mov',type=Path,help='B012 MOV artifacts')
    parser.add_argument('old_still',type=Path,help='B012 STILL artifacts')
    parser.add_argument('old_review',type=Path,help='Existing B012 raw-derived PNG directory; read only')
    parser.add_argument('lab_mov',type=Path,help='B013 LAB_MOV artifacts')
    parser.add_argument('lab_still',type=Path,help='B013 LAB_STILL artifacts')
    parser.add_argument('out',type=Path)
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    for folder in ['frames','pairs','four-cells','blind-frames','lab-pair-frames']:(args.out/folder).mkdir()
    source=decode(args.inputs/'driver-24fps.mp4')
    with Image.open(args.inputs/'reference.png') as im:reference=im.convert('RGB')
    assert reference.size==(512,896)
    labels=('B012 MOV','B012 STILL','LAB_MOV','LAB_STILL')
    folders=('b012-mov-raw','b012-still-raw','lab-mov-raw','lab-still-raw')
    roots=(args.old_mov,args.old_still,args.lab_mov,args.lab_still)
    raw_frames=[];encoded_frames=[];provenance=[]
    for case_index,(label,folder,root) in enumerate(zip(labels,folders,roots)):
        (args.out/folder).mkdir()
        if case_index < 2:
            old_folder=args.old_review/('output-raw' if case_index==0 else 'still-raw')
            loaded=[]
            for index in range(17):
                with Image.open(old_folder/f'{index:03d}.png') as im:
                    assert im.size==(512,896)
                    loaded.append(np.array(im.convert('RGB')))
            pixels=np.stack(loaded)
        else:
            raw=torch.load(root/'raw_output.pt',map_location='cpu',weights_only=True)
            assert isinstance(raw,torch.Tensor) and list(raw.shape)==[3,17,896,512] and bool(torch.isfinite(raw).all())
            value=raw[None].clamp(-1,1)
            pixels=(torch.stack([make_grid(u,nrow=1,normalize=True,value_range=(-1,1)) for u in value.unbind(2)],dim=1).permute(1,2,3,0)*255).to(torch.uint8).numpy()
        raw_frames.append(pixels);encoded_frames.append(decode(root/'output.mp4'))
        provenance.append({'case':label,'raw_sha256':sha(root/'raw_output.pt'),'mp4_sha256':sha(root/'output.mp4')})
    blind_indices=[2,3]
    secrets.SystemRandom().shuffle(blind_indices)
    (args.out/'blind-mapping.json').write_text(json.dumps({'A':labels[blind_indices[0]],'B':labels[blind_indices[1]],'disclosure':'Keep separate until observations are recorded; not independent human blinding'},indent=2)+'\n')
    selected_indices=(0,12,14,16)
    selected=Image.new('RGB',(1536,len(selected_indices)*480),'#222222')
    sheet=Image.new('RGB',(1536,6*256),'#222222')
    for index in range(17):
        images=[Image.fromarray(source[index]),reference]
        for folder,pixels in zip(folders,raw_frames):
            image=Image.fromarray(pixels[index])
            if folder in folders[:2]:
                old_folder=args.old_review/('output-raw' if folder==folders[0] else 'still-raw')
                shutil.copyfile(old_folder/f'{index:03d}.png',args.out/folder/f'{index:03d}.png')
            else:image.save(args.out/folder/f'{index:03d}.png')
            images.append(image)
        six=Image.new('RGB',(1536,480),'#222222');draw=ImageDraw.Draw(six)
        for col,(image,label) in enumerate(zip(images,('SOURCE','ACTUAL LAB REF',*labels))):
            six.paste(image.resize((256,448)),(col*256,24));draw.text((col*256+3,4),f'f{index} {label}',fill='white')
        six.save(args.out/'frames'/f'{index:03d}.png')
        blind=Image.new('RGB',(1024,480),'#222222');blind_draw=ImageDraw.Draw(blind)
        blind_images=[images[0],images[1],images[blind_indices[0]+2],images[blind_indices[1]+2]]
        for col,(image,label) in enumerate(zip(blind_images,('SOURCE','ACTUAL LAB REF','A','B'))):
            blind.paste(image.resize((256,448)),(col*256,24));blind_draw.text((col*256+3,4),f'f{index} {label}',fill='white')
        blind.save(args.out/'blind-frames'/f'{index:03d}.png')
        main_pair=Image.new('RGB',(1024,480),'#222222');main_draw=ImageDraw.Draw(main_pair)
        for col,(image,label) in enumerate(zip([images[0],images[1],images[4],images[5]],('SOURCE','ACTUAL LAB REF','LAB_MOV','LAB_STILL'))):
            main_pair.paste(image.resize((256,448)),(col*256,24));main_draw.text((col*256+3,4),f'f{index} {label}',fill='white')
        main_pair.save(args.out/'lab-pair-frames'/f'{index:03d}.png')
        sheet.paste(six.resize((512,160)),((index%3)*512,(index//3)*256))
        four=Image.new('RGB',(1024,960),'#222222');draw=ImageDraw.Draw(four)
        for cell,(image,label) in enumerate(zip(images[2:],labels)):
            col,row=cell%2,cell//2
            four.paste(image.resize((256,448)),(col*512+128,row*480+24))
            draw.text((col*512+4,row*480+4),label,fill='white')
        four.save(args.out/'four-cells'/f'{index:03d}.png')
        pair=Image.new('RGB',(3072,928),'#222222');draw=ImageDraw.Draw(pair)
        video_images=[Image.fromarray(source[index]),reference,*[Image.fromarray(v[index]) for v in encoded_frames]]
        for col,(image,label) in enumerate(zip(video_images,('SOURCE','ACTUAL LAB REF',*labels))):
            pair.paste(image,(col*512,32));draw.text((col*512+4,5),label,fill='white')
        pair.save(args.out/'pairs'/f'{index:03d}.png')
    for row,index in enumerate(selected_indices):
        with Image.open(args.out/'frames'/f'{index:03d}.png') as tile:selected.paste(tile,(0,row*480))
    sheet.save(args.out/'all17.png');selected.save(args.out/'selected.png')
    blind_selected=Image.new('RGB',(1024,len(selected_indices)*480),'#222222')
    for row,index in enumerate(selected_indices):
        with Image.open(args.out/'blind-frames'/f'{index:03d}.png') as tile:blind_selected.paste(tile,(0,row*480))
    blind_selected.save(args.out/'blind-selected.png')
    for first,last in [(0,4),(5,8),(9,12),(13,16)]:
        board=Image.new('RGB',(1536,(last-first+1)*480),'#222222')
        for row,index in enumerate(range(first,last+1)):
            with Image.open(args.out/'frames'/f'{index:03d}.png') as tile:board.paste(tile,(0,row*480))
        board.save(args.out/f'group-{first:02d}-{last:02d}.png')
        blind_board=Image.new('RGB',(1024,(last-first+1)*480),'#222222')
        for row,index in enumerate(range(first,last+1)):
            with Image.open(args.out/'blind-frames'/f'{index:03d}.png') as tile:blind_board.paste(tile,(0,row*480))
        blind_board.save(args.out/f'blind-group-{first:02d}-{last:02d}.png')
    for folder,label in zip(folders,labels):
        board=Image.new('RGB',(1024,5*472),'#222222')
        for index in range(17):
            with Image.open(args.out/folder/f'{index:03d}.png') as im:board.paste(im.resize((256,448)),((index%4)*256,(index//4)*472+24))
            ImageDraw.Draw(board).text(((index%4)*256+3,(index//4)*472+3),f'f{index} {label}',fill='white')
        board.save(args.out/f'{folder}-all17.png')
    subprocess.run(['ffmpeg','-v','error','-framerate','24','-i',str(args.out/'pairs/%03d.png'),'-frames:v','17','-c:v','libx264','-pix_fmt','yuv420p',str(args.out/'source-reference-four-cases.mp4')],check=True)
    shutil.copyfile(Path(__file__).with_name('review-template.html'),args.out/'review.html')
    report={'frames':17,'fps':24,'duration_seconds':17/24,'sample_span_seconds':16/24,'source_indices':[7,23],'temporal_quality':'UNVERIFIED','cases':provenance,'source_sha256':sha(args.inputs/'driver-24fps.mp4'),'actual_reference_sha256':sha(args.inputs/'reference.png'),'raw_png_method':'B012 existing raw-derived PNG files copied byte-for-byte; only new Lab raw tensors use same upstream clamp/make_grid/mul255/uint8','video_method':'Existing model MP4 decode then6column encode; no retiming, warp or interpolation','four_cell_layout':'B012MOV/B012STILL top, LAB_MOV/LAB_STILL bottom; same full canvas scaling','ui_controls_qa':'NOT_RUN','condition_blinding':'Random fixed globalA/B panels saved separately; mapping withheld until observations. Labelled main page separate. Sameagent not independent human.'}
    (args.out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
