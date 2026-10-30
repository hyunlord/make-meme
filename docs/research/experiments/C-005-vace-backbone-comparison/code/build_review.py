"""Build offline C005 comparison. JPEGs are review derivatives; MP4 copies are byte-exact."""
from pathlib import Path
import hashlib
import html
import json
import shutil
import subprocess
import sys
from PIL import Image, ImageDraw

CASE='case_nonrigid'
INDICES=list(range(0,33,4))
STYLE='body{background:#101418;color:#edf1f5;font:16px/1.6 system-ui;margin:0}main{max-width:1600px;margin:auto;padding:24px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}figure{margin:0;padding:12px;background:#1b222a}img,video{width:100%;display:block;height:auto}figure[hidden]{display:none}button,select{font:inherit}button:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #91caff}p{max-width:95ch}figcaption{overflow-wrap:anywhere}input{width:100%}button{padding:10px;margin:12px 0}a{color:#91caff}summary{cursor:pointer}h2{margin-top:40px}@media(max-width:650px){main{padding:12px}}'
JS="""document.querySelectorAll('section').forEach(s=>{s.querySelector('input').oninput=e=>{const i=+e.target.value;s.querySelector('output').textContent=i;s.querySelectorAll('[data-frames]').forEach(x=>x.src=JSON.parse(x.dataset.frames)[i]);};s.querySelector('[data-play]').onclick=()=>s.querySelectorAll('video').forEach(v=>{v.currentTime=0;v.play().catch(e=>{s.querySelector('[role=status]').textContent=e.message;});});s.querySelector('[data-pause]').onclick=()=>s.querySelectorAll('video').forEach(v=>v.pause());s.querySelector('select').onchange=e=>s.querySelectorAll('[data-crop]').forEach(x=>x.hidden=x.dataset.crop!==e.target.value);});"""

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

