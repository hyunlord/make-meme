"""Existing local Chrome/CDP review, no installs, no generated video quality claim."""
from __future__ import annotations
import argparse
import base64
import json
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
import websocket


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    output = root / 'viewer-check'
    output.mkdir(exist_ok=False)
    chrome = Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    with tempfile.TemporaryDirectory(prefix='b033-review-chrome-') as profile:
        with (output / 'chrome.log').open('w') as log:
            proc = subprocess.Popen([str(chrome), '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0', '--remote-allow-origins=http://localhost', '--user-data-dir='+profile, 'about:blank'], stdout=log, stderr=log)
            try:
                active = Path(profile) / 'DevToolsActivePort'
                for _ in range(100):
                    if active.is_file():
                        break
                    time.sleep(.1)
                port = int(active.read_text().splitlines()[0])
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list') as response:
                    targets = json.load(response)
                page = next(t for t in targets if t['type'] == 'page')
                ws = websocket.create_connection(page['webSocketDebuggerUrl'], origin='http://localhost', timeout=15)
                counter = 0
                def call(method: str, params: dict | None = None) -> dict:
                    nonlocal counter
                    counter += 1
                    ws.send(json.dumps({'id':counter,'method':method,'params':params or {}}))
                    while True:
                        value = json.loads(ws.recv())
                        if value.get('id') == counter:
                            if 'error' in value:
                                raise RuntimeError(value['error'])
                            return value['result']
                def evaluate(expression: str) -> object:
                    result = call('Runtime.evaluate', {'expression':expression,'returnByValue':True})
                    if result.get('exceptionDetails'):
                        raise RuntimeError(result)
                    return result['result'].get('value')
                call('Page.enable')
                call('Page.navigate', {'url':(root / 'review.html').as_uri()})
                for _ in range(100):
                    if evaluate("document.readyState==='complete' && [...document.querySelectorAll('img')].every(x=>x.complete)"):
                        break
                    time.sleep(.1)
                for _ in range(100):
                    if evaluate("document.querySelectorAll('video').length===8 && [...document.querySelectorAll('video')].every(v=>v.readyState>=2)"):
                        break
                    time.sleep(.1)
                media = evaluate("(()=>{const v=document.querySelector('video');return {readyState:v.readyState,duration:v.duration,width:v.videoWidth,height:v.videoHeight,error:v.error?.code||null}})()")
                assert media['readyState'] >= 2 and media['width'] == 896 and media['height'] == 512
                all_media = evaluate("[...document.querySelectorAll('video')].map(v=>({src:v.getAttribute('src'),readyState:v.readyState,width:v.videoWidth,height:v.videoHeight,error:v.error?.code||null}))")
                assert len(all_media) == 8 and all(v['readyState'] >= 1 and v['width'] == 896 and v['height'] == 512 and v['error'] is None for v in all_media)
                playback = call('Runtime.evaluate', {'expression': "(async()=>{const vs=[...document.querySelectorAll('video')];await Promise.all(vs.map(v=>v.play()));await new Promise(r=>setTimeout(r,150));const result=vs.map(v=>({time:v.currentTime,advanced:v.currentTime>0,error:v.error?.code||null}));vs.forEach(v=>{v.pause();v.currentTime=0});return result})()", 'awaitPromise':True, 'returnByValue':True, 'userGesture':True})
                assert 'exceptionDetails' not in playback, playback
                playback_values = playback['result']['value']
                assert all(v['advanced'] and v['error'] is None for v in playback_values)
                checks = evaluate("""(()=>{const r={};r.tasks=[...document.querySelectorAll('section#comparison')].map(p=>{const s=p.querySelector('input'),v=p.querySelector('video'),x={};x.initial=s.value==='0'&&!v.loop&&!v.autoplay;s.value='16';s.dispatchEvent(new Event('input'));x.last=p.querySelector('.controls span').textContent==='local 16 / 16'&&v.paused;s.value='0';s.dispatchEvent(new Event('input'));return x;});r.links=[...document.querySelectorAll('[src],a[href]')].map(e=>e.getAttribute('src')||e.getAttribute('href'));return r})()""")
                assert isinstance(checks, dict)
                assert len(checks['tasks']) == 1 and all(all(task.values()) for task in checks['tasks'])
                for link in checks['links']:
                    assert link.startswith('#') or (root / link).is_file(), link
                evaluate("document.querySelector('#play').focus()")
                checks['focus'] = evaluate("document.activeElement.id==='play'")
                screenshots = []
                for width,height,label in [(1280,900,'desktop'),(768,1024,'tablet'),(375,812,'mobile')]:
                    call('Emulation.setDeviceMetricsOverride', {'width':width,'height':height,'deviceScaleFactor':1,'mobile':False})
                    time.sleep(.3)
                    assert evaluate("document.documentElement.scrollWidth<=innerWidth"), 'Horizontal overflow'
                    shot = call('Page.captureScreenshot', {'format':'png','captureBeyondViewport':False})
                    name = output / f'{label}.png'
                    name.write_bytes(base64.b64decode(shot['data']))
                    screenshots.append(str(name.relative_to(root)))
                call('Emulation.setDeviceMetricsOverride', {'width':1280,'height':900,'deviceScaleFactor':1,'mobile':False})
                for task in ('comparison',):
                    evaluate(f"document.getElementById('{task}').scrollIntoView()")
                    time.sleep(.2)
                    shot = call('Page.captureScreenshot', {'format':'png','captureBeyondViewport':False})
                    name = output / f'{task}-matrix.png'
                    name.write_bytes(base64.b64decode(shot['data']))
                    screenshots.append(str(name.relative_to(root)))
                result = {'playback_advancement':playback_values,'all_video_metadata':all_media,'status':'CONTROLS_AND_LINKS_PASS','checks':checks,'video_metadata':media,'screenshots':screenshots,'continuous_video_viewing':False,'temporal_quality':'UNVERIFIED','scope':'Headless browser layout and controls only; screenshots require visual inspection separately.'}
                (output / 'result.json').write_text(json.dumps(result,indent=2)+'\n')
                ws.close()
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill(); proc.wait()


if __name__ == '__main__':
    main()
