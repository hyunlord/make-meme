"""CPU-only arithmetic and naming checks; not a live watchdog test."""
import pytest
from runtime_guard import GIB, UNIT, GuardBlocked, limits

def test_small_worker_cap() -> None:
    cap, seconds=limits(80*GIB,0,0,1800)
    assert cap==16*GIB and seconds==1740 and UNIT=='make-meme-b019-pipeline'

@pytest.mark.parametrize('available,swap',[(71*GIB,0),(80*GIB,1)])
def test_admission_failure(available: int, swap: int) -> None:
    with pytest.raises(GuardBlocked):limits(available,swap,0,1800)

def test_norm_cast_preserves_original_fp32() -> None:
    import torch
    from block_contract import runtime_dtype
    original=torch.tensor([1.000123,0.999879],dtype=torch.float32)
    for name in ['self_attn.norm_q.weight','norm3.bias','modulation']:
        actual=original.to(dtype=runtime_dtype(name))
        assert actual.dtype==torch.float32 and torch.equal(actual,original)
    assert runtime_dtype('q.weight')==torch.bfloat16
    assert not torch.equal(original.to(torch.bfloat16).float(),original)
