# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run using the existing pinned SCAIL environment; do not install dependencies.
"""CPU gates for a public-data pair; no model execution."""
from pathlib import Path


def test_public_contract_when_native_timebase_unknown():
    # Given the bounded public-data path, no inferred native FPS is permitted.
    path = Path(__file__).with_name('contracts.py')
    # When the implementation is loaded.
    assert path.exists(), 'public contract implementation not yet present'
    import contracts
    value = contracts.case_contract('public')
    # Then shape and preview timebase are the preregistered fixed contract.
    assert (value.width, value.height, value.fps) == (896, 512, 24)
    assert value.latent_shape == [16, 5, 64, 112]


def test_pair_allows_reference_mask_equality():
    # Given sixteen equal cached leaves and changed visual features only.
    import pair_contract
    left = {f't{i}': {'sha256': str(i)} for i in range(16)}
    right = {key: dict(value) for key, value in left.items()}
    right['t3']['sha256'] = 'different reference'
    # When semantic reference differences are checked.
    changed = pair_contract.pair_changes(left, right)
    # Then unchanged masks are accepted.
    assert changed == {'t3'}


def test_pair_rejects_noise_or_driving_change():
    # Given a modified driving leaf in an otherwise equal pair.
    import pair_contract
    import pytest
    left = {f't{i}': {'sha256': str(i)} for i in range(16)}
    right = {key: dict(value) for key, value in left.items()}
    right['t5']['sha256'] = 'changed driver'
    # When comparison runs, then the task is rejected before sampling.
    with pytest.raises(AssertionError):
        pair_contract.pair_changes(left, right)


def test_sampler_extraction_when_only_phase_boundaries_change():
    # Given the pinned extraction implementation reused from B-025.
    import hashlib
    here = Path(__file__).parent
    parent = here.parents[1]/'B-025-matched-reference-swap/code'
    # When the inherited core is compared byte-for-byte.
    names = ('extract.py', 'staged_loader.py', 'cuda_probe.py', 'phase_decode.py', 'artifacts.py')
    same = {name: hashlib.sha256((here/name).read_bytes()).digest() == hashlib.sha256((parent/name).read_bytes()).digest() for name in names}
    # Then the model arithmetic, decode and storage implementations are unchanged.
    assert all(same.values()), same
