# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run: pinned-python -m pytest -q code/test_crossover.py
"""Small CPU tests of the exact two-leaf crossover boundary."""
import pytest
import torch


def test_only_clip_leaves_change() -> None:
    from crossover import crossed_values
    row = {f't{i}': torch.full((2,), float(i)) for i in range(16)}
    donor = {key: value + 1 for key, value in row.items()}
    before = {key: value.clone() for key, value in row.items()}
    result = crossed_values(row, donor)
    assert {key for key in row if not torch.equal(row[key], result[key])} == {'t2', 't8'}
    assert all(torch.equal(row[key], before[key]) for key in row)
    result['t2'].zero_()
    assert torch.equal(donor['t2'], torch.full((2,), 3.0))


def test_wrong_clip_shape_rejected() -> None:
    from crossover import crossed_values
    row = {f't{i}': torch.zeros(2) for i in range(16)}
    donor = {key: value.clone() for key, value in row.items()}
    donor['t2'] = torch.zeros(3)
    with pytest.raises(AssertionError):
        crossed_values(row, donor)
