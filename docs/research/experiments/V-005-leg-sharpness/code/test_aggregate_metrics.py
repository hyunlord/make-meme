"""Evidence boundary fixtures for missing, incomplete and private artifacts."""
import json
import pytest
from aggregate_metrics import collect


def test_unavailable_stays_explicit(tmp_path):
    # Given a pending artifact that does not exist.
    spec={'status':'PENDING','leg':str(tmp_path/'absent.json')}
    # When collected without claiming success.
    result=collect(spec,2)
    # Then unavailability stays explicit, without synthesized values.
    assert result['evidence']['leg']['status']=='UNAVAILABLE'
    assert 'leg' not in result


def test_measured_requires_actual_complete_frames(tmp_path):
    # Given a real but duplicate-frame artifact.
    path=tmp_path/'leg.json';path.write_text(json.dumps({'frames':[{'frame':0},{'frame':0}]}))
    # When a measured claim is requested, then it is rejected.
    with pytest.raises(ValueError,match='Incomplete or duplicate'):
        collect({'status':'MEASURED','required':['leg'],'leg':str(path)},2)


def test_private_paths_are_not_silently_published(tmp_path):
    # Given a private path inside an otherwise valid report.
    path=tmp_path/'private.json';path.write_text(json.dumps({'frames':[{'frame':0}],'secret_path':'/home/example/raw.png'}))
    # When collecting into public metrics, then the leak is blocked.
    with pytest.raises(ValueError,match='Private path'):
        collect({'status':'MEASURED','leg':str(path)},1)
