"""Reference-only RoPE H intervention; no learned state or tensor-content edit."""
from typing import Final

SIGNATURE: Final = '        additional_ref_masks: list[torch.Tensor]=None,\n'
SITE: Final = '        def apply_rope_scail(x):\n'


def resolve_reference_h(default: int, override: int | None, additional_count: int,
                        replace: bool, height: int, frequency_count: int) -> int:
    """None preserves mode defaults; explicit offsets require the fixed pilot scope."""
    if override is None:
        return default
    assert additional_count == 0 and replace is False
    assert override in (0, 120) and 0 <= override < frequency_count
    assert override + height <= frequency_count
    return override


def patch_source(source: str) -> str:
    """Fail closed unless the pinned forward signature and single RoPE site match."""
    assert source.count(SIGNATURE) == 1 and source.count(SITE) == 1
    assert 'reference_rope_h_shift' not in source
    source = source.replace(SIGNATURE, SIGNATURE + '        reference_rope_h_shift: int | None = None,\n')
    insertion = '''        from rope_h import resolve_reference_h
        kwargs["rope_H_shift"]["ref"] = resolve_reference_h(
            kwargs["rope_H_shift"]["ref"], reference_rope_h_shift,
            additional_ref_count, replace_flag, rope_h, self.freqs.shape[0])

'''
    source = source.replace(SITE, insertion + SITE)
    loop = '        for block in self.blocks:\n'
    assert source.count(loop) == 1
    observed = '''        for block_index, block in enumerate(self.blocks):
            if reference_rope_h_shift is not None:
                self._b016_observe(block_index, kwargs["rope_T_shift"],
                    kwargs["rope_H_shift"], kwargs["rope_W_shift"],
                    ref_length, seq_length, pose_length, rope_h, rope_w, rope_t)
'''
    return source.replace(loop, observed)
