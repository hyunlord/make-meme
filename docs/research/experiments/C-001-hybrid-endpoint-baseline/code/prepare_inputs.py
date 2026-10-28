# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow", "numpy"]
# ///
# Run: python prepare_inputs.py DAVIS_ROOT OUTPUT_ROOT
"""Freeze two real 33-frame DAVIS clips with common RGB/mask geometry."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import numpy as np
from PIL import Image, ImageDraw


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(dataset: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    selection = [('case_rigid', 'car-roundabout', 30, 'car-shadow', 0),
                 ('case_nonrigid', 'dog', 0, 'dog-gooses', 85)]
    manifests = []
    for case, source, begin, target, reference in selection:
        root = output/case
        for name in ('source','source_gt','original_source','original_gt','reference'):
            (root/name).mkdir(parents=True)
        records = []
        for local, frame in enumerate(range(begin, begin+33)):
            rgb_path = dataset/'JPEGImages/480p'/source/f'{frame:05d}.jpg'
            mask_path = dataset/'Annotations/480p'/source/f'{frame:05d}.png'
            with Image.open(rgb_path) as raw, Image.open(mask_path) as indexed:
                rgb = raw.convert('RGB'); support = Image.fromarray((np.asarray(indexed)==1).astype('uint8')*255)
            assert support.getbbox(), 'Source instance absent'
            scale = min(832/rgb.width,480/rgb.height)
            size = (round(rgb.width*scale),round(rgb.height*scale))
            offset = ((832-size[0])//2,(480-size[1])//2)
            image = Image.new('RGB',(832,480)); mask = Image.new('L',(832,480))
            image.paste(rgb.resize(size,Image.Resampling.LANCZOS),offset)
            mask.paste(support.resize(size,Image.Resampling.NEAREST),offset)
            image.save(root/'source'/f'{local:03d}.png'); mask.save(root/'source_gt'/f'{local:03d}.png')
            shutil.copy2(rgb_path,root/'original_source'/rgb_path.name)
            shutil.copy2(mask_path,root/'original_gt'/mask_path.name)
            pixels = np.asarray(mask)>0; yy,xx=np.where(pixels)
            records.append({'model_index':local,'source_index':frame,'source_rgb_sha256':digest(rgb_path),
                'source_gt_sha256':digest(mask_path),'source_size':list(rgb.size),'resized_size':size,'offset':offset,
                'bbox':mask.getbbox(),'center':[float(xx.mean()),float(yy.mean())],'area':int(pixels.sum()),'visible':True,
                'role_id':'edited_subject','analysis_origin':'DAVIS_GT_MASK_GIVEN','sam_conditioning':False})
        rgb_path=dataset/'JPEGImages/480p'/target/f'{reference:05d}.jpg'
        mask_path=dataset/'Annotations/480p'/target/f'{reference:05d}.png'
        with Image.open(rgb_path) as raw,Image.open(mask_path) as indexed:
            rgb=raw.convert('RGB'); support=Image.fromarray((np.asarray(indexed)==1).astype('uint8')*255)
        box=support.getbbox();assert box
        margin=round(max(box[2]-box[0],box[3]-box[1])*.10)
        crop=(max(0,box[0]-margin),max(0,box[1]-margin),min(rgb.width,box[2]+margin),min(rgb.height,box[3]+margin))
        shutil.copy2(rgb_path,root/'reference/original.jpg');shutil.copy2(mask_path,root/'reference/instance-mask.png')
        rgb.save(root/'reference/full.png');rgb.crop(crop).save(root/'reference/crop.png')
        for i,name in [(0,'start'),(32,'end')]:shutil.copyfile(root/'source'/f'{i:03d}.png',root/f'{name}.png')
        subprocess.run(['ffmpeg','-v','error','-n','-framerate','16','-i',str(root/'source/%03d.png'),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(root/'source.mp4')],check=True)
        sheet=Image.new('RGB',(832*3,510*11),'#202020');draw=ImageDraw.Draw(sheet)
        for index in range(33):
            with Image.open(root/'source'/f'{index:03d}.png') as frame:
                x,y=(index%3)*832,(index//3)*510;sheet.paste(frame,(x,y+25));draw.text((x+5,y+5),f'{case} local {index} source {begin+index}',fill='white')
        sheet.resize((1248,2805)).save(root/'contact_sheet.jpg')
        manifest={'case_id':case,'operation':'replace_subject','source_sequence':source,'source_frames':list(range(begin,begin+33)),
            'target_sequence':target,'target_frame':reference,'target_track':1,'source_track':1,'reference_crop':crop,
            'reference_sha256':digest(rgb_path),'reference_mask_sha256':digest(mask_path),'source_fps':None,
            'timebase_assumed':True,'preview_fps':16,'model_frame_count':33,'canvas':[832,480],
            'sample_span_seconds_assumed':2,'file_duration_seconds':33/16,'rgb_resample':'LANCZOS','mask_resample':'NEAREST',
            'anchors':[{'model_index':0,'role':'start'},{'model_index':32,'role':'end'}],'records':records}
        (root/'manifest.json').write_text(json.dumps(manifest,indent=2));manifests.append(manifest)
    (output/'INPUTS.json').write_text(json.dumps({'dataset':'DAVIS2017trainval480p','new_download_bytes':0,'cases':manifests},indent=2))

if __name__=='__main__':prepare(*map(Path,sys.argv[1:]))
