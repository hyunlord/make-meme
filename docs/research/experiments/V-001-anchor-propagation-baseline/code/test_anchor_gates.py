"""Fixed CPU gate fixtures; no model imports or generated-image selection."""
import numpy as np
from anchor_gates import background_mae, geometry
from test_reflections import obj


def test_geometry() -> None:
    source = [obj(0,[100,100,200,300]),obj(1,[400,100,500,300])]
    result = geometry(source,source)
    assert all(result['gates'].values())
    assert result['casting'] == {'Lab':1,'IG':0}
    grown = [obj(0,[100,100,200,300]),obj(1,[400,100,500,421])]
    assert not geometry(source,grown)['gates']['G3']
    assert not geometry(source,[obj(0,[100,100,200,300])])['gates']['G1']


def test_mae_and_reflection_exclusion() -> None:
    source = np.zeros((720,1280,3),dtype=np.uint8)
    anchor = source.copy();anchor[500:600,100:200]=255
    union = np.zeros((720,1280),dtype=bool);union[500:600,100:200]=True
    mae,count = background_mae(source,anchor,union)
    assert mae == 0 and count == 720*1280-148*148
    anchor[:]=12
    assert background_mae(source,anchor,union)[0] == 12
    assert background_mae(source,anchor,np.ones_like(union)) == (None,0)


if __name__ == '__main__':
    test_geometry();test_mae_and_reflection_exclusion();print('2 anchor CPU fixture groups PASS')
