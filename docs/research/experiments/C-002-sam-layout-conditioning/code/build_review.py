"""Build offline C002 comparison. JPEGs are review derivatives; MP4 copies are byte-exact."""
from pathlib import Path
import hashlib
import html
import json
import shutil
import subprocess
import sys
from PIL import Image, ImageDraw

CASES=('case_rigid','case_nonrigid')
INDICES=list(range(0,33,4))
STYLE='body{background:#101418;color:#edf1f5;font:16px/1.6 system-ui;margin:0}main{max-width:1600px;margin:auto;padding:24px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}figure{margin:0;padding:12px;background:#1b222a}img,video{width:100%;display:block}input{width:100%}button{padding:10px;margin:12px 0}a{color:#91caff}summary{cursor:pointer}h2{margin-top:40px}@media(max-width:650px){main{padding:12px}}'
JS="""document.querySelectorAll('section').forEach(s=>{s.querySelector('input').oninput=e=>{const i=+e.target.value;s.querySelector('output').textContent=i;s.querySelectorAll('[data-frames]').forEach(x=>x.src=JSON.parse(x.dataset.frames)[i]);};s.querySelector('button').onclick=()=>s.querySelectorAll('video').forEach(v=>{v.currentTime=0;v.play().catch(()=>{});});});"""

def copy(a,b):
    b.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a,b)
    assert hashlib.sha256(a.read_bytes()).digest()==hashlib.sha256(b.read_bytes()).digest()

def jpg(a,b,crop=None):
    b.parent.mkdir(parents=True,exist_ok=True)
    with Image.open(a) as im:
        im=im.convert('RGB')
        if crop:im=im.crop(crop)
        im.save(b,quality=90,subsampling=0)

def fig(path,label,video=False):
    tag=f'<video controls muted playsinline preload="metadata" src="{path}"></video>' if video else f'<a href="{path}"><img loading="lazy" src="{path}" alt="{html.escape(label)}"></a>'
    return f'<figure>{tag}<figcaption>{html.escape(label)}</figcaption></figure>'

def sheet(groups,root,name,crop=None):
    canvas=Image.new('RGB',(416*len(INDICES),270*len(groups)),'#1b222a');d=ImageDraw.Draw(canvas)
    for row,(label,paths) in enumerate(groups):
        for col,i in enumerate(INDICES):
            with Image.open(paths[i]) as im:
                im=im.convert('RGB')
                if crop:im=im.crop(crop)
                im.thumbnail((416,240));canvas.paste(im,(col*416,row*270+25))
            d.text((col*416+5,row*270+3),f'{label} {i}/32',fill='white')
    canvas.save(root/name,quality=90)

def preview(paths,destination):
    subprocess.run(['ffmpeg','-v','error','-framerate','16','-i',str(paths),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(destination)],check=True)

