# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run: imported by the CPU cache audit and encoder.
"""Six allowable reference leaves, with shape/dtype and other leaves fixed."""
from typing import Final, TypedDict


class TensorDigest(TypedDict):
    shape: list[int]
    dtype: str
    sha256: str


REFERENCE_KEYS: Final = frozenset(('t2', 't3', 't4', 't8', 't9', 't10'))


def changed_reference_leaves(
    original: dict[str, TensorDigest], derived: dict[str, TensorDigest]
) -> set[str]:
    """Accept new VAE/CLIP/mask values, never new tensor shapes or devices."""
    assert set(original) == set(derived) == {f't{i}' for i in range(16)}
    for key in original:
        assert original[key]['shape'] == derived[key]['shape'], key
        assert original[key]['dtype'] == derived[key]['dtype'], key
    changed = {key for key in original if original[key] != derived[key]}
    assert changed <= REFERENCE_KEYS, changed - REFERENCE_KEYS
    return changed
