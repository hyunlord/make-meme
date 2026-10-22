"""CPU-only private RGB/mask preparation; no diffusion or learned segmentation.
Usage: python input_preflight.py B002_ROOT B006_ROOT OUTPUT_ROOT
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import cv2
import numpy as np
from PIL import Image, ImageDraw


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def transform(image, mask, height=896, width=512):
    w,h=image.size
    if w/h>width/height: size=(int(w*height/h),height)
    else: size=(width,int(h*width/w))
    left=(size[0]-width)//2;top=(size[1]-height)//2
    box=(left,top,left+width,top+height)
    rgb=image.resize(size,Image.Resampling.BICUBIC).crop(box)
    # Categorical IDs remain discrete; upstream uses bicubic on masks. Record this difference.
    ids=mask.resize(size,Image.Resampling.NEAREST).crop(box)
    return rgb,ids,dict(source_size=[w,h],resized_size=list(size),crop_box=list(box),target_hw=[height,width],rgb_sampler='PIL bicubic; upstream torchvision bicubic pixel equality not assumed',mask_sampler='nearest categorical IDs; prepared target-size files need no further resize')


def encode(folder,output):
    command=['ffmpeg','-y','-v','error','-framerate','24','-i',str(folder/'%03d.png'),'-frames:v','17','-fps_mode','passthrough','-c:v','libx264rgb','-crf','0','-pix_fmt','rgb24',str(output)]
    subprocess.run(command,check=True,timeout=90)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=avg_frame_rate,nb_read_frames,duration,width,height','-of','json',str(output)]))
    stream=probe['streams'][0];assert stream['avg_frame_rate']=='24/1' and int(stream['nb_read_frames'])==17
    return dict(command=command,probe=probe,sha256=sha(output))


b002,b006,root=map(Path,sys.argv[1:]);out=root/'outputs/input_preflight';inp=root/'inputs/input_preflight'
for name in ['source','driver_mask','prepared_driver','prepared_mask']:(inp/name).mkdir(parents=True,exist_ok=True)
out.mkdir(parents=True,exist_ok=True)
photo=b002/'inputs/R-original.jpeg';alpha=b002/'inputs/alpha.png'
assert sha(photo)=='54f8052c7264139a41d2818d5c881abd2442f462b5d02cc7908c1f360f00fadb'
assert sha(alpha)=='29ea5d20bf6ee1bf85e263ba14ab1cc3063f4dd6670064a6f63f3184cc725a3a'
ref=Image.open(photo).convert('RGB');a=np.asarray(Image.open(alpha).convert('L'))>127
assert a.shape==(ref.height,ref.width)
refmask=np.zeros((*a.shape,3),dtype=np.uint8);refmask[a]=[255,0,0]
ref.save(inp/'reference.png');Image.fromarray(refmask).save(inp/'reference-mask.png')
refready,refids,reftransform=transform(ref,Image.fromarray(refmask));refready.save(inp/'reference-512x896.png');refids.save(inp/'reference-mask-512x896.png')
annotations=json.loads((b006/'annotations/annotated_landmarks.json').read_text())['frames'];records=[]
cv2.setRNGSeed(20261022)
for index,frame in enumerate(annotations):
    path=b006/'inputs/source'/f'{index:03d}.png';assert sha(path)==frame['source_sha256']
    image=Image.open(path).convert('RGB');rgb=np.asarray(image);assert image.size==(512,288)
    # Broad known background; each frame optimized independently, no flow/interpolation.
    seeds=np.full((288,512),cv2.GC_BGD,np.uint8);seeds[62:260,203:325]=cv2.GC_PR_BGD
    cv2.fillPoly(seeds,[np.array([[279,82],[301,91],[294,118],[296,175],[280,211],[274,242],[219,230],[237,196],[241,142],[269,108]],np.int32)],cv2.GC_PR_FGD)
    cv2.fillPoly(seeds,[np.array([[264,123],[282,127],[278,187],[254,192],[251,151]],np.int32)],cv2.GC_FGD)
    for point in frame['landmarks'].values():
        if point['xy'] is not None:cv2.circle(seeds,tuple(point['xy']),1,cv2.GC_FGD,-1)
    cv2.grabCut(cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR),seeds,None,np.zeros((1,65),np.float64),np.zeros((1,65),np.float64),5,cv2.GC_INIT_WITH_MASK)
    foreground=np.isin(seeds,[cv2.GC_FGD,cv2.GC_PR_FGD]);mask=np.zeros_like(rgb);mask[foreground]=[255,0,0]
    image.save(inp/'source'/f'{index:03d}.png');Image.fromarray(mask).save(inp/'driver_mask'/f'{index:03d}.png')
    ready,ids,geometry=transform(image,Image.fromarray(mask));ready.save(inp/'prepared_driver'/f'{index:03d}.png');ids.save(inp/'prepared_mask'/f'{index:03d}.png')
    kept=[]
    for name,point in frame['landmarks'].items():
        if point['xy'] is not None:
            x,y=point['xy'];sx,sy=geometry['resized_size'];left,top,_,_=geometry['crop_box'];xy=[x*sx/512-left,y*sy/288-top]
            kept.append(dict(name=name,target_xy=xy,inside=0<=xy[0]<512 and 0<=xy[1]<896))
    assert all(p['inside'] for p in kept)
    sheet=Image.new('RGB',(1536,896));sheet.paste(ready,(0,0));sheet.paste(ids,(512,0));overlay=Image.blend(ready,ids,.35);sheet.paste(overlay,(1024,0));sheet.save(out/f'driver-{index:02d}.jpg',quality=95)
    records.append(dict(frame=index,source_sha256=sha(path),foreground_pixels=int(foreground.sum()),geometry=geometry,visible_landmark_crop_check=kept,mask_status='UNREVIEWED_BOUNDARY_NOT_GROUND_TRUTH'))
refsheet=Image.new('RGB',(1536,896));refsheet.paste(refready,(0,0));refsheet.paste(refids,(512,0));refsheet.paste(Image.blend(refready,refids,.35),(1024,0));refsheet.save(out/'reference-pair.jpg',quality=95)
videos={name:encode(inp/folder,out/f'{name}-24fps.mp4') for name,folder in [('original-rgb','source'),('prepared-rgb','prepared_driver'),('prepared-mask','prepared_mask')]}
# Check actual decoded lossless mask colors, not only encoded metadata.
decoded=subprocess.check_output(['ffmpeg','-v','error','-i',str(out/'prepared-mask-24fps.mp4'),'-f','rawvideo','-pix_fmt','rgb24','-'])
pixels=np.frombuffer(decoded,np.uint8).reshape(17,896,512,3);colors=np.unique(pixels.reshape(-1,3),axis=0);assert colors.tolist()==[[0,0,0],[255,0,0]]
report=dict(reference_photo_sha256=sha(photo),reference_alpha_sha256=sha(alpha),reference_geometry=reftransform,frames=records,videos=videos,decoded_mask_colors=colors.tolist(),fps=24,frame_count=17,file_duration_seconds=17/24,endpoint_interval_seconds=16/24,default16fps_duration_seconds=17/16,writer_override='Upstream generate.py cache_video fps=cfg.sample_fps; explicitly set cfg.sample_fps=24 before saving, do not relabel16fps output. No upstream file changed.',identity_semantics='red same character ID in reference and driver; black unrelated background; no white visible-background claims',mask_method='Reference B002 recorded manual/GrabCut alpha reused; driver independent GrabCut5 with fixed rough polygon and observed visible-point seeds. Not learned, not automatic accuracy evidence.',mode='animation replace_flag=false',diffusion_inference='NOT_RUN',temporal_quality='UNVERIFIED')
(root/'reports').mkdir(exist_ok=True);(root/'reports/input_preflight.json').write_text(json.dumps(report,indent=2)+'\n')
print('CPU RGB/mask/FPS files created. Mask boundaries still require visual review.')
