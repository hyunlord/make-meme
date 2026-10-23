"""Private CPU paired driving review: raw RGB PNGs, exact input canvases, native24fps comparison."""
from __future__ import annotations
import argparse
import hashlib
import json
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
    parser.add_argument('inputs',type=Path)
    parser.add_argument('source_frames',type=Path)
    parser.add_argument('control',type=Path,help='STILL artifacts directory, read only')
    parser.add_argument('artifacts',type=Path)
    parser.add_argument('out',type=Path)
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    for folder in ['frames','output-raw','pairs']:(args.out/folder).mkdir()
    source=decode(args.inputs/'driver-24fps.mp4');encoded=decode(args.artifacts/'output.mp4');control_encoded=decode(args.control/'output.mp4')
    raw=torch.load(args.artifacts/'raw_output.pt',map_location='cpu',weights_only=True)
    assert isinstance(raw,torch.Tensor) and list(raw.shape)==[3,17,896,512] and bool(torch.isfinite(raw).all())
    value=raw[None].clamp(-1,1)
    pixels=(torch.stack([make_grid(u,nrow=1,normalize=True,value_range=(-1,1)) for u in value.unbind(2)],dim=1).permute(1,2,3,0)*255).to(torch.uint8).numpy()
    sheet=Image.new('RGB',(3*512,6*256),'#222222')
    selected_indices=(0,12,14,16)
    selected=Image.new('RGB',(1024,len(selected_indices)*480),'#222222')
    sourcefiles=[]
    still_raw=torch.load(args.control/'raw_output.pt',map_location='cpu',weights_only=True)
    assert isinstance(still_raw,torch.Tensor) and list(still_raw.shape)==[3,17,896,512] and bool(torch.isfinite(still_raw).all())
    still_value=still_raw[None].clamp(-1,1)
    still_pixels=(torch.stack([make_grid(u,nrow=1,normalize=True,value_range=(-1,1)) for u in still_value.unbind(2)],dim=1).permute(1,2,3,0)*255).to(torch.uint8).numpy()
    (args.out/'still-raw').mkdir()
    with Image.open(args.source_frames/'000.png') as im:reference=im.convert('RGB')
    assert np.array_equal(np.asarray(reference),source[0]), 'Reference/static must equal selected source first frame'
    for index in range(17):
        original=args.out/'still-raw'/f'{index:03d}.png'
        control=Image.fromarray(still_pixels[index]);control.save(original)
        assert control.size==(512,896)
        output=Image.fromarray(pixels[index]);output.save(args.out/'output-raw'/f'{index:03d}.png')
        four=Image.new('RGB',(1024,480),'#222222');draw=ImageDraw.Draw(four)
        for col,(image,label) in enumerate([(Image.fromarray(source[index]),'SOURCE'),(reference,'STATIC COPY f0'),(output,'MOV raw output'),(control,'STILL raw output')]):
            tile=ImageOps.contain(image,(256,448))
            four.paste(tile,(col*256+(256-tile.width)//2,24+(448-tile.height)//2))
            draw.text((col*256+3,4),f'f{index} {label}',fill='white')
        four.save(args.out/'frames'/f'{index:03d}.png')
        sheet.paste(four.resize((512,240)),((index%3)*512,(index//3)*256))
        pair=Image.new('RGB',(2048,928),'#222');draw=ImageDraw.Draw(pair)
        for c,(im,label) in enumerate([(Image.fromarray(source[index]),'SOURCE'),(reference,'STATIC COPY f0'),(Image.fromarray(encoded[index]),'MOV OUTPUT'),(Image.fromarray(control_encoded[index]),'STILL OUTPUT')]):
            pair.paste(im,(c*512,32));draw.text((c*512+4,5),label,fill='white')
        pair.save(args.out/'pairs'/f'{index:03d}.png')
        sourcefiles.append({'frame':index,'still_raw_png_sha256':sha(original)})
    for row,index in enumerate(selected_indices):
        with Image.open(args.out/'frames'/f'{index:03d}.png') as tile:selected.paste(tile,(0,row*480))
    sheet.save(args.out/'all17.png');selected.save(args.out/'selected.png')
    # Display every frame, grouped by fixed consecutive ranges; no frame selection.
    for first,last in [(0,4),(5,8),(9,12),(13,16)]:
        board=Image.new('RGB',(1024,(last-first+1)*480),'#222222')
        for row,index in enumerate(range(first,last+1)):
            with Image.open(args.out/'frames'/f'{index:03d}.png') as tile:board.paste(tile,(0,row*480))
        board.save(args.out/f'group-{first:02d}-{last:02d}.png')
    board=Image.new('RGB',(4*256,5*472),'#222222')
    for index in range(17):
        with Image.open(args.out/'output-raw'/f'{index:03d}.png') as im:board.paste(im.resize((256,448)),((index%4)*256,(index//4)*472+24))
        ImageDraw.Draw(board).text(((index%4)*256+3,(index//4)*472+3),f'f{index} MOV raw',fill='white')
    board.save(args.out/'output-all17.png')
    still_board=Image.new('RGB',(4*256,5*472),'#222222')
    for index in range(17):
        with Image.open(args.out/'still-raw'/f'{index:03d}.png') as im:still_board.paste(im.resize((256,448)),((index%4)*256,(index//4)*472+24))
        ImageDraw.Draw(still_board).text(((index%4)*256+3,(index//4)*472+3),f'f{index} STILL raw',fill='white')
    still_board.save(args.out/'still-all17.png')
    subprocess.run(['ffmpeg','-v','error','-framerate','24','-i',str(args.out/'pairs/%03d.png'),'-frames:v','17','-c:v','libx264','-pix_fmt','yuv420p',str(args.out/'source-static-mov-still.mp4')],check=True)
    shutil.copyfile(Path(__file__).with_name('review-template.html'),args.out/'review.html')
    report={'frames':17,'fps':24,'duration_seconds':17/24,'sample_span_seconds':16/24,'temporal_quality':'UNVERIFIED','raw_png_method':'Exact upstream cache_video clamp/make_grid(-1,1)/mul255/uint8 before lossy MP4 encoding','source_processing':'Actual decoded512x896 model input; same-size upstream center crop is identity framing. MOV and STILL raw tensors are independently converted without alteration. Source interval is [7,24), local f0 is original f7. Static copy deliberately repeats sourcef0. No per-frame zoom, warp or interpolation.','still_output_mp4_sha256':sha(args.control/'output.mp4'),'mov_raw_sha256':sha(args.artifacts/'raw_output.pt'),'mov_output_mp4_sha256':sha(args.artifacts/'output.mp4'),'source_video_sha256':sha(args.inputs/'driver-24fps.mp4'),'reference_sha256':sha(args.inputs/'reference.png'),'source_start_frame':7,'source_end_frame_exclusive':24,'still_raw_sha256':sha(args.control/'raw_output.pt'),'sourcefiles':sourcefiles,'comparison_video_method':'Decode each model MP4 then side-by-side encode; PNG panels instead use raw tensors. No frame interpolation or retiming.','ui_controls_qa':'UNVERIFIED until separate browser check'}
    (args.out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
