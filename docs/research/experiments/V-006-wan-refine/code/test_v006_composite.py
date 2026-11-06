# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "pytest"]
# ///
"""Run with existing Python: python -m pytest test_v006_composite.py."""
import numpy as np
import v006_composite_core as core


def test_temporal_ramps_include_zero_endpoints() -> None:
    # Given a bounded replacement with two inclusive ramps.
    policy = core.BlendPolicy((2, 12), (2, 4), (10, 12), .45, 2, 2)
    # When the timeline is evaluated.
    weights = [core.temporal_weight(i, policy) for i in range(15)]
    # Then unchanged endpoints and an unattenuated interior are retained.
    assert weights == [0, 0, 0, .5, 1, 1, 1, 1, 1, 1, 1, .5, 0, 0, 0]


def test_local_feather_cannot_change_exterior_pixels() -> None:
    # Given a rectangular observed body and contrasting input/refinement.
    mask = np.zeros((40, 50), dtype=bool)
    mask[5:30, 12:30] = True
    base = np.full((40, 50, 3), 19, dtype=np.uint8)
    refined = np.full_like(base, 210)
    policy = core.BlendPolicy((2, 12), (2, 4), (10, 12), .45, 2, 2)
    # When a full-strength local derivative is composited.
    alpha = core.leg_alpha(mask, 6, policy)
    result = core.mix(base, refined, alpha)
    # Then the support is finite, feathered, and exterior is byte-identical.
    assert np.array_equal(result[alpha == 0], base[alpha == 0])
    assert np.array_equal(result[alpha == 1], refined[alpha == 1])
    assert np.any((alpha > 0) & (alpha < 1))
    assert not alpha[:15].any()


def test_missing_body_keeps_local_input_unchanged() -> None:
    # Given no detected real Lab mask.
    mask = np.zeros((20, 30), dtype=bool)
    policy = core.BlendPolicy((2, 12), (2, 4), (10, 12), .45, 2, 2)
    # When an in-window local alpha is requested.
    alpha = core.leg_alpha(mask, 6, policy)
    # Then there is no invented local region.
    assert not alpha.any()
