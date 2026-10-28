# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run: existing research Python /absolute/sam_analysis.py /absolute/config.json [--cpu-only]
"""Offline existing SAM3.1 analysis; masks are never passed to the video generator."""
from pathlib import Path
import json
import sys
import time


def main() -> None:
    config_path = Path(sys.argv[1])
    assert config_path.is_absolute() and config_path.is_file()
    cfg = json.loads(config_path.read_text())
    from PIL import Image
    root = Path(cfg['inputs'])
    anchors = Path(cfg['anchors'])
    output = Path(cfg['output'])
    assert all(p.is_absolute() for p in (root, anchors, output))
    for case in ('case_rigid', 'case_nonrigid'):
        files = sorted((root/case/'source').glob('*.png'))
        assert len(files) == 33
        for path in files + [anchors/case/f'{role}.png' for role in ('start','end')]:
            with Image.open(path) as image:
                assert image.size == (832,480)
                image.verify()
    assert Path(cfg['checkpoint']).is_file() and Path(cfg['comfy_root']).is_dir()
    if '--cpu-only' in sys.argv:
        print(json.dumps({'status':'CPU_ENTRY_PASS','torch_imported':False,'images_verified':70}))
        return
    started = time.time()
    output.mkdir(parents=True,exist_ok=True)
    with (output/'attempt.json').open('x') as handle:
        json.dump({'started':started,'kind':'SAM_ANALYSIS_ONLY'},handle)
    sys.argv = [sys.argv[0]]
    sys.path.insert(0,cfg['comfy_root'])
    import numpy as np
    import torch
    import torch.nn.functional as functional
    import comfy.sd
    import comfy.model_management
    from comfy.ldm.sam3.tracker import unpack_masks
    from comfy_extras.nodes_sam3 import SAM3_Detect, SAM3_VideoTrack

    def rgb(path: Path):
        return torch.from_numpy(np.asarray(Image.open(path).convert('RGB')).copy()).float()/255

    def save_masks(case: str, name: str, masks, frames, source: str) -> list:
        folder = output/case/name
        folder.mkdir(parents=True,exist_ok=True)
        records=[]
        for index, mask in enumerate(masks):
            array=mask.cpu().numpy().astype(bool)
            yy,xx=np.where(array)
            record={'index':index,'role':'edited_subject','mask_source':source,'visible':bool(len(xx)),
                    'area':int(len(xx)),'bbox':None,'center':None,'uncertainty':[]}
            if len(xx):
                record['bbox']=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
                record['center']=[float(xx.mean()),float(yy.mean())]
                if xx.min()==0 or xx.max()==831 or yy.min()==0 or yy.max()==479:
                    record['uncertainty'].append('touches_frame_border')
            else:record['uncertainty'].append('not_detected_or_occluded')
            Image.fromarray(array.astype('uint8')*255).save(folder/f'{index:03d}-mask.png')
            pixels=(frames[index].cpu().numpy()*255).astype('uint8')
            pixels[array]=(pixels[array]*.55+np.array([0,255,80])*.45).astype('uint8')
            Image.fromarray(pixels).save(folder/f'{index:03d}-overlay.png')
            records.append(record)
        (folder/'objects.json').write_text(json.dumps(records,indent=2))
        return records

    model,clip,_,_=comfy.sd.load_checkpoint_guess_config(cfg['checkpoint'],output_vae=False)
    summary={'implementation':'existing ComfyUI SAM3.1 integration','revision':cfg['revision'],
             'sam_conditioning_video':False,'source_role_selection':'maximal first-frame overlap with separate DAVIS GT; no mask replacement',
             'cross_domain_role_mapping':'explicit edited_subject assignment, not automatic identity proof','cases':{}}
    with torch.inference_mode():
        for case,query in (('case_rigid','car'),('case_nonrigid','dog')):
            conditioning=clip.encode_from_tokens_scheduled(clip.tokenize(query))
            frames=torch.stack([rgb(p) for p in sorted((root/case/'source').glob('*.png'))])
            tracked=SAM3_VideoTrack.execute(frames,model,conditioning=conditioning,detection_threshold=.5,max_objects=4,detect_interval=1)[0]
            packed=tracked['packed_masks']
            case_out=output/case;case_out.mkdir(exist_ok=True)
            if packed is None:
                summary['cases'][case]={'status':'SOURCE_NOT_DETECTED','query':query}
                continue
            np.savez_compressed(case_out/'sam_raw_packed.npz',masks=packed.cpu().numpy())
            all_masks=unpack_masks(packed).float()
            masks=functional.interpolate(all_masks,size=(480,832),mode='bilinear',align_corners=False)>.5
            gt_files=sorted((root/case/'source_gt').glob('*.png'))
            gt=torch.from_numpy(np.asarray(Image.open(gt_files[0])).copy()>0)
            ious=[]
            for candidate in masks[0]:
                candidate=candidate.cpu();union=(candidate|gt).sum().item()
                ious.append(float((candidate&gt).sum().item()/union) if union else 0.)
            selected=max(range(len(ious)),key=ious.__getitem__)
            rows=save_masks(case,'source',masks[:,selected],frames,'SAM3.1')
            result={'status':'SAM_ANALYSIS_COMPLETED','query':query,'track_index':selected,'first_frame_gt_ious':ious,
                    'frame_count':len(rows),'visible_frames':sum(row['visible'] for row in rows),'anchors':{}}
            for role in ('start','end'):
                frame=rgb(anchors/case/f'{role}.png').unsqueeze(0)
                detected,boxes=SAM3_Detect.execute(model,frame,conditioning=conditioning,threshold=.5,refine_iterations=2,individual_masks=False)
                anchor_rows=save_masks(case,role,detected>.5,frame,'SAM3.1')
                result['anchors'][role]={'boxes':boxes,'visible':anchor_rows[0]['visible'],'role':'edited_subject','mapping':'reviewable spatial/appearance assignment'}
            summary['cases'][case]=result
            (output/'summary.json').write_text(json.dumps(summary,indent=2))
    comfy.model_management.unload_all_models()
    torch.cuda.empty_cache()
    summary.update(finished=time.time(),elapsed_seconds=time.time()-started,status='SAM_ANALYSIS_COMPLETED')
    (output/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary))

if __name__=='__main__':
    main()
