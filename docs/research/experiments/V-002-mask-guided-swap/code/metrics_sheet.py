# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run: existing Python metrics_sheet.py /private/metrics-config.json /private/sheet.jpg
"""Fixed nine-time diagnostic derivative; never alters the original video."""
from __future__ import annotations

from pathlib import Path
import json
import sys

import numpy as np
from PIL import Image, ImageDraw
from numpy.typing import NDArray

from metrics import Config
from output_metrics import Frame, canonical, load_frame
from reflections import classify


def actual_mask(frame: Frame) -> NDArray[np.bool_]:
    result = np.zeros((720, 1280), dtype=bool)
    for track in classify(frame.objects)['actual_track_indices']:
        result |= frame.masks[track]
    return result


def silhouette_overlay(source: Frame, output: Frame) -> Image.Image:
    """Cyan source, magenta output, white overlap; actual instances only."""
    a, b = actual_mask(source), actual_mask(output)
    rgb = (source.rgb.astype(np.float32)*.35).astype(np.uint8)
    rgb[a & ~b] = (0, 220, 220)
    rgb[b & ~a] = (240, 0, 240)
    rgb[a & b] = (255, 255, 255)
    return Image.fromarray(rgb)


def main() -> None:
    config_path, destination = map(Path, sys.argv[1:])
    cfg = Config.read(config_path)
    raw = json.loads(config_path.read_text())
    source, output = (json.loads(path.read_text()) for path in (cfg.source_summary, cfg.output_summary))
    src_images, out_images = (sorted(path.glob('*.png')) for path in (cfg.source_frames, cfg.output_frames))
    input_images = sorted(Path(raw['input_frames']).glob('*.png')) if raw.get('input_frames') else []
    input_geometry = raw.get('input_geometry', cfg.geometry)
    width, height, label = 320, 180, 25
    sheet = Image.new('RGB', (width*9, (height+label)*4+40), 'white')
    draw = ImageDraw.Draw(sheet)
    draw.text((5, 5), 'EVALUATION DERIVATIVE | rows: source / model input / output / masks (cyan=source magenta=output white=overlap)', fill='black')
    for column, index in enumerate(range(0, 73, 9)):
        sf = load_frame(cfg.source_summary.parent, src_images[index], source['frames'][index]['objects'], index, 'CANONICAL')
        panels: list[Image.Image | None] = [Image.fromarray(sf.rgb), None, None, None]
        if index < len(input_images):
            with Image.open(input_images[index]) as image:
                panels[1] = canonical(image.convert('RGB'), input_geometry, mask=False)
        if index < len(out_images):
            of = load_frame(cfg.output_summary.parent, out_images[index], output['frames'][index]['objects'], index, cfg.geometry)
            panels[2] = Image.fromarray(of.rgb)
            panels[3] = silhouette_overlay(sf, of)
        for row, panel in enumerate(panels):
            x, y = column*width, 40+row*(height+label)
            draw.text((x+4, y+4), f'{("SOURCE", "INPUT", "OUTPUT", "MASKS")[row]} t={index} source={240+index}', fill='black')
            if panel is None:
                draw.rectangle((x, y+label, x+width-1, y+label+height-1), fill=(225, 225, 225))
                draw.text((x+10, y+label+70), 'NOT GENERATED' if row >= 2 else 'INPUT NOT AVAILABLE', fill='black')
            else:
                sheet.paste(panel.resize((width, height), Image.Resampling.BILINEAR), (x, y+label))
    sheet.save(destination, quality=92)
    with Image.open(destination) as image:
        assert image.size == sheet.size
        image.verify()
    print(json.dumps({'status': 'DERIVATIVE_SHEET_WRITTEN', 'sample_indices': list(range(0, 73, 9)), 'size': sheet.size}))


if __name__ == '__main__':
    main()
