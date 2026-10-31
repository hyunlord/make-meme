# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run: score.py <task> pair <framesA> <framesB> <frame_count> <out.json>
#      score.py <task> single <frames> <frame_count> <out.json>
"""Apply the fixed C-012 reader (evaluate.py) to saved 416x240 frame folders.

For frame_count N != 33 (external model) the sample for each pre-registered tau is the frame
i = round(tau*(N-1)) and the truth is evaluated at that frame's own tau = i/(N-1).
"""
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate import Reader, read_video, judge_pair, judge_single, load_rgb

TAUS = [k / 8 for k in range(9)]


def sample(folder: Path, n: int) -> tuple[list, list[float], list[int]]:
    idx = [round(t * (n - 1)) for t in TAUS]
    return [load_rgb(folder / f'{i:03d}.png') for i in idx], [i / (n - 1) for i in idx], idx


def main() -> None:
    task, mode = Path(sys.argv[1]), sys.argv[2]
    reader = Reader(task)
    if mode == 'pair':
        fa, fb, n, out = Path(sys.argv[3]), Path(sys.argv[4]), int(sys.argv[5]), Path(sys.argv[6])
        frames_a, taus, idx = sample(fa, n)
        frames_b, _, _ = sample(fb, n)
        rows_a, rows_b = read_video(reader, frames_a, taus), read_video(reader, frames_b, taus)
        result = {'frame_indices': idx, 'taus': taus, 'rows_A': rows_a, 'rows_B': rows_b, 'judge': judge_pair(rows_a, rows_b)}
    else:
        f, n, out = Path(sys.argv[3]), int(sys.argv[4]), Path(sys.argv[5])
        frames, taus, idx = sample(f, n)
        rows = read_video(reader, frames, taus)
        result = {'frame_indices': idx, 'taus': taus, 'rows': rows, 'judge': judge_single(rows)}
    out.write_text(json.dumps(result, indent=2, default=lambda o: o.item()))
    j = result['judge']
    print(json.dumps(default=lambda o: o.item(), obj={k: j[k] for k in j if k.startswith('c') or k.startswith('verdict')} if mode == 'pair' else
                     {'errors_vs_A': [None if e is None else round(e, 1) for e in j['errors_vs_A_px']],
                      'errors_vs_B': [None if e is None else round(e, 1) for e in j['errors_vs_B_px']], 'statuses': j['statuses']}))


if __name__ == '__main__':
    main()
