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
    output = root / 'reports/viewer-check'
    output.mkdir(exist_ok=False)
    chrome = Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    with tempfile.TemporaryDirectory(prefix='b024-review-chrome-') as profile:
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
                    if evaluate("document.readyState==='complete' && document.getElementById('still')?.complete"):
                        break
                    time.sleep(.1)
                checks = evaluate("""(()=>{const s=document.getElementById('frame'),v=document.getElementById('video'),r={};r.initial=s.value==='0'&&document.getElementById('previous').disabled&&!v.loop&&!v.autoplay;document.getElementById('next').click();r.next=s.value==='1'&&document.getElementById('still').getAttribute('src').endsWith('001.png');s.value='16';s.dispatchEvent(new Event('input'));r.last=document.getElementById('next').disabled&&document.getElementById('number').textContent.includes('source142');document.getElementById('previous').click();r.previous=s.value==='15';const l=document.getElementById('loop');l.checked=true;l.dispatchEvent(new Event('change'));r.loop=v.loop;l.checked=false;l.dispatchEvent(new Event('change'));s.value='0';s.dispatchEvent(new Event('input'));r.links=[...document.querySelectorAll('[src],a[href]')].map(e=>e.getAttribute('src')||e.getAttribute('href'));return r})()""")
                assert isinstance(checks, dict)
                assert all(checks[k] for k in ('initial','next','last','previous','loop'))
                for link in checks['links']:
                    assert (root / link).is_file(), link
                screenshots = []
                for width,height,label in [(1440,1080,'desktop'),(390,844,'mobile')]:
                    call('Emulation.setDeviceMetricsOverride', {'width':width,'height':height,'deviceScaleFactor':1,'mobile':False})
                    time.sleep(.3)
                    shot = call('Page.captureScreenshot', {'format':'png','captureBeyondViewport':False})
                    name = output / f'{label}.png'
                    name.write_bytes(base64.b64decode(shot['data']))
                    screenshots.append(str(name.relative_to(root)))
                result = {'status':'CONTROLS_AND_LINKS_PASS','checks':checks,'screenshots':screenshots,'continuous_video_viewing':False,'temporal_quality':'UNVERIFIED','scope':'Headless browser layout and controls only; screenshots require visual inspection separately.'}
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
