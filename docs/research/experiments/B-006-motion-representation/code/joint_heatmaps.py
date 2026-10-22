"""CPU representation demo: manual visible points -> heatmaps, never pose estimation."""
from __future__ import annotations

from dataclasses import dataclass

import hashlib
import json
from pathlib import Path
import sys
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
import torch

JOINTS: Final = ('nose', 'left_eye', 'right_eye', 'neck', 'tail_base', 'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow', 'left_front_paw', 'right_front_paw', 'left_hip', 'right_hip', 'left_knee', 'right_knee', 'left_hind_paw', 'right_hind_paw')


class ObservationError(ValueError):
    """Manual annotation violates the visibility/coordinate contract."""


class Point(BaseModel):
    model_config = ConfigDict(frozen=True, extra='ignore')
    visibility: Literal['visible', 'occluded', 'unobservable']
    xy: tuple[float, float] | None
    uncertainty_px: float | None = None

    @model_validator(mode='after')
    def check_observation(self) -> Point:
        visible = self.visibility == 'visible'
        if visible != (self.xy is not None):
            raise ObservationError('Visible requires xy; nonvisible requires null xy')
        if visible:
            if self.uncertainty_px is None or self.uncertainty_px <= 0:
                raise ObservationError('Visible requires positive uncertainty')
            if self.xy is not None and not (0 <= self.xy[0] < 512 and 0 <= self.xy[1] < 288):
                raise ObservationError('Coordinates outside decoded canvas')
        elif self.uncertainty_px is not None:
            raise ObservationError('Nonvisible requires null uncertainty')
        return self


class Frame(BaseModel):
    model_config = ConfigDict(frozen=True, extra='ignore')
    frame: int = Field(ge=0, le=16)
    annotation_status: Literal['ANNOTATED', 'NOT_ANNOTATED']
    viewed_individually: bool = False
    landmarks: dict[str, Point]


class Annotation(BaseModel):
    model_config = ConfigDict(frozen=True, extra='ignore')
    frames: tuple[Frame, ...]


@dataclass(frozen=True, slots=True)
class Representation:
    heatmaps: torch.Tensor
    valid: torch.Tensor
    visibility: torch.Tensor


def render(annotation: Annotation, sigma_cells: float = 2.0) -> Representation:
    if sigma_cells <= 0:
        raise ObservationError('Gaussian sigma must be positive')
    indices = [frame.frame for frame in annotation.frames]
    if len(indices) != len(set(indices)):
        raise ObservationError('Duplicate frame indices')
    maps = torch.zeros((17, 17, 72, 128), dtype=torch.float32, device='cpu')
    valid = torch.zeros((17, 17), dtype=torch.bool)
    visibility = torch.full((17, 17), 3, dtype=torch.uint8)
    yy, xx = torch.meshgrid(torch.arange(72), torch.arange(128), indexing='ij')
    codes = {'visible': 0, 'occluded': 1, 'unobservable': 2}
    for frame in annotation.frames:
        if frame.annotation_status != 'ANNOTATED':
            if any(point.xy is not None for point in frame.landmarks.values()):
                raise ObservationError('NOT_ANNOTATED cannot contain coordinates')
            continue
        if not frame.viewed_individually or set(frame.landmarks) != set(JOINTS):
            raise ObservationError('Annotated frame needs individual review and all joint IDs')
        for j, name in enumerate(JOINTS):
            point = frame.landmarks[name]
            visibility[frame.frame, j] = codes[point.visibility]
            if point.xy is None:
                continue
            x, y = point.xy
            gaussian = torch.exp(-((xx - x / 512 * 128) ** 2 + (yy - y / 288 * 72) ** 2) / (2 * sigma_cells ** 2))
            maps[frame.frame, j] = gaussian / gaussian.max()
            valid[frame.frame, j] = True
    return Representation(maps, valid, visibility)


def main() -> None:
    source, output = Path(sys.argv[1]), Path(sys.argv[2])
    result = render(Annotation.model_validate_json(source.read_text()))
    output.mkdir(parents=True, exist_ok=False)
    tensors = {name: getattr(result, name) for name in Representation.__dataclass_fields__}
    torch.save(tensors, output / 'heatmaps.pt')
    report = {'scope': 'CPU manual-coordinate representation; not estimated pose or generated visual content', 'input_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'device': 'cpu', 'gaussian': 'peak-normalized, sigma2 heatmap cells; xy normalized by512x288; missing channels all-zero plus validity', 'visibility_codes': {'visible': 0, 'occluded': 1, 'unobservable': 2, 'not_annotated': 3}, 'valid_points': int(result.valid.sum()), 'tensors': {key: {'shape': list(value.shape), 'dtype': str(value.dtype), 'sha256': hashlib.sha256(value.contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()} for key, value in tensors.items()}}
    (output / 'report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))


if __name__ == '__main__':
    main()
