"""Regression fixture from actual saved S3 receipts; CPU stdlib only.

python3 test_postprocess_offset_fixture.py [private-process-output.py]
Optional path tests the exact assertions extracted without importing the worker.
"""
import ast
import json
from pathlib import Path
import sys


def main() -> None:
    evidence = json.loads(Path(__file__).with_name('POSTPROCESS_OFFSET_FIX.json').read_text())
    rows = evidence['fixture_rows']
    old_failed = sum(row['recorded_offset'] != row['source_frame']*row['multiplier']-row['native_target_frame'] for row in rows)
    assert old_failed == 10
    if len(sys.argv) > 1:
        tree = ast.parse(Path(sys.argv[1]).read_text())
        checks = [node for node in ast.walk(tree) if isinstance(node, ast.Assert) and
                  ("image['offset']" in ast.unparse(node) or 'target_frame == source_frame * multiplier' in ast.unparse(node))]
        assert len(checks) == 2
        compiled = compile(ast.Module(body=checks, type_ignores=[]), 'checker', 'exec')
    else:
        compiled = compile('\n'.join(evidence['after_assertions']), 'recorded-fix', 'exec')
    for row in rows:
        values = {'image': {'offset': row['recorded_offset']}, 'source_frame': row['source_frame'],
                  'target_frame': row['native_target_frame'], 'multiplier': row['multiplier']}
        exec(compiled, values)
        try:
            exec(compiled, dict(values, target_frame=values['target_frame']+1))
        except AssertionError:
            pass
        else:
            raise AssertionError('Incorrect target was accepted')
    print(f'PASS: {len(rows)} actual mapping rows, {len(rows)} invalid targets rejected; old checker fails {old_failed}')


if __name__ == '__main__':
    main()
