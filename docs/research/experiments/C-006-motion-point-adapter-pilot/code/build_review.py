"""Offline matched-index review. Original generated MP4 bytes remain unchanged."""
from pathlib import Path
import argparse
import hashlib
import html
import json
import shutil
import subprocess
import time
import numpy as np
from PIL import Image, ImageDraw

STYLE='''body{background:#10151e;color:#edf3fa;font:16px/1.6 system-ui;margin:0}main{max-width:1600px;margin:auto;padding:24px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}figure{margin:0;padding:12px;background:#1b2431}img,video{width:100%;display:block;height:auto}button,select{font:inherit;padding:8px}button:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #8cceff}p{max-width:95ch}figcaption{overflow-wrap:anywhere}input{width:100%}a{color:#8cceff}summary{cursor:pointer}h2{margin-top:48px}.zoom{overflow:auto}.zoom img{width:200%;max-width:none}@media(max-width:650px){main{padding:12px}}'''
JS='''document.querySelectorAll('section').forEach(s=>{const slider=s.querySelector('input');slider.oninput=()=>{let i=+slider.value;s.querySelector('output').textContent=i;s.querySelectorAll('[data-frames]').forEach(x=>{x.src=JSON.parse(x.dataset.frames)[i];x.parentElement.href=x.src;});s.querySelectorAll('video').forEach(v=>{v.pause();v.currentTime=i/16;});};s.querySelector('[data-play]').onclick=()=>s.querySelectorAll('video').forEach(v=>{v.currentTime=+slider.value/16;v.play().catch(e=>s.querySelector('[role=status]').textContent=e.message);});s.querySelector('[data-pause]').onclick=()=>s.querySelectorAll('video').forEach(v=>v.pause());s.querySelector('[data-zoom]').onclick=()=>s.querySelectorAll('.frame').forEach(x=>x.classList.toggle('zoom'));});'''

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)
    assert sha(source)==sha(target)


def preview(pattern: Path, target: Path) -> None:
    subprocess.run(['ffmpeg','-v','error','-n','-framerate','16','-i',str(pattern),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(target)],check=True)


def fig(path: str, label: str, video: bool = False) -> str:
    escaped=html.escape(label)
    media=f'<video controls muted playsinline preload="metadata" src="{path}" aria-label="{escaped}"></video>' if video else f'<a href="{path}"><img loading="lazy" src="{path}" alt="{escaped}"></a>'
    return f'<figure>{media}<figcaption>{escaped}</figcaption></figure>'


def sheet(groups: list, indices: list[int], target: Path) -> None:
    canvas=Image.new('RGB',(416*len(indices),270*len(groups)),'#1b2431')
    draw=ImageDraw.Draw(canvas)
    for row,(label,paths) in enumerate(groups):
        for column,index in enumerate(indices):
            with Image.open(paths[index]) as image:
                image=image.convert('RGB');image.thumbnail((416,240))
                canvas.paste(image,(column*416,row*270+25))
            draw.text((column*416+5,row*270+3),f'{label} {index}/32',fill='white')
    canvas.save(target,quality=92,subsampling=0)


