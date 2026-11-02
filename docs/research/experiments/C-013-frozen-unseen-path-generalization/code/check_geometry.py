# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run: python3 code/check_geometry.py /absolute/PATHS.json
"""Pure geometry boundary checks; these do not validate the image detector."""
from pathlib import Path
import json
import sys
from criteria import judge, trained


def main() -> None:
    paths = json.loads(Path(sys.argv[1]).read_text())['paths']
    for name, path in paths.items():
        target = path['center_xy_pixel_index']
        rows = [{'status': 'ok', 'center': p, 'peak': 1.0} for p in target]
        assert judge(rows, target, s_path=name == 'S')['full_path_quality_pass']
        for which in (0, 1):
            old = [{'status': 'ok', 'center': list(trained(t)[which]), 'peak': 1.0} for t in range(33)]
            assert not judge(old, target, s_path=name == 'S')['full_path_quality_pass']
        for status in ('missing', 'duplicate'):
            bad = [dict(row) for row in rows]
            bad[16] = {'status': status, 'center': None, 'peak': 0.0}
            assert not judge(bad, target, s_path=name == 'S')['position_pass']
        extra = [dict(row) for row in rows]
        extra[1] = {'status': 'missing', 'center': None, 'peak': 0.0}
        assert judge(extra, target, s_path=name == 'S')['position_pass']
        assert not judge(extra, target, s_path=name == 'S')['full_path_quality_pass']
        print(f'{name}: GEOMETRY_CONTRACT_PASS')


if __name__ == '__main__':
    main()
