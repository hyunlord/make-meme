from __future__ import annotations

import numpy as np
from PIL import Image

from make_meme.pipelines.assign import RefInfo, color_hist, group_refs, hist_dist, pair_groups
from make_meme.pipelines.detect import Subject


def _solid(rgb, size=(64, 64)):
    return Image.new("RGB", size, rgb)


def _ref(label, rgb):
    return RefInfo(path=None, label=label, hist=color_hist(_solid(rgb)))  # type: ignore[arg-type]


def test_hist_distance_bounds():
    a, b = color_hist(_solid((10, 10, 10))), color_hist(_solid((240, 240, 240)))
    assert hist_dist(a, a) == 0.0
    assert hist_dist(a, b) > 0.9


def test_two_different_dogs_are_two_groups_and_same_dog_angles_one_group():
    black_dog, grey_dog = _ref("animal", (15, 15, 15)), _ref("animal", (150, 140, 135))
    assert group_refs([black_dog, grey_dog]) == [[0], [1]]
    assert group_refs([grey_dog, _ref("animal", (155, 143, 138))]) == [[0, 1]]
    # same colours but a person and a dog are never the same replacement
    assert group_refs([_ref("person", (15, 15, 15)), black_dog]) == [[0], [1]]


def test_pairing_follows_appearance_not_just_size():
    refs = [_ref("animal", (150, 140, 135)), _ref("animal", (15, 15, 15))]  # grey dog, black dog
    subjects = [Subject(1, "person", 0.9, (0, 0, 10, 10), ""), Subject(2, "person", 0.9, (20, 0, 30, 10), "")]
    hists = {1: color_hist(_solid((20, 18, 18))), 2: color_hist(_solid((140, 120, 110)))}  # 1 black hair, 2 brown
    mappings, why = pair_groups([[0], [1]], refs, subjects, hists)
    assert dict(mappings) == {1: [1], 2: [0]}  # black dog -> black-haired subject
    assert "appearance" in why


def test_pairing_keeps_size_order_when_ambiguous():
    refs = [_ref("animal", (100, 100, 100)), _ref("animal", (101, 101, 101))]
    subjects = [Subject(1, "person", 0.9, (0, 0, 10, 10), ""), Subject(2, "person", 0.9, (20, 0, 30, 10), "")]
    same = color_hist(_solid((240, 10, 10)))
    mappings, why = pair_groups([[0], [1]], refs, subjects, {1: same, 2: same})
    assert mappings == [(1, [0]), (2, [1])] and "size order" in why
    assert np.isclose(sum(color_hist(_solid((1, 2, 3)))), 1.0)
