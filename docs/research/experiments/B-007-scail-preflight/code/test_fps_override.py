"""CPU mock of proposed writer expression, NOT a diffusion pipeline execution.
Future integration must also add parser.add_argument('--output_fps', type=int,
default=None) and reject nonpositive values. No upstream files are modified here.
"""
from pathlib import Path
from types import SimpleNamespace

patch=Path(__file__).with_name('future_fps_override.patch').read_text()
line=next(line for line in patch.splitlines() if line.startswith('+            fps='))
expression=line.split('fps=',1)[1].rstrip(',')
observed=[]
def cache_video_mock(**kwargs):
    observed.append(kwargs)

cfg=SimpleNamespace(sample_fps=16)
for explicit,expected in [(24,24),(None,16)]:
    args=SimpleNamespace(output_fps=explicit)
    value=eval(expression,{'__builtins__':{}},{'args':args,'cfg':cfg})
    cache_video_mock(tensor='17 original source frames; no generated tensor',fps=value)
    assert observed[-1]['fps']==expected
assert 17/24!=17/16
print('PASS CPU mock: explicit24 overrides default16; None preserves16. Diffusion writer NOT_RUN.')
