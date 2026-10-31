# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow", "pydantic", "numpy"]
# ///
"""White masks pass the three-channel contract; the legacy red mask fails it but passes a channel-0-only check."""
from pathlib import Path
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rebuild_cache import check_mask_contract, white_masks


def legacy_masks() -> list[Image.Image]:
    return [Image.new('RGB', (416, 240), 0 if t in (0, 32) else 255) for t in range(33)]


def test_white_passes() -> None:
    assert check_mask_contract(white_masks())['rgb_equal']


def test_legacy_red_fails_three_channel_check() -> None:
    try:
        check_mask_contract(legacy_masks())
    except AssertionError:
        return
    raise AssertionError('legacy red mask passed the contract')


def test_channel0_only_check_cannot_see_the_bug() -> None:
    legacy = np.stack([np.asarray(m) for m in legacy_masks()])
    white = np.stack([np.asarray(m) for m in white_masks()])
    assert np.array_equal(legacy[..., 0], white[..., 0])
    assert not np.array_equal(legacy, white)


if __name__ == '__main__':
    test_white_passes()
    test_legacy_red_fails_three_channel_check()
    test_channel0_only_check_cannot_see_the_bug()
    print('PASS')