def build(c001: Path, c002: Path, c005: Path, out: Path, blocked: bool = False) -> None:
    """Compare two cases using existing anchors and original generated MP4 bytes."""
    out.mkdir(parents=True,exist_ok=False);sections=[];records={}
    for case in ('case_rigid','case_nonrigid'):
        root=out/case;root.mkdir();src=c001/'inputs'/case
        base=c002/'video'/case/'layout_mov';large=c005/'video'/case
        if not blocked:assert (large/'generated.mp4').is_file(),f'Actual14B output required: {case}'
        cropmeta=json.loads((c001/'review-final'/case/'evaluation-crop.json').read_text());crop=cropmeta['bbox_xyxy']
        (root/'evaluation-crop.json').write_text(json.dumps(cropmeta,indent=2))
        groups=[('SOURCE',sorted((src/'source').glob('*.png'))),('VACE_1.3B RESULT',sorted((base/'frames').glob('*.png')))]
        if not blocked:groups.append(('VACE_14B RESULT',sorted((large/'frames').glob('*.png'))))
        cards='<p><strong>14B: NO GENERATED OUTPUT.</strong> Vehicle loading stopped at SYSTEM_PSI_FULL_PRESSURE before forward; dog was not started. Cause attribution UNKNOWN. No retry or quality conclusion.</p>' if blocked else ''
        for name,path,label in [('source',src/'source.mp4','SOURCE'),('vace-1.3b',base/'generated.mp4','VACE1.3B · C002 generated result'),('vace-14b',large/'generated.mp4','VACE14B · C005 generated result')]:
            if blocked and name=='vace-14b':continue
            copy(path,root/f'{name}.mp4');cards+=fig(f'{case}/{name}.mp4',label+' · original MP4 bytes',True)
        anchors=''
        for name,path in [('target-reference',src/'reference/full.png'),('target-reference-crop',src/'reference/crop.png'),('start-anchor',c001/'anchors'/case/'start.png'),('end-anchor',c001/'anchors'/case/'end.png')]:
            copy(path,root/f'{name}.png');anchors+=fig(f'{case}/{name}.png',name.upper()+' · original C001 input')
        condition_root=base if blocked else large
        conditions=sorted((condition_root/'condition').glob('*.png'));assert len(conditions)==33
        preview(condition_root/'condition/%03d.png',root/'condition-preview.mp4');groups.append(('ACTUAL MODEL INPUT',conditions))
        slider='';boxes=[('full',None),('subject',crop)]
        boxes += [('head',[180,100,500,430]),('legs',[180,210,480,470])] if case=='case_nonrigid' else [('wheels',[160,240,680,430]),('scene',[0,0,832,480])]
        for label,paths in groups:
            assert len(paths)==33
            slug=label.lower().replace(' ','-')
            for kind,box in boxes:
                urls=[]
                for i,path in enumerate(paths):
                    target=root/f'{slug}-{kind}'/f'{i:03d}.jpg';jpg(path,target,box);urls.append(f'{case}/{slug}-{kind}/{i:03d}.jpg')
                hidden='' if kind=='full' else ' hidden'
                slider+=f'<figure data-crop="{kind}"{hidden}><a href="{urls[0]}"><img src="{urls[0]}" data-frames="{html.escape(json.dumps(urls),quote=True)}" alt="{label} {kind}"></a><figcaption>{label} · {kind} · JPEG review derivative</figcaption></figure>'
        for label,paths in groups[:3]:
            canvas=Image.new('RGB',(2496,1620),'#1b222a');draw=ImageDraw.Draw(canvas)
            for i,path in enumerate(paths):
                with Image.open(path) as im:canvas.paste(im.convert('RGB').resize((416,240)),((i%6)*416,(i//6)*270+25))
                draw.text(((i%6)*416+5,(i//6)*270+3),f'{label} {i}',fill='white')
            canvas.save(root/(label.lower().replace(' ','-')+'-all33.jpg'),quality=92)
        sheet(groups,root,'fixed-sheet.jpg');sheet(groups[:3],root,'fixed-subject-sheet.jpg',crop)
        global INDICES
        INDICES=[8,16,28,29,30,31,32];sheet(groups[:3],root,'critical-sheet.jpg');INDICES=list(range(0,33,4))
        if case=='case_nonrigid':
            sheet(groups[:3],root,'fixed-head-sheet.jpg',[180,100,500,430]);sheet(groups[:3],root,'fixed-legs-sheet.jpg',[180,210,480,470])
        cmd=['ffmpeg','-v','error','-n']
        for name in (('source','vace-1.3b') if blocked else ('source','vace-1.3b','vace-14b')):cmd+=['-i',str(root/f'{name}.mp4')]
        cmd+=['-filter_complex',('hstack=inputs=2' if blocked else 'hstack=inputs=3'),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(root/'comparison-derived.mp4')];subprocess.run(cmd,check=True)
        if not blocked:
            for name in ('result.json','condition.json','latent.json','first-model-input.json'):copy(large/name,root/'evidence'/name)
        options=''.join(f'<option value="{kind}">{kind}</option>' for kind,_ in boxes)
        sections.append(f'''<section><h2>{case}</h2><div class="grid">{anchors}</div><h3>Source and actual generated results</h3><button data-play>Play all from frame0 · 16fps</button><button data-pause>Pause all</button><p role="status"></p><div class="grid">{cards}</div><details><summary>Common dynamic layout / actual model input and derived comparison</summary>{fig(case+'/condition-preview.mp4','Actual RGB model input · derived preview; no C003 scribble or C004 anchor',True)}{fig(case+'/comparison-derived.mp4','Derived side-by-side encode · original MP4s retained separately',True)}</details><h3>Same index · <output>0</output>/32</h3><label>Frame<input type="range" min="0" max="32" value="0" aria-label="{case} frame"></label><label>Fixed view <select aria-label="{case} crop">{options}</select></label><p>Full33 indices. Identical fixed crop for every output/frame; no time alignment or spatial warp.</p><div class="grid">{slider}</div><details><summary>Fixed9 / subject / critical8,16,28,29–32 sheets</summary>{fig(case+'/fixed-sheet.jpg','Fixed9 full frame')}{fig(case+'/fixed-subject-sheet.jpg','Fixed9 subject')}{fig(case+'/critical-sheet.jpg','Critical same-index comparison')}</details></section>''')
        records[case]={'vace_1.3b':'REUSED_C002','vace_14b':('NO_OUTPUT_SAFETY_STOP' if case=='case_rigid' else 'NOT_RUN') if blocked else 'COMPLETE'}
    reports=' '.join(f'<a href="reports/{name}">{name}</a>' for name in ('RESULTS.md','BACKEND_COMPARISON.md','LESSON_KO.md','COSTS.json','REPRODUCE.md'))
    intro=f'''<h1>C-005 · VACE backbone comparison</h1><p>Same original C001 anchors and C002 dynamic SAM layouts; existing1.3B results compared with new14B results. Two public checkpoints, two development cases, one seed. This is not a pure parameter-count causal experiment or a general ranking.</p><p>Source FPS unknown; assumed preview16fps. File duration2.0625s and endpoint sample interval2.0s differ. Temporal quality: UNVERIFIED. Browser playback/file decoding and static sheets do not establish perceptual temporal quality.</p><p>Compare appearance, coarse motion, internal events and protected scene separately. The original dog end-anchor/source pose conflict remains. No C004 corrected anchor or C003 internal lines. New JPEG sheets/crops and comparison/condition MP4s are review derivatives; generated MP4s retain original bytes.</p><p>{reports}</p>'''
    if blocked:intro='<h1>C-005 · Operational safety stop</h1><p><strong>No14B generated video or quality comparison.</strong> First vehicle model loading stopped at SYSTEM_PSI_FULL_PRESSURE before any forward; dog NOT_RUN. Cause attribution UNKNOWN. No automatic retry or guard relaxation. Existing1.3B/source/anchors and C002 model-input previews below are historical evidence, not14B outputs.</p>'+intro.replace('Same original C001 anchors and C002 dynamic SAM layouts; existing1.3B results compared with new14B results.', 'Original C001 anchors and C002 dynamic SAM layouts are preserved. Only existing1.3B results are available.')
    script=JS.replace('x.src=JSON.parse(x.dataset.frames)[i]','{x.src=JSON.parse(x.dataset.frames)[i];x.parentElement.href=x.src;}')
    (out/'index.html').write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>C005 VACE backbone comparison</title><style>'+STYLE+'</style></head><body><main>'+intro+''.join(sections)+'</main><script>'+script+'</script></body></html>')
    (out/'review-summary.json').write_text(json.dumps({'outputs':records,'temporal':'UNVERIFIED','derived_comparison_mp4':True},indent=2));print(json.dumps({'files':sum(p.is_file() for p in out.rglob('*')),'outputs':records}))

if __name__=='__main__':build(*(Path(x).resolve() for x in sys.argv[1:5]),blocked='--blocked' in sys.argv[5:])
