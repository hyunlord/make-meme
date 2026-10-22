"""Small CPU fixture: no private images, manual coordinates or model weights."""
from copy import deepcopy
import json
from pathlib import Path
import sys

from pydantic import ValidationError
import torch
from joint_heatmaps import Annotation, JOINTS, ObservationError, render


def test_contract() -> None:
    points = {name: {'visibility': 'unobservable', 'xy': None, 'uncertainty_px': None} for name in JOINTS}
    points['nose'] = {'visibility': 'visible', 'xy': [256, 144], 'uncertainty_px': 2}
    fixture = {'frames': [{'frame': 0, 'annotation_status': 'ANNOTATED', 'viewed_individually': True, 'landmarks': points}]}
    result = render(Annotation.model_validate(fixture))
    assert list(result.heatmaps.shape) == [17, 17, 72, 128]
    assert result.heatmaps.device.type == 'cpu' and int(result.valid.sum()) == 1
    assert result.heatmaps[0, 0, 36, 64] == 1 and torch.count_nonzero(result.heatmaps[1:]) == 0
    assert torch.count_nonzero(result.heatmaps[0, 1:]) == 0
    assert result.visibility[0, 1] == 2 and torch.all(result.visibility[1:] == 3)
    bad = deepcopy(fixture)
    bad['frames'][0]['landmarks']['nose']['visibility'] = 'occluded'
    try:
        Annotation.model_validate(bad)
    except ValidationError:
        rejected = True
    else:
        rejected = False
    assert rejected, 'Nonvisible coordinate must fail'
    bad = deepcopy(fixture)
    bad['frames'][0]['annotation_status'] = 'NOT_ANNOTATED'
    try:
        render(Annotation.model_validate(bad))
    except ObservationError:
        rejected = True
    else:
        rejected = False
    assert rejected, 'Unannotated coordinate must fail'
    if len(sys.argv) == 2:
        Path(sys.argv[1]).write_text(json.dumps(fixture, indent=2))
    print('PASS: CPU shape, peak, missingness, visibility and contradictory annotation rejection. Toy contract only.')


if __name__ == '__main__':
    test_contract()
