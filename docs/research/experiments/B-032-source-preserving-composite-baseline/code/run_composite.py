"""Read frozen private manifest, composite on CPU, encode two new derived MP4s."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import subprocess
import time
import numpy as np
from PIL import Image
from compositor import blend, fixed_envelope, mask_assisted, radius_for_sources, to_uint8


def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument('manifest',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    started=time.monotonic()
    manifest=json.loads(args.manifest.read_text())
    for item in manifest['files']:
        if sha(Path(item['path'])) != item['sha256']:
            raise ValueError(f"Input changed: {item['role']}")
    source_paths=[Path(p) for p in manifest['source_frames']]
    source=np.stack([np.array(Image.open(p).convert('RGB')) for p in source_paths])
    masks=np.stack([np.array(Image.open(p).convert('RGB')) for p in manifest['source_masks']])
    supports=np.all(masks==[255,0,0],axis=-1)
    targets=np.stack([np.array(Image.open(p))>0 for p in manifest['target_masks']])
    anchor=np.array(Image.open(manifest['anchor_support']).convert('L'))>0
    generated=np.load(manifest['generated_float'],allow_pickle=False)
    if source.shape != (17,512,896,3) or generated.shape != source.shape:
        raise ValueError('Frame/canvas mismatch')
    if not np.isfinite(generated).all() or generated.min() < -1 or generated.max()>1:
        raise ValueError('Raw range violation')
    normalized=source.astype(np.float32)/127.5-1
    fixed,box=fixed_envelope(supports,anchor)
    radius=radius_for_sources(supports)
    report={'fixed_box_xyxy_exclusive':asdict(box),'dilation_radius':radius,'cases':{},
            'source_fps':None,'preview_fps':24,'timebase_assumed':True,
            'range':'float32 RGB [-1,1]; floor((clip(x,-1,1)+1)*127.5); source E0 bytes explicitly copied',
            'gpu_workers':0,'vae_decodes':0,'new_derived_encodes':2}
    args.output.mkdir(parents=True,exist_ok=True)
    for name in ('FIXED_ENVELOPE','MASK_ASSISTED'):
        begin=time.monotonic();root=args.output/name
        if root.exists(): raise FileExistsError(root)
        for sub in ('frames','edit-support'): (root/sub).mkdir(parents=True)
        rows=[]
        for i in range(17):
            e=fixed if name=='FIXED_ENVELOPE' else mask_assisted(supports[i],targets[i],radius)
            y=blend(normalized[i],generated[i],e)
            out=to_uint8(y);out[e==0]=source[i][e==0]
            raw8=to_uint8(generated[i])
            checks={'frame':i,'source_exact_float':bool(np.array_equal(y[e==0],normalized[i][e==0])),
                    'generated_exact_float':bool(np.array_equal(y[e==1],generated[i][e==1])),
                    'source_exact_uint8':bool(np.array_equal(out[e==0],source[i][e==0])),
                    'generated_exact_uint8':bool(np.array_equal(out[e==1],raw8[e==1])),
                    'target_outside_nonzero':int(np.count_nonzero(targets[i] & (e==0))),
                    'target_outside_core':int(np.count_nonzero(targets[i] & (e<1))),
                    'source_outside_core':int(np.count_nonzero(supports[i] & (e<1))),
                    'edit_nonzero_pixels':int(np.count_nonzero(e)),
                    'edit_core_pixels':int(np.count_nonzero(e==1))}
            if not all(checks[k] for k in ('source_exact_float','generated_exact_float','source_exact_uint8','generated_exact_uint8')):
                raise ValueError('Endpoint contract failed')
            rows.append(checks)
            Image.fromarray(out).save(root/'frames'/f'{i:03}.png')
            Image.fromarray(np.rint(e*255).astype(np.uint8)).save(root/'edit-support'/f'{i:03}.png')
        composite_seconds=time.monotonic()-begin;encode_begin=time.monotonic()
        command=['ffmpeg','-v','error','-nostdin','-framerate','24','-i',str(root/'frames'/'%03d.png'),
                 '-frames:v','17','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(root/'output.mp4')]
        subprocess.run(command,check=True)
        probe=subprocess.run(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries',
                              'stream=width,height,r_frame_rate,nb_read_frames','-of','json',str(root/'output.mp4')],check=True,capture_output=True,text=True)
        metadata=json.loads(probe.stdout)['streams'][0]
        if metadata['nb_read_frames']!='17' or metadata['r_frame_rate']!='24/1': raise ValueError('Encoding contract')
        report['cases'][name]={'frames':rows,'composition_and_png_seconds':composite_seconds,
                               'encode_and_probe_seconds':time.monotonic()-encode_begin,
                               'mp4_sha256':sha(root/'output.mp4'),'mp4_bytes':(root/'output.mp4').stat().st_size,'ffprobe':metadata}
    report['input_hashes_unchanged']=all(sha(Path(x['path']))==x['sha256'] for x in manifest['files'])
    if not report['input_hashes_unchanged']: raise ValueError('Inputs changed')
    report['elapsed_seconds']=time.monotonic()-started
    (args.output/'measurements.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2))
if __name__=='__main__': main()
