# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Imported by evaluate_paths.py; CPU-only.
"""Predeclared geometry criteria, independent of template detection."""
from typing import Final, TypedDict
import math

SAMPLES: Final = (0, 4, 8, 12, 16, 20, 24, 28, 32)
CORE: Final = (8, 12, 16, 20, 24)


class Detection(TypedDict):
    status: str
    center: list[float] | None
    peak: float


class Judgment(TypedDict):
    errors_px: list[float | None]
    identified_samples: int
    bad_frames: list[int]
    mean_observed_error_px: float | None
    core_mean_error_px: float | None
    midpoint_error_px: float | None
    endpoint_errors_px: list[float | None]
    E_req: float | None
    E_mem: float | None
    novel_margin_pass: bool
    position_pass: bool
    all33_single: bool
    full_path_quality_pass: bool
    interpretation: str
    s_events_pass: bool | None


def trained(t: int) -> tuple[tuple[float, float], tuple[float, float]]:
    tau = t / 32
    off = 0.0 if t in (0, 32) else 48 * math.sin(math.pi * tau) ** 2
    return (104 + 208 * tau, 120 - off), (104 + 208 * tau, 120 + off)


def judge(rows: list[Detection], target: list[list[float]], *, s_path: bool = False) -> Judgment:
    """Missing/duplicate rows never contribute zero error or pass a required frame."""
    assert len(rows) == len(target) == 33
    errors = [None if r['center'] is None or r['status'] != 'ok' else math.dist(r['center'], q) for r, q in zip(rows, target, strict=True)]
    observed = [errors[t] for t in SAMPLES if errors[t] is not None]
    central = [errors[t] for t in CORE if errors[t] is not None]
    mean = sum(observed) / len(observed) if observed else None
    req = sum(central) / 5 if len(central) == 5 else None
    memory = [min(math.dist(rows[t]['center'], p) for p in trained(t)) for t in CORE if rows[t]['center'] is not None and rows[t]['status'] == 'ok']
    mem = sum(memory) / 5 if len(memory) == 5 else None
    endpoints = [errors[0], errors[32]]
    required = all(errors[t] is not None for t in (0, *CORE, 32))
    position = required and len(observed) >= 8 and mean is not None and mean <= 11.2 and req is not None and req <= 8.4 and errors[16] <= 8.4 and all(e is not None and e <= 11.2 for e in endpoints)
    margin = req is not None and mem is not None and req + 4 <= mem
    events = None
    if s_path:
        events = required and all(rows[t]['center'][1] > 120 for t in (8, 12)) and all(rows[t]['center'][1] < 120 for t in (20, 24)) and errors[16] <= 8.4
    bad = [t for t, r in enumerate(rows) if r['status'] != 'ok']
    interpretation = 'NOVEL_PATH_FAILURE'
    if not required:
        interpretation = 'APPEARANCE_OR_DETECTION_LIMITED'
    elif position and margin and (events is not False):
        interpretation = 'REQUESTED_PATH_SUPPORTED'
    elif req is not None and mem is not None and mem < req:
        interpretation = 'TRAINED_PATH_ATTRACTION_OBSERVED'
    return {'errors_px': errors, 'identified_samples': len(observed), 'bad_frames': bad,
            'mean_observed_error_px': mean, 'core_mean_error_px': req, 'midpoint_error_px': errors[16],
            'endpoint_errors_px': endpoints, 'E_req': req, 'E_mem': mem, 'novel_margin_pass': margin,
            'position_pass': bool(position), 'all33_single': not bad,
            'full_path_quality_pass': bool(position and margin and not bad and events is not False),
            'interpretation': interpretation, 's_events_pass': events}
