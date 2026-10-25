"""Write a self-contained local HTML review after actual comparison assets exist."""
from pathlib import Path
import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    root = args.root
    required = ['reports/comparison-final/comparison-30fps.mp4', 'reports/comparison-final/comparison-all17.png', 'reports/comparison-final/comparison-reference-lab.png']
    for relative in required:
        if not (root / relative).is_file():
            raise FileNotFoundError(relative)
    html = '''<!doctype html>
<html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="B-025 비공개 원본·새 Lab·새 IG 비교"><title>B-025 비공개 비교</title>
<style>
:root{--bg:#14181d;--surface:#20262e;--text:#f1f4f7;--muted:#bec7d2;--link:#8cc8ff;--s:8px;--body:16px;--title:24px;--small:14px;--width:1440px;--ref:448px}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:var(--body)/1.5 system-ui,sans-serif}main{max-width:var(--width);margin:auto;padding:calc(3*var(--s))}h1,h2{font-size:var(--title);line-height:1.3}a{color:var(--link)}p{color:var(--muted)}video,.frame{width:100%;height:auto;background:var(--surface)}.reference{width:100%;max-width:var(--ref);height:auto}button{font:inherit;padding:var(--s);background:var(--surface);color:var(--text);border:1px solid var(--muted);cursor:pointer}button:focus-visible,a:focus-visible,input:focus-visible{outline:3px solid var(--link)}.controls{display:flex;align-items:center;gap:var(--s);flex-wrap:wrap;margin:calc(2*var(--s)) 0}input[type=range]{flex:1;min-width:120px}summary{cursor:pointer}section{margin-block:calc(3*var(--s))}.note{font-size:var(--small)}
</style><main><h1>B-025 · 원본 / REF_LAB / REF_IG</h1>
<p>비공개 연구 검토. 왼쪽 SOURCE, 가운데 새 REF_LAB, 오른쪽 새 REF_IG. 각 입력 896×512, 전체 17프레임, 30fps, 0.5667초. 두 생성 모두 adapter OFF입니다.</p>
<p>비교 MP4는 재인코딩한 보기 자료이며 원시 출력과 PNG가 별도로 보존됩니다. 보간·warp·안정화·프레임 복제 없음. temporal=UNVERIFIED: 파일 재생 기능 확인은 사람이 연속 시청한 품질 검수를 의미하지 않습니다.</p>
<p>정적 전체 프레임 검토: IG 외형 변화는 색상 이상으로 보이지만, 참조의 웅크린 자세가 남아 원본의 사족 직립 전달은 FAIL입니다. 바닥 밧줄 소실 등 장면 보존은 PARTIAL이며 실제 개체 일치는 확정하지 않았습니다.</p>
<section><h2>실제 속도</h2><video id="video" controls preload="metadata" width="2688" height="544" src="reports/comparison-final/comparison-30fps.mp4"></video>
<div class="controls"><label><input id="loop" type="checkbox"> 반복 재생</label><span>반복 시 local16→0은 반복 경계이며 구간 내부 동작이 아닙니다.</span></div>
<a download href="reports/comparison-final/comparison-30fps.mp4">비교 MP4 다운로드</a></section>
<section><h2>전체 17프레임 개별 확인</h2><div class="controls"><button id="previous" type="button">이전</button><label for="frame">local 프레임</label><input id="frame" type="range" min="0" max="16" value="0" step="1"><button id="next" type="button">다음</button><output id="number">local0 / source126 / 4.2000초</output></div>
<img id="still" class="frame" width="2688" height="544" src="reports/comparison-final/comparison-frames/000.png" alt="local0 원본·Lab 참조·IG 참조 전체 화면 비교">
<p><a href="reports/comparison-final/comparison-all17.png">전체17프레임 시트</a> · <a href="reports/comparison-final/comparison-local0-8-16.png">사전 지정 local0/8/16</a> · <a href="reports/comparison-final/comparison-manifest.json">입출력 해시와 변환 기록</a></p></section>
<section><h2>실제 Lab reference</h2><img class="reference" width="896" height="512" src="reports/comparison-final/comparison-reference-lab.png" alt="실험에 사용한 Lab 참조 전체 캔버스"><h2>실제 IG reference</h2><img class="reference" width="896" height="512" src="reports/comparison-final/comparison-reference-ig.png" alt="기존 IG support 밖만 회색128로 바꾼 실제 참조"><p><a href="reports/reference-pair-preregistered.png">두 참조와 마스크 overlay</a> · <a href="reports/REFERENCE_INPUT_PROVENANCE.json">입력 원본·support 계보</a></p><p>reference는 영상 시간축에 삽입하지 않았습니다. 실제 개체와 품종 유사성, 자세와 국소 움직임은 각각 평가합니다.</p></section>
</main><script>
const slider=document.getElementById('frame'), still=document.getElementById('still'), number=document.getElementById('number');
function show(i){i=Math.max(0,Math.min(16,i));slider.value=i;still.src='reports/comparison-final/comparison-frames/'+String(i).padStart(3,'0')+'.png';still.alt='local'+i+' 원본·Lab 참조·IG 참조 전체 화면 비교';number.textContent='local'+i+' / source'+(126+i)+' / '+((126+i)/30).toFixed(4)+'초';document.getElementById('previous').disabled=i===0;document.getElementById('next').disabled=i===16;}
slider.addEventListener('input',()=>show(Number(slider.value)));document.getElementById('previous').addEventListener('click',()=>show(Number(slider.value)-1));document.getElementById('next').addEventListener('click',()=>show(Number(slider.value)+1));document.getElementById('loop').addEventListener('change',event=>{document.getElementById('video').loop=event.target.checked});show(0);
</script></html>'''
    path = root / 'review.html'
    if path.exists():
        raise FileExistsError(path)
    path.write_text(html)


if __name__ == '__main__':
    main()
