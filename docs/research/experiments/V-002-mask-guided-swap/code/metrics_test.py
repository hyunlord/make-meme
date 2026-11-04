"""CPU fixtures for V-002 silhouette scoring and preregistered selection."""
import numpy as np
from metrics_core import silhouette_score
from selection import Candidate, choose


def test_iou_exact_and_disjoint() -> None:
    # Given / When / Then: same and disjoint nonempty masks.
    source = np.array([[True, False], [False, False]])
    opposite = np.array([[False, True], [False, False]])
    assert silhouette_score(source, source) == (1.0, 1.0)
    assert silhouette_score(source, opposite) == (0.0, 0.0)


def test_missing_has_explicit_observation_gap() -> None:
    # Missing detection is not a perfect zero-error observation.
    source = np.array([[True, False]])
    assert silhouette_score(source, None) == (None, 0.0)


def test_selection_eligibility_and_tie() -> None:
    assert choose([Candidate('M1', 73, 66, .7), Candidate('M2', 73, 73, .72)]) == 'M1'
    assert choose([Candidate('M1', 73, 65, .9), Candidate('M2', 73, 66, .7)]) == 'M2'
    assert choose([Candidate('M1', 73, 73, .69), Candidate('M2', 73, 73, .72)]) == 'M2'
    assert choose([Candidate('M1', 73, 73, None), Candidate('M2', 73, 65, .8)]) is None
    assert choose([Candidate('M2', 73, 73, .7), Candidate('M3', 73, 73, .7)]) == 'M2'
    assert choose([Candidate('M1', 49, 49, .9)]) is None


if __name__ == '__main__':
    test_iou_exact_and_disjoint()
    test_missing_has_explicit_observation_gap()
    test_selection_eligibility_and_tie()
    print('3 V-002 CPU fixture groups PASS')
