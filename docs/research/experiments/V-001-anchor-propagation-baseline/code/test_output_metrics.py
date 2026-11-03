"""CPU fixtures for coordinates, literal reflections and missing measurements."""
import math
import numpy as np
from PIL import Image

from output_metrics import Frame, canonical, canonical_object, match_cast, object_metrics, transition, visible_support
from reflections import classify
from sam_analysis import describe
from test_reflections import obj


def test_engine_geometry() -> None:
    assert canonical(Image.new('RGB',(1152,640)), 'E1',mask=False).size == (1280,720)
    e1_support = visible_support('E1')
    assert not e1_support[:5].any() and not e1_support[-5:].any()
    assert e1_support[5:-5].all()
    e1mask = Image.new('L',(1152,640));e1mask.putpixel((500,200),255)
    e1mapped = np.asarray(canonical(e1mask,'E1',mask=True)) > 0
    row = obj(1,[400,100,600,300])
    converted = canonical_object(row,e1mapped,'E1')
    assert converted['center'] is not None and converted['bbox'] is not None
    assert math.isclose(converted['center'][0],(500+.5)*1280/1152-.5)
    assert math.isclose(converted['center'][1],(200+4+.5)*720/648-.5)
    expected_bbox = [400*1280/1152,104*720/648,600*1280/1152,304*720/648]
    assert all(math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12)
               for actual, expected in zip(converted['bbox'], expected_bbox, strict=True))
    support = visible_support('E2')
    assert not support[:,0].any() and not support[:,-1].any()
    assert support[:,640].all() and int(support.sum()) < 1280*720
    mask = Image.new('L',(832,480));mask.putpixel((406,240),255)
    mapped = np.asarray(canonical(mask,'E2',mask=True)) > 0
    yy,xx=np.where(mapped)
    assert abs(float(xx.mean())-((406+10+.5)*1280/853-.5)) < 1
    assert abs(float(yy.mean())-((240+.5)*720/480-.5)) < 1


def test_cast_and_missing() -> None:
    source = [obj(0,[400,100,500,300]),obj(1,[100,100,200,300])]
    output = [obj(8,[100,100,200,300]),obj(7,[400,100,500,300]),obj(9,[400,300,500,500])]
    cast = match_cast(source,output)
    assert cast == {'Lab':7,'IG':8}
    assert classify(output)['reflection_track_indices'] == [9]
    rgb=np.zeros((720,1280,3),dtype=np.uint8);union=np.zeros((720,1280),dtype=bool)
    errors,ratio,opposite=object_metrics(Frame(rgb,source,{},union),Frame(rgb,output,{},union),cast)
    assert errors == {'Lab':0.0,'IG':0.0} and ratio == 1 and opposite is False
    errors,ratio,opposite=object_metrics(Frame(rgb,source,{},union),Frame(rgb,output[1:],{},union),cast)
    assert errors['IG'] is None and ratio is None and opposite is None
    assert match_cast(source,[obj(6,[100,100,200,300])]) is None
    ambiguous=[obj(6,[250,100,350,300]),obj(7,[250,100,350,300])]
    assert match_cast(source,ambiguous) is None


def test_background_reflection_exclusion() -> None:
    rgb=np.zeros((720,1280,3),dtype=np.uint8);changed=rgb.copy();changed[500:600,100:200]=200
    union=np.zeros((720,1280),dtype=bool);union[500:600,100:200]=True
    before=Frame(rgb,[],{},union);after=Frame(changed,[],{},union)
    count,out,src=transition(before,before,before,after,visible_support('E2'))
    assert count > 0 and out == 0 and src == 0
    changed[:]=10
    after=Frame(changed,[],{},union)
    assert transition(before,before,before,after,visible_support('E1'))[1] == 10
    assert describe(np.zeros((720,1280),dtype=bool),4)['present'] is False


if __name__ == '__main__':
    test_engine_geometry();test_cast_and_missing();test_background_reflection_exclusion()
    print('3 output metric CPU fixture groups PASS')