def build(c001,c002,out):
    out.mkdir(parents=True,exist_ok=False);sections=[];summary={}
    for case in CASES:
        root=out/case;root.mkdir();src=c001/'inputs'/case
        cropmeta=json.loads((c001/'review-final'/case/'evaluation-crop.json').read_text());crop=cropmeta['bbox_xyxy']
        (root/'evaluation-crop.json').write_text(json.dumps(cropmeta,indent=2))
        groups=[('SOURCE',sorted((src/'source').glob('*.png'))),('ENDPOINT',sorted((c001/'video'/case/'frames').glob('*.png')))]
        cards='';records={}
        for name,path in [('source',src/'source.mp4'),('endpoint',c001/'video'/case/'generated.mp4')]:
            copy(path,root/f'{name}.mp4');cards+=fig(f'{case}/{name}.mp4',name.upper()+' · original MP4 bytes',True)
        for mode in ('layout_mov','layout_still'):
            clip=c002/'video'/case/mode
            if (clip/'generated.mp4').exists():
                copy(clip/'generated.mp4',root/f'{mode}.mp4');cards+=fig(f'{case}/{mode}.mp4',mode.upper()+' · original MP4 bytes',True)
                frames=sorted((clip/'frames').glob('*.png'));assert len(frames)==33
                groups.append((mode.upper(),frames));records[mode]='COMPLETE'
                for filename in ('result.json','condition.json','latent.json'):
                    if (clip/filename).exists():copy(clip/filename,root/mode/filename)
                conditions=sorted((clip/'condition').glob('*.png'));assert len(conditions)==33
                preview(clip/'condition/%03d.png',root/f'{mode}-condition.mp4')
                cards+=fig(f'{case}/{mode}-condition.mp4',mode.upper()+' actual X_t · derived condition preview',True)
                groups.append((mode.upper()+' CONDITION',conditions))
            else:records[mode]='NOT_AVAILABLE';cards+=f'<p>{mode}: NOT_AVAILABLE</p>'
        sam=c001/'analysis'/case/'source';preview(sam/'%03d-overlay.png',root/'sam-overlay.mp4')
        cards+=fig(f'{case}/sam-overlay.mp4','Selected source SAM overlay · analysis preview',True)
        copy(sam/'objects.json',root/'sam-objects.json')
        groups.append(('SOURCE SAM',sorted(sam.glob('*-overlay.png'))))
        for name,path in [('reference',src/'reference/full.png'),('reference-crop',src/'reference/crop.png'),('start-anchor',c001/'anchors'/case/'start.png'),('end-anchor',c001/'anchors'/case/'end.png')]:
            copy(path,root/f'{name}.png');cards+=fig(f'{case}/{name}.png',name)
        slider=''
        for label,paths in groups:
            assert len(paths)==33
            folder=label.lower().replace(' ','-');links=[];zooms=[]
            for i,path in enumerate(paths):
                target=root/folder/f'{i:03d}.jpg';jpg(path,target);links.append(f'{case}/{folder}/{i:03d}.jpg')
                target=root/f'{folder}-crop'/f'{i:03d}.jpg';jpg(path,target,crop);zooms.append(f'{case}/{folder}-crop/{i:03d}.jpg')
            for title,urls in [(label,links),(label+' FIXED CROP',zooms)]:
                slider+=f'<figure><img src="{urls[0]}" data-frames="{html.escape(json.dumps(urls),quote=True)}" alt="{title}"><figcaption>{title} · JPEG review derivative</figcaption></figure>'
        sheet(groups,root,'fixed-sheet.jpg');sheet(groups,root,'fixed-crop-sheet.jpg',crop)
        summary[case]=records
        sections.append(f'<section><h2>{case}</h2><button>Play all from frame 0</button><div class="grid">{cards}</div><h3>Same-index review · <output>0</output>/32</h3><label>Frame<input type="range" min="0" max="32" value="0" aria-label="{case} frame"></label><div class="grid">{slider}</div><details><summary>Fixed indices 0/4/8/12/16/20/24/28/32</summary>{fig(case+"/fixed-sheet.jpg","Fixed full-frame comparison")}{fig(case+"/fixed-crop-sheet.jpg","Same C001 crop · no warp")}</details></section>')
    (out/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>C002 SAM layout comparison</title><style>'+STYLE+'</style><main><h1>C-002 · SAM layout conditioning</h1><p>C001 ENDPOINT reused. MOV uses each source SAM contour; STILL repeats L0 in the middle. Anchors remain at 0/32. Source FPS unknown; all previews use assumed 16 fps. SAM contours condition C002 generation; overlays are analysis only. Temporal quality: UNVERIFIED.</p><p>Slider/crop JPEGs and contact sheets are lossy review derivatives. Full PNGs remain in full evidence. Generated and source MP4s are unchanged. Same frozen crop and frame index; no optical alignment or time warp.</p>'+''.join(sections)+'</main><script>'+JS+'</script></html>')
    (out/'review-summary.json').write_text(json.dumps(summary,indent=2))
    payload={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file()}
    (out/'payload-hashes.json').write_text(json.dumps(payload,indent=2))
    print(json.dumps({'files':len(payload),'bytes':sum(p.stat().st_size for p in out.rglob('*') if p.is_file()),'cases':summary}))

if __name__=='__main__':build(*(Path(x).resolve() for x in sys.argv[1:4]))
