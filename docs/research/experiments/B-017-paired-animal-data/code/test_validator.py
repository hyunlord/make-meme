"""Synthetic fixtures test validator mechanics only, never animal data quality."""
import subprocess
from pathlib import Path

import pytest
from case_schema import Asset, Case, Evidence, Manifest, Masks, Rights
from pydantic import ValidationError
from validate_cases import temporal_overlap, validate_manifest


@pytest.fixture
def clip(tmp_path: Path) -> Asset:
    path = tmp_path / 'synthetic.mkv'
    _ = subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                    'testsrc=size=32x24:rate=24', '-frames:v', '3',
                    '-c:v', 'ffv1', str(path)], check=True)
    return Asset(path=path, kind='VIDEO', width=32, height=24, frames=3,
                 fps=24, timestamps=(0, .042, .083), source_id='fixture',
                 session_id='fixture-session', source_fps=24,
                 frame_indices=(0, 1, 2), identity_id='fixture-id', origin='GENERATED')


def make_case(clip: Asset, name: str = 'fixture') -> Case:
    return Case(sample_id=name, pair_type='SELF_RECON_SMOKE', D=clip, Y=clip,
                origin_group='fixture-group', split='DEVELOPMENT', mode='ANIMATION',
                caption='Synthetic fixture; not actual animal data')


def test_missing_and_synthetic(clip: Asset) -> None:
    result = validate_manifest(Manifest(cases=(make_case(clip),)))
    case = result.cases[0]
    assert 'R' in case.missing_fields and 'masks.D' in case.missing_fields
    assert case.d_equals_y_decoded is True
    assert case.training_ready is False
    assert 'GENERATED_TARGET_EXCLUDED' in case.blockers


def test_wrong_metadata(clip: Asset) -> None:
    broken = clip.model_copy(update={'width': 33})
    result = validate_manifest(Manifest(cases=(make_case(broken),)))
    assert result.cases[0].media['D'].status == 'FAIL'


def test_schema_rejects_duplicate_source_indices(clip: Asset) -> None:
    payload = clip.model_dump()
    payload['frame_indices'] = [0, 0, 2]
    with pytest.raises(ValidationError):
        _ = Asset.model_validate(payload)


def test_cross_split_same_source(clip: Asset) -> None:
    one = make_case(clip)
    two = make_case(clip, 'second').model_copy(update={'split': 'TEST'})
    result = validate_manifest(Manifest(cases=(one, two)))
    assert any('SOURCE_CROSS_SPLIT' in flag for flag in result.leakage_flags)
    assert any('TEMPORAL_OVERLAP' in flag for flag in result.leakage_flags)


def test_different_ids_do_not_prove_cross_motion(clip: Asset) -> None:
    image = clip.path.parent / 'first.png'
    _ = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(clip.path), '-frames:v', '1',
                    str(image)], check=True)
    ref = clip.model_copy(update={'path': image, 'kind': 'IMAGE', 'frames': 1,
                                 'timestamps': (0,), 'frame_indices': (0,)})
    case = make_case(clip).model_copy(update={
        'R': ref, 'D': clip.model_copy(update={'identity_id': 'other'}),
        'masks': Masks(R=ref, D=clip), 'pair_type': 'CROSS_ID_MOTION_PAIR',
        'identity_evidence': Evidence(status='CONFIRMED', basis='fixture only'),
        'rights': Rights(training='ALLOWED'),
    })
    out = validate_manifest(Manifest(cases=(case,))).cases[0]
    assert out.r_equals_y_first_decoded is True
    assert 'MOTION_CORRESPONDENCE_UNCONFIRMED' in out.blockers
    assert out.pair_available is False


def test_sparse_source_and_bad_pts(clip: Asset) -> None:
    bad = clip.model_copy(update={'frame_indices': (0, 2, 4)})
    out = validate_manifest(Manifest(cases=(make_case(bad),))).cases[0]
    assert 'SOURCE_TIME_RESAMPLED_OR_MISDECLARED' in out.media['D'].errors
    wrong_pts = clip.model_copy(update={'timestamps': (0, .1, .2)})
    out = validate_manifest(Manifest(cases=(make_case(wrong_pts),))).cases[0]
    assert 'ENCODED_TIMESTAMPS_MISMATCH' in out.media['D'].errors


def test_unknown_rights_missing_target_caption(clip: Asset) -> None:
    case = make_case(clip).model_copy(update={'Y': None, 'caption': ''})
    out = validate_manifest(Manifest(cases=(case,))).cases[0]
    assert {'Y', 'caption', 'masks.R', 'masks.D'}.issubset(out.missing_fields)
    assert 'RIGHTS_PENDING' in out.readiness
    assert out.training_ready is False


def test_case_limit_and_duplicate_ids(clip: Asset) -> None:
    with pytest.raises(ValidationError):
        _ = Manifest(cases=tuple(make_case(clip, f'c{i}') for i in range(9)))
    with pytest.raises(ValidationError):
        _ = Manifest(cases=(make_case(clip), make_case(clip)))


def test_mask_geometry_and_identity_rejected(clip: Asset) -> None:
    case = make_case(clip).model_copy(update={'masks': Masks(D=clip.model_copy(update={'width': 33}))})
    out = validate_manifest(Manifest(cases=(case,))).cases[0]
    assert 'MASK_D_SPATIAL_TEMPORAL_MISMATCH' in out.blockers
    case = make_case(clip).model_copy(update={
        'R': clip.model_copy(update={'identity_id': 'other'}),
        'identity_evidence': Evidence(status='CONFIRMED', basis='deliberately contradictory fixture'),
    })
    out = validate_manifest(Manifest(cases=(case,))).cases[0]
    assert 'R_Y_IDENTITY_MISMATCH_OR_UNKNOWN' in out.blockers


def test_missing_file_and_nonfinite_metadata(clip: Asset) -> None:
    bad = clip.model_copy(update={'path': clip.path.parent / 'absent.mp4'})
    out = validate_manifest(Manifest(cases=(make_case(bad),))).cases[0]
    assert out.media['Y'].status == 'FAIL'
    payload = clip.model_dump()
    payload['fps'] = float('nan')
    with pytest.raises(ValidationError):
        _ = Asset.model_validate(payload)


def test_reference_within_vs_outside_target(clip: Asset) -> None:
    inside = clip.model_copy(update={'frame_indices': (1,), 'frames': 1})
    outside = clip.model_copy(update={'frame_indices': (10,), 'frames': 1})
    assert temporal_overlap(inside, clip) is True
    assert temporal_overlap(outside, clip) is False
    assert temporal_overlap(None, clip) is None
