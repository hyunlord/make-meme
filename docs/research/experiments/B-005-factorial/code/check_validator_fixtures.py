"""Isolated in-memory fixtures execute the actual factorial check block, no GPU/data edits."""
from pathlib import Path
from copy import deepcopy
import json
root=Path(__file__).resolve().parents[1]
source=(root/'reports/validate_runs.py').read_text()
block=source[source.index('factorial = {}'):source.index('result["factorial_controls"]')]
base=Path('/fixture/B003');run=Path('/fixture/B005')
def row(ref,condition,seed):
 return {'tensors':{key:{'sha256':value} for key,value in {'shared.noise':str(seed),'positive.context':'pos','negative.context':'neg','shared.vace_context':ref+condition}.items()},'slices':{key:{'sha256':value} for key,value in {'reference_prefix':ref,'video_reactive':condition,'video_inactive':'inactive','mask_all':'mask'}.items()}}
data={}
for seed in (20261022,20261023):
 for cell,path in [('bg-real',base/'outputs'/f'C-real-{seed}'),('bg-null',base/'outputs'/f'C-null-{seed}'),('gray-real',base.parent/'B-004-reference-neutral'/'outputs'/f'R-gray-{seed}'),('gray-null',run/'outputs'/f'R-gray-C-null-{seed}')]:
  ref,condition=cell.split('-');data[str(path/'actual_input_hashes.jsonl')]=[row(ref,condition,seed)]
def check(fixture):
 ns={'baseline':base,'root':run,'rows':lambda p:fixture.get(str(p),[]),'sha':lambda p:'fixture'}
 exec(compile(block,'actual-factorial-block','exec'),ns)
 return ns['factorial']
results={};positive=check(data);results['positive_expected_pass']=all(x['pass'] for x in positive.values())
key=str(run/'outputs/R-gray-C-null-20261022/actual_input_hashes.jsonl')
for name,group,field in [('noise','tensors','shared.noise'),('reference','slices','reference_prefix'),('reactive','slices','video_reactive')]:
 altered=deepcopy(data);altered[key][0][group][field]['sha256']='mismatch'
 evaluated=check(altered);results[name+'_mismatch_detected']=not evaluated['20261022']['pass'] and evaluated['20261023']['pass']
report={'scope':'Synthetic validator wiring only, not inference or visual quality. Exact factorial block extracted from reports/validate_runs.py. No actual assets/records changed.','checks':results,'all_pass':all(results.values())}
(root/'reports/validator_fixture_results.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));assert report['all_pass']
