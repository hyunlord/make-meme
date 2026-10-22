"""Guard arithmetic fixture: no process launch or checkpoint load."""
import pytest
from runtime_guard import limits, GuardBlocked

def test_headroom_and_cap():
    # Given fresh90GiB andzero swap; when calculating; then64GiB cap.
    assert limits(90*1024**3, 0, 1000, 5000) == (64*1024**3, 3940)

def test_swap_blocks():
    # Given nonzeroswap; when calculating; then failclosed.
    with pytest.raises(GuardBlocked):
        limits(90*1024**3, 1, 1000, 5000)

def test_deadline_blocks():
    with pytest.raises(GuardBlocked):
        limits(90*1024**3, 0, 5000, 5000)
