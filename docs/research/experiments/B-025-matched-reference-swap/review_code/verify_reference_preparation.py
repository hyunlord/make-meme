"""Reconstruct the frozen IG input on CPU and verify exact pixels, without writes.

Run: python verify_reference_preparation.py PRIVATE_B025_ROOT
Uses only the original/support copies and frozen Lab/IG files in that root.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root: Path) -> None:
    ig = root / 'inputs' / 'REF_IG'
    with Image.open(ig / 'original.jpeg') as image:
        original = image.convert('RGB')
    with Image.open(ig / 'existing-support-1600x1200.png') as image:
        support = image.convert('L')
    canvas = Image.new('RGB', (896, 512), 'white')
    canvas.paste(original.resize((683, 512), Image.Resampling.LANCZOS), (106, 0))
    support_canvas = Image.new('L', (896, 512), 0)
    support_canvas.paste(support.resize((683, 512), Image.Resampling.NEAREST), (106, 0))
    foreground = np.asarray(support_canvas) > 127
    expected = np.full((512, 896, 3), 128, dtype=np.uint8)
    expected[foreground] = np.asarray(canvas)[foreground]
    semantic = np.zeros_like(expected)
    semantic[foreground] = (255, 0, 0)
    with Image.open(ig / 'reference.png') as image:
        np.testing.assert_array_equal(np.asarray(image.convert('RGB')), expected)
    with Image.open(ig / 'reference-mask.png') as image:
        np.testing.assert_array_equal(np.asarray(image.convert('RGB')), semantic)
    with Image.open(ig / 'reference-before-neutral.png') as image:
        np.testing.assert_array_equal(np.asarray(image.convert('RGB')), np.asarray(canvas))
    print(json.dumps({'status': 'PASS', 'scope': 'Exact input reconstruction, not segmentation or identity quality', 'support_pixels': int(foreground.sum()), 'reference_sha256': digest(ig / 'reference.png'), 'mask_sha256': digest(ig / 'reference-mask.png'), 'new_model_calls': 0}, indent=2))


if __name__ == '__main__':
    verify(Path(sys.argv[1]).resolve())
