# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib", "pydantic>=2"]
# ///
# How to run: python build_loss_curves.py B022_PRIVATE_ROOT
"""Plot recorded scalar FM losses only; never evaluate or load a model."""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Final, Literal

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pydantic import BaseModel, ConfigDict, RootModel

TUPLES: Final = ('train_0', 'train_1', 'train_2', 'holdout')
SIGMAS: Final = (0.2, 0.5, 0.8, 0.65)
STEPS: Final = (20, 50, 100)
TupleId = Literal['train_0', 'train_1', 'train_2', 'holdout']


class LossRow(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)
    loss: float


class TrainRow(LossRow):
    update: int
    tuple_id: TupleId


class Progress(BaseModel):
    model_config = ConfigDict(frozen=True)
    updates: tuple[TrainRow, ...]
    tail_evaluations: int


class Snapshots(RootModel[dict[str, dict[TupleId, LossRow]]]):
    model_config = ConfigDict(frozen=True)


def sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(root: Path) -> None:
    snapshot_path = root / 'stages/TRAIN/reports/evaluation-snapshots.json'
    progress_path = root / 'stages/TRAIN/reports/train-progress.json'
    snapshots = Snapshots.model_validate_json(snapshot_path.read_text()).root
    progress = Progress.model_validate_json(progress_path.read_text())
    observed_steps = tuple(sorted(int(step) for step in snapshots))
    assert observed_steps and all(step in STEPS for step in observed_steps)
    assert observed_steps[0] == 20, 'The matched checkpoint starts at20'
    assert all(set(row) == set(TUPLES) for row in snapshots.values())
    assert len(progress.updates) <= 80
    for index, row in enumerate(progress.updates):
        assert row.update == index + 21 and row.tuple_id == TUPLES[(row.update - 1) % 3]
    completed = 20 + len(progress.updates)
    assert max(observed_steps) <= completed
    output = root / 'reports/loss-curves'
    output.mkdir(parents=True, exist_ok=False)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    for index, tuple_id in enumerate(TUPLES):
        axis = axes.flat[index]
        values = [snapshots[str(step)][tuple_id].loss for step in observed_steps]
        axis.plot(observed_steps, values, 'o-', label='B022 same-checkpoint evaluation')
        axis.set(title=f'{tuple_id}: sigma={SIGMAS[index]}', xlabel='Optimizer update',
                 ylabel='FP32 velocity MSE', xticks=STEPS, xlim=(17, 103))
        if completed < 100:
            axis.axvspan(completed + 1, 100, alpha=0.08, color='gray')
            axis.text(0.55, 0.75, f'After update{completed}: NOT_RUN', transform=axis.transAxes)
        axis.ticklabel_format(axis='y', style='plain', useOffset=False)
        axis.grid(alpha=0.3)
        axis.legend(fontsize=8)
    fig.suptitle('Same-clip fixed FM tuples; independent y axes; not video quality')
    fig.savefig(output / 'evaluation-by-tuple.png', dpi=150)
    fig.savefig(output / 'evaluation-by-tuple.svg')
    plt.close(fig)
    fig, axes = plt.subplots(3, 1, figsize=(12, 9), constrained_layout=True)
    for index, tuple_id in enumerate(TUPLES[:3]):
        rows = [row for row in progress.updates if row.tuple_id == tuple_id]
        axes[index].plot([row.update for row in rows], [row.loss for row in rows], '.-')
        axes[index].set(title=f'{tuple_id}: sigma={SIGMAS[index]}, n={len(rows)}',
                        xlabel='Update whose pre-step loss was recorded', ylabel='FP32 MSE')
        axes[index].ticklabel_format(axis='y', style='plain', useOffset=False)
        axes[index].grid(alpha=0.3)
    fig.suptitle(f'Tuple-separated losses: {completed} updates completed, {len(progress.updates)} pre-step rows recorded'
                 + '; B021 update1..20 rows not synthesized')
    fig.savefig(output / 'training-by-tuple.png', dpi=150)
    fig.savefig(output / 'training-by-tuple.svg')
    plt.close(fig)
    with (output / 'evaluation-by-tuple.csv').open('w', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(['tuple_id', 'sigma', 'update', 'B022_MSE', 'status'])
        for index, tuple_id in enumerate(TUPLES):
            for step in STEPS:
                writer.writerow([tuple_id, SIGMAS[index], step,
                                 snapshots[str(step)][tuple_id].loss if step in observed_steps else '',
                                 'OBSERVED' if step in observed_steps else 'NOT_RUN'])
    with (output / 'training-by-tuple.csv').open('w', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(['update', 'tuple_id', 'pre_step_MSE'])
        writer.writerows((r.update, r.tuple_id, r.loss) for r in progress.updates)
    provenance = {
        'scope': 'Recorded scalar losses; no extra model forward, no quality claim',
        'same_clip_holdout_not_independent_video': True,
        'planned_evaluation_updates': STEPS,
        'observed_evaluation_updates': observed_steps,
        'actual_completed_updates': completed,
        'recorded_pre_step_rows': len(progress.updates),
        'missing_pre_step_rows': [],
        'historical_b021_update20_scalar_gap': 'Preserved; no past row invented',
        'new_updates': len(progress.updates),
        'actual_tuple_exposures': [sum((i - 1) % 3 == j for i in range(21, completed + 1)) for j in range(3)],
        'recorded_tuple_rows': [sum(r.tuple_id == k for r in progress.updates) for k in TUPLES[:3]],
        'y_axes': 'Independent per tuple; magnification is not quality improvement',
        'inputs': [{'path': str(p), 'sha256': sha256(p)}
                   for p in (snapshot_path, progress_path)],
        'outputs': [{'name': p.name, 'sha256': sha256(p)}
                    for p in sorted(output.iterdir()) if p.is_file()],
    }
    (output / 'manifest.json').write_text(json.dumps(provenance, indent=2) + '\n')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: build_loss_curves.py B022_PRIVATE_ROOT')
    run(Path(sys.argv[1]))