def all_sheet(label: str, paths: list[Path], target: Path) -> None:
    canvas=Image.new('RGB',(2496,1620),'#1b2431');draw=ImageDraw.Draw(canvas)
    for i,path in enumerate(paths):
        with Image.open(path) as image:canvas.paste(image.convert('RGB').resize((416,240)),((i%6)*416,(i//6)*270+25))
        draw.text(((i%6)*416+5,(i//6)*270+3),f'{label} {i}/32',fill='white')
    canvas.save(target,quality=92,subsampling=0)


def cost_panel(out: Path) -> str:
    """Publish measured stage times, without equating them to total cost."""
    reports = Path(__file__).resolve().parent.parent
    costs = json.loads((reports/'COSTS.json').read_text())
    for name in ('RESULTS.md','COSTS.json','LESSON_KO.md','REPRODUCE.md'):
        copy(reports/name, out/'reports'/name)
    tracker = costs['auxiliary']['tracker_primary_seconds'] + costs['auxiliary']['tracker_cross_seconds']
    passes = costs['auxiliary']['tracker_primary_passes'] + costs['auxiliary']['tracker_cross_passes']
    links = ' · '.join(f'<a href="reports/{name}">{name}</a>' for name in ('RESULTS.md','COSTS.json','LESSON_KO.md','REPRODUCE.md'))
    return f'<footer><h2>Measured cost and reports</h2><p>Training: {costs["training"]["updates"]} updates / {costs["training"]["active_seconds"]:.3f}s active. Video: {costs["video"]["normal_completed"]} completed / {costs["video"]["total_worker_internal_seconds"]:.3f}s worker-internal total. Tracker: {passes} passes / {tracker:.3f}s. These are stage timers, not whole-task wall time or energy cost.</p><p>Annotation/review time was not measured separately. Paid generation service calls: 0; local electricity cost is unmeasured. Full cache, failure, recovery and measurement limitations are retained in COSTS.json.</p><p>{links}</p></footer>'


def build(private: Path, out: Path) -> None:
    started=time.monotonic();out.mkdir(parents=True,exist_ok=False)
    exclusions=json.loads((private/'point-exclusions.json').read_text())['clips']
    sections=[];receipt={'cases':{},'quality':'SEE_CASE_REVIEWS','temporal':'UNVERIFIED','original_mp4_sha256':{}}
    for sequence in ('horsejump-low','lucia','cross-id-dog'):
        data=private/'data'/sequence
        if sequence=='cross-id-dog':
            data=private/'cross-id-dog'
            if not all((private/'outputs'/sequence/mode/'generated.mp4').is_file() for mode in ('BASE','ON','NULL')):
                continue
        if not data.exists():
            if sequence=='cross-id-dog':continue
            raise FileNotFoundError(data)
        root=out/sequence;root.mkdir()
        source=sorted((data/'source').glob('*.png'))
        assert len(source)==33
        groups=[('SOURCE',source)];cards='';status={}
        preview(data/'source/%03d.png',root/'source-derived.mp4')
        cards+=fig(f'{sequence}/source-derived.mp4','SOURCE · derived 16fps preview',True)
        for mode in ('BASE','ON','NULL'):
            output=private/'outputs'/sequence/mode
            frames=sorted((output/'frames').glob('*.png'))
            if len(frames)==33 and (output/'generated.mp4').is_file():
                copy(output/'generated.mp4',root/f'{mode}.mp4')
                receipt['original_mp4_sha256'][f'{sequence}/{mode}']=sha(root/f'{mode}.mp4')
                groups.append((mode+' GENERATED',frames));status[mode]='COMPLETE'
                cards+=fig(f'{sequence}/{mode}.mp4',mode+' · actual generated result · original MP4 bytes',True)
            else:
                status[mode]='NOT_AVAILABLE'
                cards+=f'<figure><p>{mode}: NOT_AVAILABLE</p><figcaption>No generated output presented.</figcaption></figure>'
        anchors=''
        for name in ('start','end'):
            copy(data/'anchors'/f'{name}.png',root/f'{name}.png')
            anchors+=fig(f'{sequence}/{name}.png',name.upper()+' anchor · model input')
        if sequence=='cross-id-dog':
            copy(data/'reference/full.png',root/'target-reference.png')
            anchors+=fig(f'{sequence}/target-reference.png','TARGET reference · existing input')
            if (private/'cross-cache/point-summary.json').exists():
                copy(private/'cross-cache/point-summary.json',root/'retarget-point-summary.json')
                anchors+='<p><a href="cross-id-dog/retarget-point-summary.json">Actual adapter point summary</a>: normalized target approximation, distinct from raw source tracker overlay; no joint/3D correspondence.</p>'
        diagnostics=[]
        track_path=(private/'cross-tracks'/'tracks.npz') if sequence=='cross-id-dog' else private/'tracks'/sequence/'tracks.npz'
        if track_path.exists():
            with np.load(track_path,allow_pickle=False) as tracks:
                points=tracks['tracks'];active=tracks['visible'] & tracks['valid']
                active[:,exclusions.get(sequence,{}).get('excluded_point_ids',[])]=False
            overlays=root/'point-overlay';overlays.mkdir()
            for t,path in enumerate(source):
                with Image.open(path) as image:
                    image=image.convert('RGB');draw=ImageDraw.Draw(image)
                    for k,(x,y) in enumerate(points[t]):
                        if active[t,k] and np.isfinite([x,y]).all() and 0<=x<416 and 0<=y<240:
                            draw.ellipse((x-2,y-2,x+2,y+2),fill='#8cceff');draw.text((x+3,y-7),str(k),fill='white')
                    image.save(overlays/f'{t:03d}.png')
            diagnostics.append(('SOURCE TRACK DIAGNOSTIC (not GT)',sorted(overlays.glob('*.png'))))
            preview(overlays/'%03d.png',root/'points-derived.mp4')
        conditions=sorted((private/'outputs'/sequence/'BASE'/'condition').glob('*.png'))
        if len(conditions)==33:
            diagnostics.append(('ACTUAL VACE RGB INPUT',conditions))
            preview(private/'outputs'/sequence/'BASE'/'condition/%03d.png',root/'condition-derived.mp4')
        slider=''
        for label,paths in groups+diagnostics:
            slug=label.lower().split(' ')[0];urls=[]
            for index,path in enumerate(paths):
                target=root/slug/f'{index:03d}.jpg';target.parent.mkdir(exist_ok=True)
                with Image.open(path) as image:image.convert('RGB').save(target,quality=92,subsampling=0)
                urls.append(f'{sequence}/{slug}/{index:03d}.jpg')
            slider+=f'<figure><div class="frame"><a href="{urls[0]}"><img src="{urls[0]}" data-frames="{html.escape(json.dumps(urls),quote=True)}" alt="{html.escape(label)}"></a></div><figcaption>{html.escape(label)} · JPEG review derivative</figcaption></figure>'
            all_sheet(label,paths,root/f'{slug}-all33.jpg')
        sheet(groups,list(range(0,33,4)),root/'fixed9.jpg')
        sheet(groups,[8,16,28,29,30,31,32],root/'critical.jpg')
        previews=''
        for name,label in [('points','Source tracker diagnostics; applied visible/valid/exclusions, not joint/contact GT or retargeted adapter coordinates'),('condition','Actual shared VACE RGB input; not generated result')]:
            if (root/f'{name}-derived.mp4').exists():previews+=fig(f'{sequence}/{name}-derived.mp4',label+' · derived preview',True)
        quality='NO_ESTABLISHED_GAIN; ON and NULL scene/appearance regression versus BASE' if sequence!='cross-id-dog' else 'NO_ESTABLISHED_GAIN; ON/NULL facial fragments and scene regression versus BASE'
        provenance='HEAD_ONLY: three nose/eye points; manual endpoint/bbox uncertainty; existing SAM mask' if sequence=='cross-id-dog' else 'MASK_GIVEN / DATASET_MASK_ASSISTED'
        sections.append(f'''<section><h2>{sequence}</h2><p>{provenance}. Quality: {quality}. BASE bypasses adapter; ON uses actual tracks; NULL uses endpoint-only trajectories. Same index, no alignment or warp.</p><div class="grid">{anchors}</div><button data-play>Play from selected frame · 16fps</button> <button data-pause>Pause all</button><p role="status"></p><div class="grid">{cards}</div><details><summary>Input diagnostics (not generated results)</summary><div class="grid">{previews}</div></details><h3>Same frame <output>0</output>/32</h3><label>Frame<input aria-label="{sequence} frame" type="range" min="0" max="32" value="0"></label><button data-zoom>Toggle 2× view (scroll each frame)</button><div class="grid">{slider}</div><details><summary>Fixed9 and critical frame sheets</summary>{fig(sequence+'/fixed9.jpg','Fixed9 SOURCE / BASE / ON / NULL')}{fig(sequence+'/critical.jpg','8,16,28,29–32 same-index comparison')}</details></section>''')
        receipt['cases'][sequence]={'outputs':status,'quality':quality,'provenance':provenance}
    intro='<h1>C-006 · Motion point adapter pilot</h1><p>Held-out test: horsejump-low and lucia. Training: bear, blackswan, bmx-bumps, boat, bus, camel, cows, dance-twirl. Validation: elephant and goat. Cross-ID dog is a separate optional transfer diagnostic, not a third held-out self-reconstruction test.</p><p>Matched SOURCE / BASE / ON / NULL review. Dataset-mask-assisted development pilot; tracked points are not semantic joints or contact ground truth. Retained points are not proven correct. Case-specific review status is shown below; operational execution and quality are separate.</p><p>33 frames, assumed preview16fps; file duration2.0625s versus endpoint interval2.0s. Original source FPS unknown. Temporal quality UNVERIFIED: browser playback checks and static sheets are not perceptual continuous review.</p><p>Generated MP4 bytes copied unchanged. JPEG sheets, source and diagnostic MP4s are new review derivatives. Raw tensors, training caches and checkpoint are excluded. Optional cross-ID case is shown only when its source data exists.</p>'
    (out/'index.html').write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>C006 motion point adapter</title><style>'+STYLE+'</style></head><body><main>'+intro+''.join(sections)+cost_panel(out)+'</main><script>'+JS+'</script></body></html>')
    receipt['build_seconds']=time.monotonic()-started
    (out/'review-summary.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('private',type=Path);parser.add_argument('out',type=Path)
    args=parser.parse_args();build(args.private.resolve(),args.out.resolve())
