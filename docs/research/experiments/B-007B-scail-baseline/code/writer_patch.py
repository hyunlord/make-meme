"""Produce an isolated explicit-FPS entrypoint, never modify the pinned source.
Usage: python writer_patch.py ORIGINAL_GENERATE_PY NEW_GENERATE_PY
"""
from pathlib import Path
import sys


def patch_writer(source: Path, destination: Path) -> None:
    """Require exact anchored changes and a separate output location."""
    assert source.resolve()!=destination.resolve()
    text=source.read_text()
    changes=[('    parser = argparse.ArgumentParser()','    parser = argparse.ArgumentParser()\n    parser.add_argument("--output_fps", type=int, default=None, help="Explicit output FPS; does not change frame count or learned motion prior.")'),
             ('def _validate_args(args):','def _validate_args(args):\n    if args.output_fps is not None and args.output_fps <= 0:\n        raise ValueError("output_fps must be positive")'),
             ('            fps=cfg.sample_fps,','            fps=(args.output_fps if args.output_fps is not None else cfg.sample_fps),')]
    for before,after in changes:
        assert text.count(before)==1,before
        text=text.replace(before,after,1)
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists():assert destination.read_text()==text
    else:destination.write_text(text)

if __name__=='__main__':patch_writer(Path(sys.argv[1]),Path(sys.argv[2]))
