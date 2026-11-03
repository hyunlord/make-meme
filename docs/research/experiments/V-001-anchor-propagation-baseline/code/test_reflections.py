"""CPU boundary tests for the literal user amendment, without model imports."""
from reflections import cast_present, classify, first_frame_cast
from sam_analysis import ObjectRow


def obj(index: int, bbox: list[int], area: float = .01) -> ObjectRow:
    return {'track_index': index, 'bbox': bbox, 'center': [(bbox[0]+bbox[2])/2, (bbox[1]+bbox[3])/2],
            'area': round(area*1280*720), 'area_fraction': area, 'present': True,
            'meets_area_minimum': area >= .005}


def test_horizontal_inclusive() -> None:
    assert classify([obj(0, [0,0,100,100]),obj(1,[50,100,150,200])])['reflection_track_indices'] == [1]
    assert classify([obj(0, [0,0,100,100]),obj(1,[51,100,151,200])])['reflection_track_indices'] == []


def test_vertical_strict() -> None:
    assert classify([obj(0,[0,0,100,100]),obj(1,[0,60,100,160])])['reflection_track_indices'] == []
    assert classify([obj(0,[0,0,100,100]),obj(1,[0,61,100,161])])['reflection_track_indices'] == [1]


def test_smaller_width_and_self_exclusion() -> None:
    assert classify([obj(0,[0,0,100,100]),obj(1,[90,100,110,200])])['reflection_track_indices'] == [1]
    assert classify([obj(0,[0,0,10,10])])['reflection_track_indices'] == []


def test_cast_ids_area_and_no_reassignment() -> None:
    initial=[obj(2,[0,0,50,100]),obj(9,[100,0,150,100])]
    casting=first_frame_cast(initial)
    assert casting == {'Lab':9,'IG':2}
    assert cast_present([obj(2,[0,0,50,100],.005),obj(9,[100,0,150,100],.005)],casting)
    assert not cast_present([obj(2,[0,0,50,100],.004999),obj(9,[100,0,150,100])],casting)
    assert not cast_present([obj(3,[0,0,50,100]),obj(9,[100,0,150,100])],casting)


if __name__ == '__main__':
    test_horizontal_inclusive(); test_vertical_strict(); test_smaller_width_and_self_exclusion(); test_cast_ids_area_and_no_reassignment()
    print('4 reflection boundary tests PASS')
