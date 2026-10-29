"""CPU tests of interior boundary and common bbox sampling invariants."""
import numpy as np
import cv2
from prepare_internal import bbox, composite, interior, normalize, restore


def test_geometry() -> None:
    mask = np.zeros((480,832),np.uint8)
    mask[80:280,100:500] = 255
    layout = np.full((480,832,3),255,np.uint8)
    contours,_ = cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(layout,contours,-1,(0,0,0),3)
    allowed = interior(mask,layout)
    assert not allowed[83,150] and allowed[84,150]
    assert bbox(mask) == (100,80,500,280)
    field = np.zeros((480,832),np.float32)
    field[130:230,200:400] = 0.625
    norm = normalize(field,bbox(mask))
    assert norm.shape == (256,256) and norm.dtype == np.float32
    restored = restore(norm,bbox(mask))
    assert np.max(restored[mask == 0]) == 0
    canvas = composite(layout,allowed,restored)
    assert np.array_equal(canvas[~allowed],layout[~allowed])
    assert np.array_equal(canvas[...,0],canvas[...,1])
    assert canvas[180,300,0] == 96
    # Same normalized held field moves/resizes with the new bbox, not screen coordinates.
    translated_box = (300,160,700,360)
    moved = restore(norm,translated_box)
    assert np.isclose(moved[260,500],0.625) and moved[130,200] == 0
    # Identical first source structure produces bitwise-identical DYNAMIC/HOLD at t0.
    assert np.array_equal(composite(layout,allowed,restore(norm,bbox(mask))),canvas)
    changed = norm.copy(); changed[100:150,100:150] = 0.0
    assert not np.array_equal(composite(layout,allowed,restore(changed,bbox(mask))),canvas)
    # All-white source scribble cannot acquire artificial internal lines from normalization.
    white = np.zeros((480,832),np.float32)
    assert np.array_equal(composite(layout,allowed,restore(normalize(white,bbox(mask)),bbox(mask))),layout)


if __name__ == '__main__':
    test_geometry()
    print('PASS: precise interior, pixel-center bbox sampling, shared processing, outside identity, moving HOLD')
