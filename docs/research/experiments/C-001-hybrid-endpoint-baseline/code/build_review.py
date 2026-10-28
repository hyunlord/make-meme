# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
# Run: python build_review.py PRIVATE_ROOT REVIEW_OUTPUT [VIDEO_OUTPUT_ROOT]
"""Assemble an offline review from actual C-001 artifacts without altering outputs."""
from pathlib import Path
import hashlib
import html
import json
import shutil
import sys
import subprocess
from PIL import Image, ImageDraw

STYLE = '''body{margin:0;background:#101418;color:#edf1f5;font:16px/1.6 system-ui,sans-serif}main{max-width:1600px;margin:auto;padding:24px}h1{font-size:28px}h2{margin-top:40px}a{color:#91caff}p{max-width:1000px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}figure{margin:0;background:#1b222a;padding:12px}img,video{width:100%;height:auto;display:block}figcaption{font-size:14px}button,input{font:inherit}button{padding:8px 16px;margin:12px 8px 12px 0}input[type=range]{width:100%}.status{border-left:4px solid #efbd68;padding:12px;background:#1b222a}summary{cursor:pointer}table{border-collapse:collapse}td,th{border:1px solid #495561;padding:8px}@media(max-width:650px){.pair{grid-template-columns:1fr}main{padding:12px}}'''
JS = '''document.querySelectorAll('[data-case]').forEach(s=>{const slider=s.querySelector('input');const imgs=s.querySelectorAll('[data-frames]');slider.addEventListener('input',()=>{const i=Number(slider.value);s.querySelector('output').value=i;imgs.forEach(im=>{const fs=JSON.parse(im.dataset.frames);im.src=fs[i];});});s.querySelector('button').addEventListener('click',()=>{s.querySelectorAll('video').forEach(v=>{v.currentTime=0;v.playbackRate=1;v.play().catch(()=>{});});});});'''


def copy(source: Path, destination: Path) -> bool:
    if not source.is_file():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return True


def figure(path: str, label: str, video: bool = False) -> str:
    escaped = html.escape(path, quote=True)
    content = f'<video controls muted playsinline preload="metadata" src="{escaped}"></video>' if video else f'<a href="{escaped}"><img loading="lazy" src="{escaped}" alt="{html.escape(label)}"></a>'
    return f'<figure>{content}<figcaption>{html.escape(label)}</figcaption></figure>'


