"""Render already-decoded VAE tensors; never instantiate a model or encode/decode."""
from pathlib import Path
import argparse
import hashlib
import json
import torch
from PIL import Image, ImageDraw


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('root',type=Path);a=p.parse_args();out=a.root/'reports/condition-reconstruction';out.mkdir(exist_ok=False)
    records=[]
    for label,shape in [('reference',(3,1,512,896)),('driving',(3,17,256,448))]:
        src=a.root/'artifacts'/f'decoded_{label}.pt';tensor=torch.load(src,map_location='cpu',weights_only=True)
        assert isinstance(tensor,torch.Tensor) and tuple(tensor.shape)==shape and bool(torch.isfinite(tensor).all())
        frames=((tensor.clamp(-1,1)+1)/2*255).to(torch.uint8).permute(1,2,3,0).numpy()
        folder=out/label;folder.mkdir();width,height=shape[3],shape[2]
        sheet=Image.new('RGB',(width*3,(height+24)*((shape[1]+2)//3)),'#202020')
        for i,frame in enumerate(frames):
            im=Image.fromarray(frame);im.save(folder/f'{i:03d}.png');x=(i%3)*width;y=(i//3)*(height+24);sheet.paste(im,(x,y+24));ImageDraw.Draw(sheet).text((x+4,y+4),f'{label} local{i} native {width}x{height}',fill='white')
        sheet.save(out/f'{label}-all.png');records.append({'tensor':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'shape':list(shape),'native_spatial_size':[width,height],'range':[float(tensor.min()),float(tensor.max())]})
    (out/'manifest.json').write_text(json.dumps({'scope':'CPU visualization of existing VAE decode; no new model operation','operation':'clamp(-1,1), affine to[0,255], uint8; natural resolution retained','driving_resolution':'448x256 is half source spatial resolution, not source bit equality','records':records,'temporal':'UNVERIFIED'},indent=2)+'\n')


if __name__=='__main__':main()
