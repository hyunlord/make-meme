"""Build offline C004 comparison. JPEGs are review derivatives; MP4 copies are byte-exact."""
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

def build(c001: Path, c002: Path, c004: Path, out: Path) -> None:
    """Reuse actual PNG/MP4 evidence without changing generated frames or time indices."""
    out.mkdir(parents=True,exist_ok=False)
    root=out/CASE;root.mkdir();src=c001/'inputs'/CASE
    cropmeta=json.loads((c001/'review-final'/CASE/'evaluation-crop.json').read_text())
    crop=cropmeta['bbox_xyxy'];(root/'evaluation-crop.json').write_text(json.dumps(cropmeta,indent=2))
    groups=[('SOURCE',sorted((src/'source').glob('*.png')))]
    videos=[('source',src/'source.mp4','SOURCE · original preview bytes')]
    outline=c002/'video'/CASE/'layout_mov'
    groups.append(('BASE_END RESULT',sorted((outline/'frames').glob('*.png'))))
    videos.append(('base-end',outline/'generated.mp4','BASE_END · generated result · C002 original bytes'))
    cards='';records={}
    for mode in ('corrected_end',):
        clip=c004/'video'/mode
        assert (clip/'generated.mp4').is_file(), f'Actual output required: {mode}'
        videos.append((mode,clip/'generated.mp4',mode.upper()+' · generated result · original bytes'))
        frames=sorted((clip/'frames').glob('*.png'));assert len(frames)==33
        groups.append((mode.upper()+' RESULT',frames));records[mode]='COMPLETE'
        for filename in ('result.json','condition.json','latent.json','first-model-input.json'):
            copy(clip/filename,root/mode/filename)
    for name,path,label in videos:
        copy(path,root/f'{name}.mp4');cards+=fig(f'{CASE}/{name}.mp4',label,True)
    anchors=''
    for name,path in [('target-reference',src/'reference/full.png'),('target-reference-crop',src/'reference/crop.png'),('start-anchor',c001/'anchors'/CASE/'start.png'),('old-end-anchor',c001/'anchors'/CASE/'end.png'),('corrected-end-anchor',c004/'anchors/end.png')]:
        copy(path,root/f'{name}.png');anchors+=fig(f'{CASE}/{name}.png',name.upper()+' · anchor/reference input')
    condition_cards=''
    for mode in ('corrected_end',):
        clip=c004/'video'/mode
        conditions=sorted((clip/'condition').glob('*.png'));assert len(conditions)==33
        preview(clip/'condition/%03d.png',root/f'{mode}-condition.mp4')
        condition_cards+=fig(f'{CASE}/{mode}-condition.mp4',mode.upper()+' X_t · MODEL INPUT · derived preview',True)
        groups.append((mode.upper()+' INPUT',conditions))
    slider=''
    for label,paths in groups:
        assert len(paths)==33
        slug=label.lower().replace(' ','-')
        for kind,box in [('full',None),('subject',crop),('head',[180,100,500,430]),('legs',[180,210,480,470])]:
            urls=[]
            for i,path in enumerate(paths):
                target=root/f'{slug}-{kind}'/f'{i:03d}.jpg';jpg(path,target,box);urls.append(f'{CASE}/{slug}-{kind}/{i:03d}.jpg')
            hidden='' if kind=='full' else ' hidden'
            slider+=f'<figure data-crop="{kind}"{hidden}><a href="{urls[0]}"><img src="{urls[0]}" data-frames="{html.escape(json.dumps(urls),quote=True)}" alt="{label} {kind}"></a><figcaption>{label} · {kind} · JPEG review derivative</figcaption></figure>'
    for label,paths in groups[:3]:
        canvas=Image.new('RGB',(416*6,270*6),'#1b222a');draw=ImageDraw.Draw(canvas)
        for i,path in enumerate(paths):
            with Image.open(path) as im:canvas.paste(im.convert('RGB').resize((416,240)),((i%6)*416,(i//6)*270+25))
            draw.text(((i%6)*416+5,(i//6)*270+3),f'{label} {i}',fill='white')
        canvas.save(root/(label.lower().replace(' ','-')+'-all33.jpg'),quality=92)
    sheet(groups,root,'fixed-sheet.jpg');sheet(groups[:3],root,'fixed-head-sheet.jpg',[180,100,500,430]);sheet(groups[:3],root,'fixed-legs-sheet.jpg',[180,210,480,470])
    global INDICES
    INDICES=[8,16,28,29,30,31,32];sheet(groups[:3],root,'critical-sheet.jpg');INDICES=list(range(0,33,4))
    compare=[root/f'{x}.mp4' for x in ('source','base-end','corrected_end')]
    cmd=['ffmpeg','-v','error','-n']
    for path in compare:cmd+=['-i',str(path)]
    cmd+=['-filter_complex','hstack=inputs=3','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(root/'comparison-derived.mp4')]
    subprocess.run(cmd,check=True)
    reports=''.join(f'<a href="reports/{name}">{name}</a> ' for name in ('RESULTS.md','METHOD.md','LESSON_KO.md','REPRODUCE.md','COSTS.json'))
    body=f'''<h1>C-004 · End anchor consistency</h1><p>Core comparison: C002 BASE_END and C004 CORRECTED_END. The start anchor, intermediate dynamic outlines, generation mask and model settings are fixed. Only the end-anchor RGB input is replaced. No C003 internal scribble condition is used.</p><p>Source FPS unknown. Preview16fps is assumed: file duration2.0625s; endpoint sample interval2.0s. Temporal quality: UNVERIFIED. Browser playback and static sheets do not establish perceptual temporal quality.</p><p>Compare intermediate progression1–28, ending approach29–31, and actual output32 separately. The corrected anchor can also change fur, face, lighting and background; this tests the whole anchor replacement, not a pure pose intervention. Visible screen-left/right paws are not anatomical labels; joint/contact accuracy remains uncertain. Same fixed crop/index throughout, no tracking, warp or time alignment.</p><p>{reports}</p><div class="grid">{anchors}</div><section><h2>Generated results and source</h2><button data-play>Play all from frame0 · 16fps</button><button data-pause>Pause all</button><p role="status"></p><div class="grid">{cards}</div><details><summary>Derived side-by-side comparison MP4</summary>{fig(CASE+'/comparison-derived.mp4','New derived comparison encode · original generated MP4s retained separately',True)}</details><h2>Actual CORRECTED_END model input</h2><div class="grid">{condition_cards}</div><h2>Same-index review · <output>0</output>/32</h2><label>Frame index<input type="range" min="0" max="32" value="0" aria-label="Frame index"></label><label>View <select aria-label="Crop view"><option value="full">Full frame</option><option value="subject">Frozen C001 subject crop</option><option value="head">Fixed head region</option><option value="legs">Fixed leg region</option></select></label><p>JPEGs and enlarged crops are review derivatives. Crops use the same fixed screen coordinates for every method/frame; they are not tracked or aligned.</p><div class="grid">{slider}</div><details><summary>Fixed0/4/8/12/16/20/24/28/32 and critical8/16/28/29–32 sheets</summary>{fig(CASE+'/fixed-sheet.jpg','Fixed full-frame comparison')}{fig(CASE+'/fixed-head-sheet.jpg','Fixed head region')}{fig(CASE+'/fixed-legs-sheet.jpg','Fixed leg region')}{fig(CASE+'/critical-sheet.jpg','Critical indices including all29–32')}</details></section>'''
    script=JS.replace("x.src=JSON.parse(x.dataset.frames)[i]", "{x.src=JSON.parse(x.dataset.frames)[i];x.parentElement.href=x.src;}")
    (out/'index.html').write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>C004 end anchor consistency</title><style>'+STYLE+'</style></head><body><main>'+body+'</main><script>'+script+'</script></body></html>')
    (out/'review-summary.json').write_text(json.dumps({'case':CASE,'outputs':records,'temporal':'UNVERIFIED','fixed_crop':crop,'head_crop':[180,100,500,430],'legs_crop':[180,210,480,470],'derived_comparison_mp4':True},indent=2))
    print(json.dumps({'files':sum(p.is_file() for p in out.rglob('*')),'outputs':records}))



if __name__=='__main__':build(*(Path(x).resolve() for x in sys.argv[1:5]))