def contact_sheet(paths: list[Path], labels: list[str], output: Path, columns: int) -> None:
    cell=(416,270);rows=(len(paths)+columns-1)//columns
    sheet=Image.new('RGB',(columns*cell[0],rows*cell[1]),'#1b222a');draw=ImageDraw.Draw(sheet)
    for index,(path,label) in enumerate(zip(paths,labels,strict=True)):
        with Image.open(path) as original:
            image=original.convert('RGB');image.thumbnail((416,240))
        x,y=(index%columns)*416,(index//columns)*270
        sheet.paste(image,(x+(416-image.width)//2,y+25));draw.text((x+5,y+3),label,fill='white')
    sheet.save(output,quality=90)


def build(private: Path, output: Path, videos: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    (output/'DESIGN.md').write_text('''# Offline research review design
Purpose: compare source, target, two anchors and raw generation without quality claims.
Colors: background #101418; surface #1b222a; text #edf1f5; links #91caff; caution #efbd68; border #495561.
Typography: system sans, body16/1.6, title28, captions14.
Spacing:12/16/24/40px; desktopmax1600px.
Components: fullframe figures, pairedvideos, accessibleframe sliders, explicitstatus panels.
Responsive:650px breakpoint stacks comparisons; gridmin260px.
Motion: native16fpsmedia only; no decorativeanimations. Temporal quality remainsUNVERIFIED.
''')
    sections=[];summary={}
    for case in ('case_rigid','case_nonrigid'):
        root=output/case;root.mkdir();src=private/'inputs'/case;anchors=private/'anchors'/case
        clip=videos/case
        for name in ('source.mp4','manifest.json','contact_sheet.jpg'):
            copy(src/name,root/name)
        copy(src/'reference/full.png',root/'reference.png');copy(src/'reference/crop.png',root/'reference-crop.png')
        for name in ('start','end'):
            copy(anchors/f'{name}.png',root/f'anchor-{name}.png')
            copy(anchors/f'{name}-original.png',root/f'anchor-{name}-original.png')
        source_frames=sorted((src/'source').glob('*.png'))
        assert len(source_frames)==33,'Review requires actual33sourceframes'
        for index,path in enumerate(source_frames):copy(path,root/'source-frames'/f'{index:03d}.png')
        generated=copy(clip/'generated.mp4',root/'generated.mp4')
        copy(clip/'result.json',root/'result.json')
        generated_frames=sorted((clip/'frames').glob('*.png'))
        for index,path in enumerate(generated_frames):copy(path,root/'generated-frames'/f'{index:03d}.png')
        summary[case]={'generated_video':generated,'generated_frames':len(generated_frames),'source_frames':33,'temporal':'UNVERIFIED','sam_conditioning':'NOT_RUN'}
        assets=[root/'source-frames/000.png',root/'reference.png',root/'anchor-start.png',root/'source-frames/032.png',root/'reference-crop.png',root/'anchor-end.png']
        assert all(path.exists() for path in assets),'Review missing realanchor/input'
        contact_sheet(assets,['Source start','Target full','Edited start','Source end','Target crop','Edited end'],root/'anchors-sheet.jpg',3)
        if generated_frames:
            contact_sheet(generated_frames,[f'Generated {i}' for i in range(len(generated_frames))],root/'generated-sheet.jpg',4)
            selected=[i for i in (8,16,24) if i<len(generated_frames)]
            contact_sheet([source_frames[i] for i in selected]+[generated_frames[i] for i in selected],[f'Source {i}' for i in selected]+[f'Generated {i}' for i in selected],root/'middle-sheet.jpg',3)
        if len(generated_frames)==33:
            boxes=json.loads((src/'manifest.json').read_text())['records']
            left=min(row['bbox'][0] for row in boxes);top=min(row['bbox'][1] for row in boxes)
            right=max(row['bbox'][2] for row in boxes);bottom=max(row['bbox'][3] for row in boxes)
            margin=max(30,round(max(right-left,bottom-top)*.15))
            crop=(max(0,left-margin),max(0,top-margin),min(832,right+margin),min(480,bottom+margin))
            (root/'evaluation-crop.json').write_text(json.dumps({'bbox_xyxy':crop,'source':'all33sourceGTunion','margin_fraction':.15,'minimum_margin_pixels':30,'same_crop_source_generated':True,'output_alignment_or_warp':False},indent=2))
            cropped=[];labels=[]
            for name,paths in [('SOURCE',source_frames),('GENERATED',generated_frames)]:
                for index in (8,16,24):
                    target=root/f'{name.lower()}-crop-{index:03d}.png'
                    with Image.open(paths[index]) as frame:frame.crop(crop).save(target)
                    cropped.append(target);labels.append(f'{name} {index}/32 - fixed source-GT crop')
            contact_sheet(cropped,labels,root/'middle-target-sheet.jpg',3)
            contact_sheet([root/'anchor-start.png',generated_frames[0],root/'anchor-end.png',generated_frames[32]],['Input START anchor','Actual GENERATED first','Input END anchor','Actual GENERATED last'],root/'endpoint-sheet.jpg',2)
        cards=figure(f'{case}/source.mp4','SOURCE · 33 frames / preview16fps',True)+figure(f'{case}/reference.png','TARGET REFERENCE')+figure(f'{case}/anchor-start.png','START ANCHOR · t=0')+figure(f'{case}/anchor-end.png','END ANCHOR · t=32')
        cards+=figure(f'{case}/generated.mp4','GENERATED VIDEO · raw output',True) if generated else '<p class="status">GENERATED VIDEO: NOT_AVAILABLE · 실제 출력이 없어 표시하지 않습니다.</p>'
        frame_cards=[]
        for label,folder,count in [('SOURCE','source-frames',33),('GENERATED','generated-frames',len(generated_frames))]:
            if count==33:
                paths=[f'{case}/{folder}/{i:03d}.png' for i in range(33)]
                frame_cards.append(f'<figure><img data-frames="{html.escape(json.dumps(paths),quote=True)}" src="{paths[0]}" alt="{label} selected frame"><figcaption>{label}</figcaption></figure>')
        extras=figure(f'{case}/anchors-sheet.jpg','양끝 source / target / anchor 비교')+figure(f'{case}/contact_sheet.jpg','SOURCE 전체33프레임')
        if generated_frames:extras+=figure(f'{case}/generated-sheet.jpg','GENERATED 전체프레임')+figure(f'{case}/middle-sheet.jpg','중간0.25 / 0.5 / 0.75 시점 · 같은fullframe좌표')
        if len(generated_frames)==33:
            extras+=figure(f'{case}/middle-target-sheet.jpg','중간대상확대 · source GT 전체구간union+15%margin · source/generated 동일고정crop · output정합없음')+figure(f'{case}/endpoint-sheet.jpg','입력양끝앵커와 실제생성양끝 · 사후덮어쓰기없음')
        analysis_html='<p>SAM 분석 상태: 실제 분석 산출물 미수집. source GT는 입력manifest에 MASK_GIVEN으로 기록했습니다.</p>'
        analysis_root=private/'analysis'/case
        analysis_cards=[]
        for part,indices in [('source',(0,16,32)),('start',(0,)),('end',(0,))]:
            for index in indices:
                name=f'{index:03d}-overlay.png'
                if copy(analysis_root/part/name,root/'analysis'/part/name):
                    if part!='source' or index in (0,16,32):
                        analysis_cards.append(figure(f'{case}/analysis/{part}/{name}',f'SAM analysis {part} {index} · 생성조건아님'))
                copy(analysis_root/part/f'{index:03d}-mask.png',root/'analysis'/part/f'{index:03d}-mask.png')
            if copy(analysis_root/part/'objects.json',root/'analysis'/part/'objects.json'):
                analysis_cards.append(f'<p><a href="{case}/analysis/{part}/objects.json">{part} 객체·role 기록</a></p>')
        overlays=sorted((analysis_root/'source').glob('*-overlay.png'))
        if len(overlays)==33:
            subprocess.run(['ffmpeg','-v','error','-n','-framerate','16','-i',str(analysis_root/'source/%03d-overlay.png'),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(root/'source-track-overlay.mp4')],check=True)
            analysis_cards.insert(0,figure(f'{case}/source-track-overlay.mp4','SAM source track · 33 overlays를16fps로인코딩한검토파생본 · 모델생성영상아님',True))
        if analysis_cards:
            analysis_html='<div class="grid">'+''.join(analysis_cards)+'</div>'
        copy(private/'analysis/summary.json',output/'analysis-summary.json')
        extras+=analysis_html
        sections.append(f'''<section data-case="{case}"><h2>{case}</h2><p class="status">TEMPORAL_UNVERIFIED · source_fps=null / timebase_assumed=true · 객체 분석은 평가용이며 SAM-conditioned 생성이 아닙니다.</p><div class="grid">{cards}</div><button type="button">두 영상 처음부터 재생</button><p>33/16초 파일길이, 첫·끝 표본간32/16초(가정). 원본의 실제 초단위 타이밍 보존은 주장하지 않습니다.</p><label>프레임 <output>0</output> /32<input aria-label="{case} 비교프레임" type="range" min="0" max="32" value="0"></label><div class="pair">{''.join(frame_cards)}</div><details><summary>앵커·전체프레임·중간시점 시트</summary>{extras}</details><p>확인할 항목: target외형, 방향과이벤트순서, 보호장면, 중간형태변화, 깜빡임. <a href="{case}/manifest.json">입력manifest</a></p></section>''')
    page=f'''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>C-001 실제 양끝 앵커 기준선 검토</title><style>{STYLE}</style><main><h1>C-001 · 양끝 앵커 영상 기준선</h1><p>native imagegen 편집 앵커와 로컬 VACE 생성 결과. 전체중간source RGB와 SAM track은 기본영상모델 입력에 포함하지 않았습니다. 실제 파일만 표시하며 기술실행과 품질판정을 구분합니다.</p><table><tr><th>정보</th><th>영상조건</th></tr><tr><td>양끝전체RGB + caption</td><td>예 · 지정시점</td></tr><tr><td>중간source RGB</td><td>아니오 · 동작비교</td></tr><tr><td>SAM / GT / 수동support</td><td>아니오 · 분석/평가만</td></tr></table>{''.join(sections)}</main><script>{JS}</script></html>'''
    (output/'index.html').write_text(page)
    (output/'review-status.json').write_text(json.dumps(summary,indent=2))
    hashes={str(path.relative_to(output)):hashlib.sha256(path.read_bytes()).hexdigest() for path in output.rglob('*') if path.is_file()}
    (output/'REVIEW_PAYLOAD.json').write_text(json.dumps(hashes,indent=2))
    print(json.dumps(summary))

if __name__=='__main__':
    private,output=map(Path,sys.argv[1:3]);videos=Path(sys.argv[3]) if len(sys.argv)>3 else private/'video'
    build(private,output,videos)
