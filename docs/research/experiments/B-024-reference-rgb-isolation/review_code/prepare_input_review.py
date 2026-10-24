"""CPU-only full-canvas RGB/support inspection; overlays are review artifacts only."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw


def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rgb(p: Path) -> Image.Image:
    with Image.open(p) as im:
        if im.size != (896, 512):
            raise ValueError((str(p), im.size))
        return im.convert('RGB')


def support(mask: Image.Image) -> np.ndarray:
    return np.all(np.asarray(mask) == (255, 0, 0), axis=-1)


def overlay(image: Image.Image, mask: Image.Image) -> Image.Image:
    a = np.array(image).astype(np.float32)
    selected = support(mask)
    a[selected] = .7 * a[selected] + .3 * np.array([0, 255, 128])
    return Image.fromarray(a.astype(np.uint8))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('original', 'neutral', 'reference-mask', 'driver-rgb', 'driver-mask', 'output'):
        p.add_argument('--' + key, type=Path, required=True)
    args = p.parse_args()
    original, neutral, mask = map(rgb, (args.original, args.neutral, args.reference_mask))
    selected = support(mask)
    a,b=np.asarray(original),np.asarray(neutral)
    assert selected.any() and (~selected).any()
    assert np.array_equal(a[selected],b[selected]), 'Subject pixels changed'
    assert np.all(b[~selected]==128), 'Background is not exact RGB128'
    args.output.mkdir(parents=True,exist_ok=False)
    ref=Image.new('RGB',(448*5,280),'#202020')
    for i,(im,label) in enumerate(zip((original,neutral,mask,overlay(original,mask),overlay(neutral,mask)),('ORIGINAL RGB','NEUTRAL RGB','UNCHANGED SEMANTIC MASK','ORIGINAL + SUPPORT','NEUTRAL + SUPPORT'))):
        ref.paste(im.resize((448,256)),(448*i,24));ImageDraw.Draw(ref).text((448*i+4,4),label,fill='white')
    ref.save(args.output/'reference-comparison.png')
    sheet=Image.new('RGB',(1344,17*280),'#202020');records=[]
    for i in range(17):
        rp=args.driver_rgb/f'{i:03d}.png';mp=args.driver_mask/f'{i:03d}.png';im=rgb(rp);m=rgb(mp)
        for col,(panel,label) in enumerate(((im,'DRIVER RGB'),(m,'DRIVER MASK'),(overlay(im,m),'SUPPORT OVERLAY'))):
            sheet.paste(panel.resize((448,256)),(448*col,i*280+24));ImageDraw.Draw(sheet).text((448*col+4,i*280+4),f'{label} local{i} source{126+i} PTS{(126+i)/30:.4f}',fill='white')
        records.append({'local':i,'source_frame':126+i,'pts_seconds':(126+i)/30,'rgb_sha256':digest(rp),'mask_sha256':digest(mp),'support_pixels':int(support(m).sum())})
    sheet.save(args.output/'driver-all17.png')
    y,x=np.where(selected)
    report={'subject_pixel_equality':True,'non_subject_exact_rgb128':True,'reference_canvas':[896,512],'same_mask_used_for_both':True,'support_pixels':int(selected.sum()),'support_bbox_xyxy':[int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)],'reference_inputs':[{'path':str(f),'sha256':digest(f)} for f in (args.original,args.neutral,args.reference_mask)],'driver_frames':records,'operation':'Review overlay only: RED support receives 30% green tint; actual model inputs unchanged. Uniform downscale for sheets; no new segmentation.','temporal_quality':'UNVERIFIED'}
    (args.output/'input-review.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    main()
