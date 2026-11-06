"""CPU fixture boundaries for immutable metadata-only dataset records."""
import hashlib
import json
from pathlib import Path

import pytest
from build_sample import SampleError, publish


def test_hashes_readback_and_pending_review(tmp_path: Path) -> None:
    # Given an explicit small private asset and an attempted inferred review label.
    source = tmp_path/'asset.bin'
    source.write_bytes(b'original bytes')
    request = tmp_path/'manifest.json'
    request.write_text(json.dumps({'record_origin': 'BACKFILL', 'samples': [
        {'sample_id': 'fixture/run', 'outputs': {'raw': {'asset_path': str(source)}},
         'human_review': {'status': 'PASS'}}]}))
    # When a record is published, only metadata should be created.
    paths = publish(request, tmp_path/'dataset')
    record = json.loads(paths[0].read_text())
    # Then actual byte hash is retained and inferred acceptance is not propagated.
    assert record['outputs']['raw']['sha256'] == hashlib.sha256(b'original bytes').hexdigest()
    assert record['human_review']['status'] == 'PENDING'
    assert source.read_bytes() == b'original bytes'
    assert list((tmp_path/'dataset').rglob('*.*')) == paths
    with pytest.raises(SampleError, match='already exists'):
        publish(request, tmp_path/'dataset')


def test_bad_hash_prevents_any_publication(tmp_path: Path) -> None:
    # Given a manifest with a mismatched expected hash.
    source = tmp_path/'asset.bin'
    source.write_bytes(b'wrong bytes')
    request = tmp_path/'manifest.json'
    request.write_text(json.dumps({'record_origin': 'NEW', 'samples': [
        {'sample_id': 'fixture/run', 'raw': {'asset_path': str(source), 'expected_sha256': '0'*64}}]}))
    # When hydration validates the real bytes.
    with pytest.raises(SampleError, match='hash mismatch'):
        publish(request, tmp_path/'dataset')
    # Then it fails before publishing a successful sample.
    assert not (tmp_path/'dataset').exists()
