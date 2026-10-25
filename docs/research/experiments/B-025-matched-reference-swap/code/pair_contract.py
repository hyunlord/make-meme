"""Allowed semantic reference package difference, never mandatory mask difference."""
from typing import Final, TypedDict

class TensorDigest(TypedDict):
    sha256: str

REFERENCE_KEYS: Final = frozenset(('t2','t3','t4','t8','t9','t10'))

def pair_changes(left:dict[str,TensorDigest],right:dict[str,TensorDigest])->set[str]:
    assert set(left)==set(right)=={f't{i}' for i in range(16)}
    changed={key for key in left if left[key]!=right[key]}
    assert changed <= REFERENCE_KEYS
    assert {'t2','t3','t8','t9'} <= changed
    return changed
