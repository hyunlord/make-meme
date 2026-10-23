"""Browser control QA only; successful playback events do not judge temporal quality."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('review',type=Path)
    args=parser.parse_args()
    failures=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,channel="chrome")
        page=browser.new_page(viewport={'width':1280,'height':960})
        page.on('pageerror',lambda error:failures.append(str(error)))
        page.goto(args.review.resolve().as_uri())
        page.locator('#still').wait_for()
        assert page.locator('#video').get_attribute('src')=='source-reference-four-cases.mp4'
        assert 'B-013' in page.locator('h1').inner_text()
        page.wait_for_function('document.querySelector("#still").complete && document.querySelector("#still").naturalWidth > 0')
        assert page.locator('#prev').is_disabled()
        assert page.locator('#still').get_attribute('src')=='frames/000.png'
        for _ in range(16):page.locator('#next').click()
        assert page.locator('#next').is_disabled()
        assert page.locator('#still').get_attribute('src')=='frames/016.png'
        page.locator('#prev').click()
        assert page.locator('#still').get_attribute('src')=='frames/015.png'
        page.locator('#frame').fill('0')
        page.locator('#frame').dispatch_event('input')
        assert page.locator('#still').get_attribute('src')=='frames/000.png'
        flags=page.locator('#video').evaluate('(v)=>({autoplay:v.autoplay,loop:v.loop,playbackRate:v.playbackRate})')
        assert flags=={'autoplay':False,'loop':False,'playbackRate':1}
        page.wait_for_function('document.querySelector("#video").readyState >= 1')
        page.locator('#once').click()
        page.wait_for_function('document.querySelector("#video").ended',timeout=10000)
        ended=page.locator('#video').evaluate('(v)=>({ended:v.ended,paused:v.paused,duration:v.duration,currentTime:v.currentTime,loop:v.loop})')
        assert ended['ended'] and ended['paused'] and not ended['loop']
        page.screenshot(path=str(args.review.parent/'ui-desktop.png'),full_page=True)
        page.set_viewport_size({'width':400,'height':900})
        page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
        page.wait_for_timeout(300)
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        page.screenshot(path=str(args.review.parent/'ui-mobile.png'),full_page=True)
        assert not failures
        browser.close()
    (args.review.parent/'UI_QA.json').write_text(json.dumps({'controls':'PASS','tested':['frame0/16 bounds','next/previous and slider','no autoplay or loop','one-shot ended and paused','mobile no horizontal overflow'],'browser_flags':flags,'one_shot_events':ended,'page_errors':failures,'temporal_visual_quality':'UNVERIFIED; automated playback events are not human/agent continuous visual observation'},indent=2)+'\n')

if __name__=='__main__':main()
