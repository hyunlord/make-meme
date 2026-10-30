"""Prepare fixed source-group split with dataset masks, without model inference."""
from pathlib import Path
import hashlib
import json
import sys
import time
import cv2
import numpy as np
from PIL import Image, ImageDraw


def sha(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def prepare(dataset: Path, split_path: Path, destination: Path) -> None:
    started = time.monotonic()
    spec = json.loads(split_path.read_text())
    destination.mkdir(parents=True,exist_ok=False)
    cases = []
    for clip in spec['clips']:
        root = destination/clip['sequence']
        for name in ('source','mask','layout','anchors'):
            (root/name).mkdir(parents=True)
        with Image.open(dataset/'Annotations/480p'/clip['sequence']/'00000.png') as image:
            positive = np.unique(np.array(image)); positive = positive[(positive>0)&(positive<255)]
        assert len(positive)>0
        track = int(positive.min())
        records=[]
        for local,frame in enumerate(clip['frames']):
            rgb_path=dataset/'JPEGImages/480p'/clip['sequence']/f'{frame:05d}.jpg'
            mask_path=dataset/'Annotations/480p'/clip['sequence']/f'{frame:05d}.png'
            with Image.open(rgb_path) as im,Image.open(mask_path) as mi:
                rgb=im.convert('RGB'); labels=np.array(mi); original_size=rgb.size
                assert labels.shape== (rgb.height,rgb.width)
                support=Image.fromarray(np.uint8(labels==track)*255)
                scale=min(416/rgb.width,240/rgb.height)
                size=(round(rgb.width*scale),round(rgb.height*scale)); offset=((416-size[0])//2,(240-size[1])//2)
                canvas=Image.new('RGB',(416,240),'black');canvas.paste(rgb.resize(size,Image.Resampling.LANCZOS),offset)
                mask=Image.new('L',(416,240),0);mask.paste(support.resize(size,Image.Resampling.NEAREST),offset)
            arr=np.array(mask); contours,_=cv2.findContours(arr,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
            layout=np.full((240,416,3),255,np.uint8);cv2.drawContours(layout,contours,-1,(0,0,0),3)
            canvas.save(root/'source'/f'{local:03d}.png');mask.save(root/'mask'/f'{local:03d}.png');Image.fromarray(layout).save(root/'layout'/f'{local:03d}.png')
            if local in (0,32):canvas.save(root/'anchors'/('start.png' if local==0 else 'end.png'))
            y,x=np.nonzero(arr)
            box=[int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)] if len(x) else None
            records.append({'index':local,'source_frame_id':frame,'source_rgb_sha256':sha(rgb_path),'indexed_mask_sha256':sha(mask_path),
                            'source_size':list(original_size),'resized_size':list(size),'offset':list(offset),'selected_label':track,
                            'selected_area':int(len(x)),'selected_visible':bool(len(x)),'bbox_xyxy':box,
                            'rgb_sha256':sha(root/'source'/f'{local:03d}.png'),'mask_sha256':sha(root/'mask'/f'{local:03d}.png'),'layout_sha256':sha(root/'layout'/f'{local:03d}.png')})
        manifest={**clip,'selected_label':track,'mask_origin':'MASK_GIVEN / DATASET_MASK_ASSISTED','canvas':[416,240],
                  'rgb_resample':'LANCZOS','mask_resample':'NEAREST','transform':'full-frame aspect-fit; black RGB/zero mask padding; no crop or stretch',
                  'point_pixel_centers':'integer xy denotes pixel center; normalized (x+0.5)/width, (y+0.5)/height',
                  'source_fps':None,'preview_fps':16,'timebase_assumed':True,'records':records}
        (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        sheet=Image.new('RGB',(416*3,264*3),'#202020');draw=ImageDraw.Draw(sheet)
        for n,t in enumerate((0,4,8,12,16,20,24,28,32)):
            with Image.open(root/'source'/f'{t:03d}.png') as im:sheet.paste(im,(n%3*416,n//3*264+24))
            draw.text((n%3*416+5,n//3*264+5),f'{clip["split"]} {clip["sequence"]} frame{t}',fill='white')
        sheet.save(root/'source-fixed9.jpg',quality=92)
        cases.append({'sequence':clip['sequence'],'split':clip['split'],'manifest_sha256':sha(root/'manifest.json'),
                      'selected_label':track,'missing_label_frames':[r['index'] for r in records if not r['selected_visible']]})
    report={'status':'COMPLETE','clips':cases,'frames':33*len(cases),'split_sha256':sha(split_path),'seconds':time.monotonic()-started,'new_media_download_bytes':0}
    (destination/'data-manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':
    prepare(*(Path(x).resolve() for x in sys.argv[1:]))
