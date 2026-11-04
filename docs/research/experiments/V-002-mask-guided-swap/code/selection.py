# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run: existing Python selection.py /private/metric-paths.json /public/selection.json
"""V-002's frozen eligibility and IoU selection, without human-quality claims."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal
import json
import math
import sys

Variant = Literal['M1', 'M2', 'M3']
ORDER: Final = ('M1', 'M2', 'M3')


@dataclass(frozen=True, slots=True)
class Candidate:
    variant: Variant
    frames: int
    actual_two_frames: int
    mean_iou: float | None

    @property
    def eligible(self) -> bool:
        return self.frames == 73 and self.actual_two_frames >= 66 and self.mean_iou is not None


def choose(candidates: list[Candidate]) -> Variant | None:
    """M1 preference never overrides eligibility or the 0.02 proximity rule."""
    eligible = [row for row in candidates if row.eligible]
    if not eligible:
        return None
    eligible.sort(key=lambda row: (-(row.mean_iou or 0), ORDER.index(row.variant)))
    best = eligible[0]
    assert best.mean_iou is not None
    m1 = next((row for row in eligible if row.variant == 'M1'), None)
    if m1 is not None and m1.mean_iou is not None:
        difference = best.mean_iou - m1.mean_iou
        if difference < .02 or math.isclose(difference, .02, abs_tol=1e-12):
            return 'M1'
    return best.variant


def main() -> None:
    config_path, destination = map(Path, sys.argv[1:])
    config = json.loads(config_path.read_text())
    candidates: list[Candidate] = []
    evidence = {}
    for variant in ORDER:
        path = config.get(variant)
        if path is None:
            evidence[variant] = {'status': 'NOT_MEASURED', 'eligible': False}
            continue
        report = json.loads(Path(path).read_text())
        score = report['silhouette_iou']['all_frame_mean_lab_ig']
        candidate = Candidate(variant, report['frame_count'], report['actual_two_frames'], score)
        candidates.append(candidate)
        evidence[variant] = {'status': report['status'], 'frames': candidate.frames,
                             'actual_two_frames': candidate.actual_two_frames,
                             'mean_iou': score, 'eligible': candidate.eligible}
    selected = choose(candidates)
    result = {'status': 'SELECTED' if selected else 'NO_14B_CANDIDATE',
              'selected': selected, 'candidates': evidence,
              'criterion': 'All-frame mean of Lab/IG silhouette IoU; missing detections explicitly contribute zero after cast establishment.',
              'tie_rule': 'Eligible M1 within 0.02 of best; otherwise highest eligible score, exact M2/M3 tie resolves M2.',
              'quality': 'HUMAN_REVIEW_PENDING'}
    temporary = destination.with_suffix('.partial')
    temporary.write_text(json.dumps(result, indent=2)+'\n')
    temporary.replace(destination)
    assert json.loads(destination.read_text()) == result
    print(json.dumps(result))


if __name__ == '__main__':
    main()
