"""Build offline C003 comparison. JPEGs are review derivatives; MP4 copies are byte-exact."""
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

def build(c001: Path, c002: Path, c003: Path, out: Path) -> None:
    """Reuse actual PNG/MP4 evidence without changing generated frames or time indices."""
    out.mkdir(parents=True,exist_ok=False)
    root=out/CASE;root.mkdir();src=c001/'inputs'/CASE
    cropmeta=json.loads((c001/'review-final'/CASE/'evaluation-crop.json').read_text())
    crop=cropmeta['bbox_xyxy'];(root/'evaluation-crop.json').write_text(json.dumps(cropmeta,indent=2))
    groups=[('SOURCE',sorted((src/'source').glob('*.png')))]
    videos=[('source',src/'source.mp4','SOURCE · original preview bytes')]
    outline=c002/'video'/CASE/'layout_mov'
    groups.append(('OUTLINE_ONLY RESULT',sorted((outline/'frames').glob('*.png'))))
    videos.append(('outline-only',outline/'generated.mp4','OUTLINE_ONLY · generated result · C002 original bytes'))
    cards='';records={}
    for mode in ('internal_dynamic','internal_hold'):
        clip=c003/'video'/mode
        assert (clip/'generated.mp4').is_file(), f'Actual output required: {mode}'
        videos.append((mode,clip/'generated.mp4',mode.upper()+' · generated result · original bytes'))
        frames=sorted((clip/'frames').glob('*.png'));assert len(frames)==33
        groups.append((mode.upper()+' RESULT',frames));records[mode]='COMPLETE'
        for filename in ('result.json','condition.json','latent.json','first-model-input.json'):
            copy(clip/filename,root/mode/filename)
    for name,path,label in videos:
        copy(path,root/f'{name}.mp4');cards+=fig(f'{CASE}/{name}.mp4',label,True)
    anchors=''
    for name,path in [('target-reference',src/'reference/full.png'),('target-reference-crop',src/'reference/crop.png'),('start-anchor',c001/'anchors'/CASE/'start.png'),('end-anchor',c001/'anchors'/CASE/'end.png')]:
        copy(path,root/f'{name}.png');anchors+=fig(f'{CASE}/{name}.png',name.upper()+' · reused C001 input')
    condition_cards=''
    for mode in ('internal_dynamic','internal_hold'):
        clip=c003/'video'/mode
        conditions=sorted((clip/'condition').glob('*.png'));assert len(conditions)==33
        preview(clip/'condition/%03d.png',root/f'{mode}-condition.mp4')
        condition_cards+=fig(f'{CASE}/{mode}-condition.mp4',mode.upper()+' X_t · MODEL INPUT · derived preview',True)
        groups.append((mode.upper()+' INPUT',conditions))
    extra=json.loads((c003/'review-paths.json').read_text())
    for label,folder,pattern in extra['groups']:
        paths=sorted(Path(folder).glob(pattern));assert len(paths)==33,(label,len(paths))
        groups.append((label,paths))
        slug=label.lower().replace(' ','-')
        staging=root/f'{slug}-png';staging.mkdir()
        for i,path in enumerate(paths):copy(path,staging/f'{i:03d}.png')
        preview(staging/'%03d.png',root/f'{slug}.mp4')
        shutil.rmtree(staging)
        condition_cards+=fig(f'{CASE}/{slug}.mp4',label+' · structural/analysis preview · not generated output',True)
    sam=c001/'analysis'/CASE/'source'
    groups.append(('SOURCE SAM OVERLAY',sorted(sam.glob('*-overlay.png'))))
    preview(sam/'%03d-overlay.png',root/'sam-overlay.mp4')
    condition_cards+=fig(f'{CASE}/sam-overlay.mp4','SOURCE SAM OVERLAY · analysis only · not model input',True)
    slider=''
    for label,paths in groups:
        assert len(paths)==33
        slug=label.lower().replace(' ','-')
        for kind,box in [('full',None),('subject',crop),('head',[190,60,470,330]),('legs',[180,210,480,470])]:
            urls=[]
            for i,path in enumerate(paths):
                target=root/f'{slug}-{kind}'/f'{i:03d}.jpg';jpg(path,target,box);urls.append(f'{CASE}/{slug}-{kind}/{i:03d}.jpg')
            hidden='' if kind=='full' else ' hidden'
            slider+=f'<figure data-crop="{kind}"{hidden}><a href="{urls[0]}"><img src="{urls[0]}" data-frames="{html.escape(json.dumps(urls),quote=True)}" alt="{label} {kind}"></a><figcaption>{label} · {kind} · JPEG review derivative</figcaption></figure>'
    for label,paths in groups[:4]:
        canvas=Image.new('RGB',(416*6,270*6),'#1b222a');draw=ImageDraw.Draw(canvas)
        for i,path in enumerate(paths):
            with Image.open(path) as im:canvas.paste(im.convert('RGB').resize((416,240)),((i%6)*416,(i//6)*270+25))
            draw.text(((i%6)*416+5,(i//6)*270+3),f'{label} {i}',fill='white')
        canvas.save(root/(label.lower().replace(' ','-')+'-all33.jpg'),quality=92)
    sheet(groups,root,'fixed-sheet.jpg');sheet(groups[:4],root,'fixed-head-sheet.jpg',[190,60,470,330]);sheet(groups[:4],root,'fixed-legs-sheet.jpg',[180,210,480,470])
    global INDICES
    INDICES=[8,16,28,29,30,31,32];sheet(groups[:4],root,'critical-sheet.jpg');INDICES=list(range(0,33,4))
    compare=[root/f'{x}.mp4' for x in ('source','outline-only','internal_dynamic','internal_hold')]
    cmd=['ffmpeg','-v','error','-n']
    for path in compare:cmd+=['-i',str(path)]
    cmd+=['-filter_complex','hstack=inputs=4','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(root/'comparison-derived.mp4')]
    subprocess.run(cmd,check=True)
    reports=''.join(f'<a href="reports/{name}">{name}</a> ' for name in ('RESULTS.md','METHOD.md','LESSON_KO.md','REPRODUCE.md','COSTS.json'))
    body=f'''<h1>C-003 · Internal structure comparison</h1><p>Core comparison: C002 OUTLINE_ONLY, INTERNAL_DYNAMIC, INTERNAL_HOLD. Same source index, anchors, dynamic outline and generation mask. DYNAMIC changes internal structure over time; HOLD transports the initial normalized structure with the current bbox and clips it to the current interior. It is not motion-off.</p><p>Source FPS unknown. Preview16fps is assumed: file duration2.0625s; endpoint sample interval2.0s. Temporal quality: UNVERIFIED. Browser playback and static sheets do not establish perceptual temporal quality.</p><p>Source-derived lines include shape, fur and texture, not joint ground truth. Thin parts removed by the fixed4px interior band may be NOT_REPRESENTED. Frames29–32 conflict with the crouched end anchor. Same crop/index throughout, no warp or time alignment. Visible screen-left/right paws are not anatomical labels; contact remains uncertain.</p><p>{reports}</p><div class="grid">{anchors}</div><section><h2>Generated results and source</h2><button data-play>Play all from frame0 · 16fps</button><button data-pause>Pause all</button><p role="status"></p><div class="grid">{cards}</div><details><summary>Derived side-by-side comparison MP4</summary>{fig(CASE+'/comparison-derived.mp4','New derived comparison encode · original generated MP4s retained separately',True)}</details><h2>Actual model inputs and structural evidence</h2><div class="grid">{condition_cards}</div><h2>Same-index review · <output>0</output>/32</h2><label>Frame index<input type="range" min="0" max="32" value="0" aria-label="Frame index"></label><label>View <select aria-label="Crop view"><option value="full">Full frame</option><option value="subject">Frozen C001 subject crop</option><option value="head">Fixed head region</option><option value="legs">Fixed leg region</option></select></label><p>JPEGs and enlarged crops are review derivatives. Crops use the same fixed screen coordinates for every method/frame; they are not tracked or aligned.</p><div class="grid">{slider}</div><details><summary>Fixed0/4/8/12/16/20/24/28/32 and critical8/16/28/29–32 sheets</summary>{fig(CASE+'/fixed-sheet.jpg','Fixed full-frame comparison')}{fig(CASE+'/fixed-head-sheet.jpg','Fixed head region')}{fig(CASE+'/fixed-legs-sheet.jpg','Fixed leg region')}{fig(CASE+'/critical-sheet.jpg','Critical indices including all29–32')}</details></section>'''
    script=JS.replace("x.src=JSON.parse(x.dataset.frames)[i]", "{x.src=JSON.parse(x.dataset.frames)[i];x.parentElement.href=x.src;}")
    (out/'index.html').write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>C003 internal structure comparison</title><style>'+STYLE+'</style></head><body><main>'+body+'</main><script>'+script+'</script></body></html>')
    (out/'review-summary.json').write_text(json.dumps({'case':CASE,'outputs':records,'temporal':'UNVERIFIED','fixed_crop':crop,'head_crop':[190,60,470,330],'legs_crop':[180,210,480,470],'derived_comparison_mp4':True},indent=2))
    print(json.dumps({'files':sum(p.is_file() for p in out.rglob('*')),'outputs':records}))



def build_blocked(c001: Path, c002: Path, c003: Path, out: Path) -> None:
    """Show only existing evidence after a safety stop, with no substitute C003 output."""
    out.mkdir(parents=True,exist_ok=False);root=out/CASE;root.mkdir()
    src=c001/'inputs'/CASE;outline=c002/'video'/CASE/'layout_mov';sam=c001/'analysis'/CASE/'source'
    groups=[('SOURCE',sorted((src/'source').glob('*.png'))),('C002 OUTLINE_ONLY RESULT',sorted((outline/'frames').glob('*.png'))),('SOURCE SAM OVERLAY',sorted(sam.glob('*-overlay.png'))),('C002 OUTLINE MODEL INPUT',sorted((outline/'condition').glob('*.png')))]
    cards=''
    for name,path,label in [('source',src/'source.mp4','SOURCE · unchanged preview bytes'),('outline-only',outline/'generated.mp4','C002 OUTLINE_ONLY · existing generated result · unchanged bytes')]:
        copy(path,root/f'{name}.mp4');cards+=fig(f'{CASE}/{name}.mp4',label,True)
    anchors=''
    for name,path in [('target-reference',src/'reference/full.png'),('target-reference-crop',src/'reference/crop.png'),('start-anchor',c001/'anchors'/CASE/'start.png'),('end-anchor',c001/'anchors'/CASE/'end.png')]:
        copy(path,root/f'{name}.png');anchors+=fig(f'{CASE}/{name}.png',name.upper()+' · existing C001 input')
    preview(sam/'%03d-overlay.png',root/'sam-overlay.mp4');preview(outline/'condition/%03d.png',root/'outline-condition.mp4')
    cards+=fig(CASE+'/sam-overlay.mp4','Existing source SAM overlay · analysis only',True)+fig(CASE+'/outline-condition.mp4','C002 actual model input · derived preview, not C003 output',True)
    crop=json.loads((c001/'review-final'/CASE/'evaluation-crop.json').read_text())['bbox_xyxy'];slider=''
    for label,paths in groups:
        assert len(paths)==33
        slug=label.lower().replace(' ','-')
        for kind,box in [('full',None),('subject',crop),('head',[190,60,470,330]),('legs',[180,210,480,470])]:
            urls=[]
            for i,path in enumerate(paths):
                target=root/f'{slug}-{kind}'/f'{i:03d}.jpg';jpg(path,target,box);urls.append(f'{CASE}/{slug}-{kind}/{i:03d}.jpg')
            hidden='' if kind=='full' else ' hidden'
            slider+=f'<figure data-crop="{kind}"{hidden}><a href="{urls[0]}"><img src="{urls[0]}" data-frames="{html.escape(json.dumps(urls),quote=True)}" alt="{label} {kind}"></a><figcaption>{label} · {kind} · JPEG review derivative</figcaption></figure>'
    sheet(groups,root,'fixed-sheet.jpg');sheet(groups[:2],root,'fixed-head-sheet.jpg',[190,60,470,330]);sheet(groups[:2],root,'fixed-legs-sheet.jpg',[180,210,480,470])
    for path in (c003/'review-preflight').glob('*.jpg'):copy(path,out/'preflight'/path.name)
    reports=''.join(f'<a href="reports/{name}">{name}</a> ' for name in ('RESULTS.md','METHOD.md','LESSON_KO.md','REPRODUCE.md','COSTS.json'))
    body=f'''<h1>C-003 · Safety stop / comparison NOT_RUN</h1><p><strong>INTERNAL_DYNAMIC: NOT_RUN. INTERNAL_HOLD: NOT_RUN.</strong> Existing guard stopped at START_SWAPOUT_OBSERVED before the corrected CPU worker. Scribble extraction0, C003 conditions0, new videos0. No automatic retry or safety relaxation. This package contains reused source/anchors/C002 baseline and preparation evidence only. It does not establish C003 quality or internal-motion gain.</p><p>No J scribble or I interior images exist from execution. Missing conditions/results are not replaced with baseline images. Read the reports for the exact failed checks and attempt accounting. Temporal quality remains UNVERIFIED.</p><p>{reports}</p><p>Source FPS unknown. Assumed preview16fps; file2.0625s versus endpoint sample interval2.0s. Frames29–32 have an end-anchor/source pose conflict. Screen-left/right paw observations are not anatomical or contact ground truth.</p><div class="grid">{anchors}</div><section><h2>Existing evidence only</h2><button data-play>Play existing videos from frame0</button><button data-pause>Pause all</button><p role="status"></p><div class="grid">{cards}</div><h2>Same-index review · <output>0</output>/32</h2><label>Frame index<input type="range" min="0" max="32" value="0" aria-label="Frame index"></label><label>View <select aria-label="Crop view"><option value="full">Full frame</option><option value="subject">Frozen C001 subject crop</option><option value="head">Fixed head region</option><option value="legs">Fixed leg region</option></select></label><p>JPEG/crop/sheet images and condition/SAM MP4s are review derivatives. Source and C002 generated MP4s retain their original bytes. All33 indices accessible; no time shift or spatial warp.</p><div class="grid">{slider}</div><details><summary>Fixed0/4/8/12/16/20/24/28/32 sheets</summary>{fig(CASE+'/fixed-sheet.jpg','Existing evidence full frames')}{fig(CASE+'/fixed-head-sheet.jpg','Fixed head region')}{fig(CASE+'/fixed-legs-sheet.jpg','Fixed leg region')}{fig('preflight/source-all33.jpg','SOURCE all33')}{fig('preflight/outline_only-all33.jpg','Existing C002 OUTLINE_ONLY all33')}</details></section>'''
    script=JS.replace("x.src=JSON.parse(x.dataset.frames)[i]", "{x.src=JSON.parse(x.dataset.frames)[i];x.parentElement.href=x.src;}")
    (out/'index.html').write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>C003 safety stop evidence</title><style>'+STYLE+'</style></head><body><main>'+body+'</main><script>'+script+'</script></body></html>')
    (out/'review-summary.json').write_text(json.dumps({'case':CASE,'status':'SAFETY_STOP','outputs':{'internal_dynamic':'NOT_RUN','internal_hold':'NOT_RUN'},'scribble_extraction_passes':0,'new_videos':0,'temporal':'UNVERIFIED','existing_baseline_reused':True},indent=2))
    print(json.dumps({'status':'SAFETY_STOP','files':sum(p.is_file() for p in out.rglob('*'))}))

if __name__=='__main__':
    paths=tuple(Path(x).resolve() for x in sys.argv[1:5])
    if '--blocked' in sys.argv[5:]:build_blocked(*paths)
    else:build(*paths)
