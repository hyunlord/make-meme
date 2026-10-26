# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run: pinned-python -m pytest video_code/test_anchor_contract.py
"""CPU contract tests; no encoder, model, or CUDA imports."""
import copy
import pytest
from anchor_contract import changed_reference_leaves


def fixture():
    return {f't{i}': {'shape': [1], 'dtype': 'torch.float32', 'sha256': str(i)} for i in range(16)}


def test_reference_bundle_changes_only():
    # Given a complete sixteen-leaf source cache.
    original = fixture()
    derived = copy.deepcopy(original)
    for key in ('t2', 't3', 't4', 't8', 't9', 't10'):
        derived[key]['sha256'] += 'new'
    # When only the reference bundle changes.
    actual = changed_reference_leaves(original, derived)
    # Then all six are accepted, with no required change to driving/noise.
    assert actual == {'t2', 't3', 't4', 't8', 't9', 't10'}


def test_identical_support_mask_allowed():
    original = fixture()
    derived = copy.deepcopy(original)
    for key in ('t2', 't3', 't8', 't9'):
        derived[key]['sha256'] += 'new'
    assert changed_reference_leaves(original, derived) == {'t2', 't3', 't8', 't9'}


def test_driving_change_rejected():
    original = fixture()
    derived = copy.deepcopy(original)
    derived['t5']['sha256'] += 'wrong'
    with pytest.raises(AssertionError):
        changed_reference_leaves(original, derived)


def test_reference_dtype_change_rejected():
    original = fixture()
    derived = copy.deepcopy(original)
    derived['t3']['dtype'] = 'torch.bfloat16'
    with pytest.raises(AssertionError):
        changed_reference_leaves(original, derived)
