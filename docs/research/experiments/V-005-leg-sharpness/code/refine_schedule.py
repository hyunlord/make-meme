"""CPU-only selection of existing frozen scheduler entries."""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class Selection:
    requested: float
    start_index: int
    sigmas: tuple[float, ...]

    @property
    def steps(self) -> int:
        return len(self.sigmas) - 1


def select_schedule(grid: Sequence[float], requested: float) -> Selection:
    """Choose nearest nonterminal grid entry; ties retain earlier/higher sigma."""
    values = tuple(float(value) for value in grid)
    if not 0 < requested <= 1 or len(values) < 2 or values[-1] != 0:
        raise ValueError('Invalid requested sigma or schedule termination')
    if any(not 0 <= value <= 1 for value in values) or any(a <= b for a, b in zip(values, values[1:])):
        raise ValueError('Schedule must strictly descend within [0, 1]')
    index = min(range(len(values)-1), key=lambda i: abs(values[i] - requested))
    return Selection(requested, index, values[index:])


def read_official_grids(engine: Path) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Read literals without importing torch, model code, or executing the module."""
    path = engine/'packages/ltx-pipelines/src/ltx_pipelines/utils/constants.py'
    names = ('DISTILLED_SIGMA_VALUES', 'STAGE_2_DISTILLED_SIGMA_VALUES')
    found = {}
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in names:
                    found[target.id] = tuple(float(v) for v in ast.literal_eval(node.value))
    return found[names[0]], found[names[1]]
