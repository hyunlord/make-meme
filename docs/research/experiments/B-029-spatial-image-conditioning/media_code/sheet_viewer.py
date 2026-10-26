# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
# Existing environment: python sheet_viewer.py REVIEW_ROOT
"""Build a portable all-frame viewer from canonical contact sheets, without duplicate PNGs."""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

from PIL import Image


def write_viewer(root: Path) -> None:
    """Reuse canonical sheet pixels; slider reveals a row without media reencoding."""
    sections = []
    for folder in sorted(root.iterdir()):
        if not (folder / 'all17.png').is_file() or not (folder / 'manifest.json').is_file():
            continue
        with Image.open(folder / 'all17.png') as image:
            width, height = image.size
        name = html.escape(folder.name, quote=True)
        manifest = json.loads((folder / 'manifest.json').read_text())
        labels = html.escape(' / '.join(manifest['labels']))
        sections.append(f'''<section><h2>{name}: {labels}</h2>
<p>17 frames; source FPS unknown; preview24fps. Temporal quality UNVERIFIED.</p>
<video controls preload="metadata" src="{name}/comparison-preview24.mp4"></video>
<p>No autoplay or forced loop. End-to-start replay is not within-clip motion.</p>
<div><button class="prev" disabled>Previous frame</button> <button class="next">Next frame</button>
<label>Local frame <input type="range" min="0" max="16" value="0"><output>0</output></label></div>
<p>Frame view uses one row of the canonical all17 sheet: uniform 50% sheet downscale, no subject-specific crop or alignment. Full-resolution values remain in full-package raw tensors.</p>
<div class="sheet-window" style="aspect-ratio:{width}/{height / 17}"><img class="sheet" src="{name}/all17.png" alt="Selected row of all 17 source and output comparisons"></div>
<p><a href="{name}/all17.png">All17 sheet</a> · <a href="{name}/local0-8-16.png">Local0/8/16</a> · <a href="{name}/manifest.json">Provenance</a></p>
<details><summary>Unchanged B027 reference</summary><img src="{name}/references.png" alt="Reference input"></details></section>''')
    template = Path(__file__).with_name('viewer.html').read_text()
    template = template[:template.index('</main><script>')] + '''</main><script>
for(const section of document.querySelectorAll('section')){
 const slider=section.querySelector('input'),out=section.querySelector('output'),image=section.querySelector('.sheet'),prev=section.querySelector('.prev'),next=section.querySelector('.next');
 function show(value){const i=Math.max(0,Math.min(16,Number(value)));slider.value=i;out.textContent=i;prev.disabled=i===0;next.disabled=i===16;image.style.transform='translateY(-'+(100*i/17)+'%)';}
 slider.addEventListener('input',()=>show(slider.value));prev.addEventListener('click',()=>show(Number(slider.value)-1));next.addEventListener('click',()=>show(Number(slider.value)+1));
}
</script></html>'''
    template = template.replace('</style>', '.sheet-window{overflow:hidden}.sheet-window .sheet{width:100%;height:auto;margin:0;display:block}</style>')
    (root / 'review-sheets.html').write_text(template.replace('<!-- TASKS -->', '\n'.join(sections)))


if __name__ == '__main__':
    write_viewer(Path(sys.argv[1]))
