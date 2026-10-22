# /// script
# dependencies = ["Pillow", "numpy", "opencv-python"]
# ///
# Run: python prepare_reference.py RUN_ROOT LAB_PHOTO SOURCE_F0 (CPU only; private assets)
"""Recorded manual silhouette seeds plus nonlearned GrabCut; no RGB synthesis."""
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(sys.argv[1])
SOURCE = Path(sys.argv[2])
P_SOURCE = Path(sys.argv[3])
# Observed full-resolution coordinates, decoded Image.open.convert RGB; no EXIF transpose.
OUTLINE = [(406,780),(410,672),(421,561),(448,510),(510,472),(574,450),(635,452),
 (699,467),(753,498),(797,525),(822,579),(829,650),(819,720),(820,787),(800,796),
 (829,831),(858,906),(879,992),(891,1089),(894,1172),(911,1272),(917,1404),
 (919,1515),(926,1622),(944,1673),(950,1718),(929,1746),(884,1755),(846,1739),
 (827,1707),(831,1659),(833,1583),(839,1516),(831,1460),(811,1401),
 (800,1465),(748,1476),(699,1461),(650,1480),(598,1482),(549,1456),
 (516,1474),(470,1520),(467,1582),(475,1655),(463,1709),(435,1742),
 (392,1749),(366,1724),(355,1681),(368,1629),(380,1541),(403,1450),
 (399,1348),(410,1251),(421,1158),(421,1060),(435,972),(448,892),(464,821),(448,759)]

def main() -> None:
    started=time.monotonic(); out=ROOT/'inputs';out.mkdir(parents=True,exist_ok=True)
    shutil.copy2(SOURCE,out/'R-original.jpeg');shutil.copy2(P_SOURCE,out/'P.png')
    with Image.open(SOURCE) as image: rgb=np.asarray(image.convert('RGB')).copy()
    h,w=rgb.shape[:2]; polygon=np.zeros((h,w),np.uint8)
    observed=np.array(OUTLINE,np.float64) * np.array([w/1368,h/1824])
    full_outline=np.rint(observed).astype(np.int32)
    cv2.fillPoly(polygon,[full_outline],255)
    expanded=cv2.dilate(polygon,np.ones((31,31),np.uint8))
    inner=cv2.erode(polygon,np.ones((25,25),np.uint8))
    labels=np.full((h,w),cv2.GC_BGD,np.uint8)
    labels[expanded>0]=cv2.GC_PR_BGD;labels[polygon>0]=cv2.GC_PR_FGD;labels[inner>0]=cv2.GC_FGD
    cv2.setRNGSeed(20261022)
    cv2.grabCut(cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR),labels,None,np.zeros((1,65)),np.zeros((1,65)),5,cv2.GC_INIT_WITH_MASK)
    alpha=np.where((labels==cv2.GC_FGD)|(labels==cv2.GC_PR_FGD),255,0).astype(np.uint8)
    # Fill internal alpha holes in dog only; exterior-connected between-legs bedding stays excluded.
    contours,_=cv2.findContours(alpha,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    alpha[:]=0;cv2.drawContours(alpha,[max(contours,key=cv2.contourArea)],-1,255,cv2.FILLED)
    alpha[polygon==0]=0  # Recorded manual silhouette excludes GrabCut bedding/shadow spill.
    white=np.full_like(rgb,255);white[alpha==255]=rgb[alpha==255]
    Image.fromarray(alpha).save(out/'alpha.png');Image.fromarray(white).save(out/'R-bg.png')
    Image.fromarray(rgb).save(out/'R-original-decoded.png')
    model=ImageOps.pad(Image.fromarray(white),(512,288),color=(128,128,128));model.save(out/'R-bg-model512288.png')
    original_model=ImageOps.pad(Image.fromarray(rgb),(512,288),color=(128,128,128));original_model.save(out/'R-original-model512288.png')
    sheet=Image.new('RGB',(1368,680),(35,35,35));draw=ImageDraw.Draw(sheet)
    for i,(title,img) in enumerate([('Decoded original',Image.fromarray(rgb)),('White background; same RGB',Image.fromarray(white)),('B001 model pad 512x288',model)]):
        tile=ImageOps.contain(img,(440,620));sheet.paste(tile,(i*456+(456-tile.width)//2,40+(620-tile.height)//2));draw.text((i*456+8,10),title,fill='white')
    sheet.save(out/'reference-mask-review.jpg',quality=96)
    exact=bool(np.array_equal(white[alpha==255],rgb[alpha==255]));assert exact
    metadata={'method':'Manual fullresolution polygon seeds + OpenCV GrabCut5, RNG20261022; largest exterior contour fill removes internal alpha holes; recorded manual silhouette clips bedding/shadow spill. No learned model, no feathering or RGB change.',
      'manual_outline_view_xy':OUTLINE,'observation_canvas':[1368,1824],'actual_outline_xy':full_outline.tolist(),'source_path':str(SOURCE),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
      'decoded_orientation':'Image.open.convert RGB, no exif_transpose','size':[w,h],'background_rgb':[255,255,255],
      'foreground_pixels':int((alpha==255).sum()),'all_retained_foreground_rgb_exact':exact,
      'foreground_source_bytes_sha256':hashlib.sha256(rgb[alpha==255].tobytes()).hexdigest(),
      'foreground_output_bytes_sha256':hashlib.sha256(white[alpha==255].tobytes()).hexdigest(),
      'alpha_sha256':hashlib.sha256((out/'alpha.png').read_bytes()).hexdigest(),
      'R_bg_sha256':hashlib.sha256((out/'R-bg.png').read_bytes()).hexdigest(),
      'cpu_processing_seconds':time.monotonic()-started,'manual_masking':'Human-directed polygon coordinates; not automatic segmentation performance',
      'model_normalization':'Same B001 ImageOps.pad RGB512x288 gray128; wholecanvas preserved','visual_review':'PENDING'}
    (out/'mask-method.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps({k:v for k,v in metadata.items() if k!='manual_outline_xy'},indent=2))

if __name__=='__main__': main()
