"""CPU media helpers for scaled condition construction."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

import numpy as np
from numpy.typing import NDArray
from PIL import Image, ImageDraw

from scaled_geometry import bbox


@dataclass(frozen=True, slots=True)
class Canvas:
    master: tuple[int, int]
    target: tuple[int, int]

    @property
    def resized(self) -> tuple[int, int]:
        factor = max(self.target[0]/self.master[0], self.target[1]/self.master[1])
        return round(self.master[0]*factor), round(self.master[1]*factor)

    def image(self, image: Image.Image, mask: bool) -> Image.Image:
        if image.size == self.target:
            return image.copy()
        assert image.size == self.master
        width, height = self.resized
        resized = image.resize((width, height), Image.Resampling.NEAREST if mask else Image.Resampling.LANCZOS)
        left, top = (width-self.target[0])//2, (height-self.target[1])//2
        return resized.crop((left, top, left+self.target[0], top+self.target[1]))


def read_masks(summary: Path, index: int, canvas: Canvas) -> dict[int, NDArray[np.bool_]]:
    data = json.loads(summary.read_text())
    rows = next(frame['objects'] for frame in data['frames'] if frame['index'] == index)
    masks = {}
    for row in rows:
        if not row['present']:
            continue
        with Image.open(summary.parent/f"{index:03d}-track-{row['track_index']:02d}.png") as image:
            assert list(image.size) == data['coordinate_size']
            transformed = canvas.image(image.convert('L'), True)
            mask = np.asarray(transformed) > 0
        if mask.any():
            masks[row['track_index']] = mask
    return masks


def describe(track: int, mask: NDArray[np.bool_]) -> dict:
    yy, xx = np.nonzero(mask)
    return {'track_index': track, 'present': bool(len(xx)), 'area': int(len(xx)),
            'area_fraction': len(xx)/mask.size,
            'bbox': list(bbox(mask)) if len(xx) else None,
            'center': [float(xx.mean()), float(yy.mean())] if len(xx) else None}


def review_panel(path: Path, canvas: Canvas) -> Image.Image:
    with Image.open(path) as image:
        return canvas.image(image.convert('RGB'), False)


def write_sheet(panels: list[tuple[int, Image.Image, Image.Image, Image.Image]], path: Path) -> None:
    """Each row shows source canny, scaled canny, and the accepted anchor."""
    width = 384
    height = round(panels[0][1].height*width/panels[0][1].width)
    band = 24
    sheet = Image.new('RGB', (width*3, (height+band)*len(panels)), 'white')
    draw = ImageDraw.Draw(sheet)
    for row, (frame, original, scaled, anchor) in enumerate(panels):
        for column, (label, image) in enumerate(zip(('SOURCE CANNY', 'SCALED CANNY', 'ANCHOR'), (original, scaled, anchor))):
            x, y = column*width, row*(height+band)
            draw.text((x+4, y+5), f'f{frame:03d} {label}', fill='black')
            sheet.paste(image.resize((width, height), Image.Resampling.LANCZOS), (x, y+band))
    sheet.save(path)


def overlay(anchor: Image.Image, scaled: NDArray[np.bool_], target: NDArray[np.bool_]) -> Image.Image:
    rgb = np.asarray(anchor).astype(np.float32).copy()
    red, green = np.array([255, 0, 0]), np.array([0, 255, 0])
    rgb[scaled] = .5*rgb[scaled]+.5*red
    rgb[target] = .5*rgb[target]+.5*green
    return Image.fromarray(np.rint(rgb).clip(0, 255).astype(np.uint8))
