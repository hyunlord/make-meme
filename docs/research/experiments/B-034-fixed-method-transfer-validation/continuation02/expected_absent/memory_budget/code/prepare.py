# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# How to run: python prepare.py OLD_ROOT NEW_ROOT DEADLINE_EPOCH
"""Prepare a fresh attempt using existing frozen inputs, without GPU/model imports."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

old, root = (Path(value).resolve() for value in sys.argv[1:3])
deadline = float(sys.argv[3])
assert not root.exists(), 'Fresh root required; never overwrite attempts'
code = root/'code'
code.mkdir(parents=True)
source_code = Path(__file__).resolve().parent
for source in source_code.glob('*.py'):
    shutil.copyfile(source, code/source.name)
(root/'reports').mkdir()
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
summary = {}
for stage in ('STEP_S','STEP_D'):
    source = old/'stages'/stage
    folder = root/'stages'/stage
    for name in ('reports','configs','artifacts','outputs'):
        (folder/name).mkdir(parents=True)
    for name in ('upstream','models','experiment','inputs'):
        (folder/name).symlink_to((source/name).resolve())
    (folder/'code').symlink_to(code)
    (folder/'PREREGISTERED_INPUTS.json').symlink_to((source/'PREREGISTERED_INPUTS.json').resolve())
    for item in (source/'configs').glob('*.json'):
        shutil.copyfile(item,folder/'configs'/item.name)
    for item in (source/'artifacts').iterdir():
        if item.is_symlink():
            (folder/'artifacts'/item.name).symlink_to(item.resolve())
    cfg=json.loads((source/'config.json').read_text())
    cfg.update(unit='make-meme-b034-mb1-'+stage.lower().replace('_','-'),deadline_epoch=deadline,
               gpu_cutoff_utc='2026-10-28T05:08:00Z',hard_deadline_utc='2026-10-28T05:23:00Z',
               start_utc='2026-10-28T03:53:00Z',resume_attempt_id='MEMORY_BUDGET_01',
               memory_budget_state=str(root/'memory-budget-state.json'),
               step_latent=str(root/'stages/STEP_S/artifacts/final_latent.safetensors'))
    (folder/'config.json').write_text(json.dumps(cfg,indent=2))
    execution=json.loads((folder/'configs/execution.json').read_text())
    execution.update(deadline='2026-10-28T05:08:00Z',artifact_consumer='B034_MEMORY_BUDGET_01')
    (folder/'configs/execution.json').write_text(json.dumps(execution,indent=2))
    policy=json.loads((folder/'configs/service-policy.json').read_text())
    policy.update(stage_root=str(folder),deadline_epoch=deadline,resume_attempt_id='MEMORY_BUDGET_01',
                  authorization='User approved bounded memory amendment; fresh heavy1/decode1; historical failures unchanged')
    assert policy['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'Reboot invalidates inherited contract'
    (folder/'configs/service-policy.json').write_text(json.dumps(policy,indent=2))
    frozen=json.loads((source/'freeze.json').read_text())
    paths=[Path(name) for name in frozen['files'] if not Path(name).is_relative_to(old)]
    paths+=list(code.glob('*.py'))+list((folder/'configs').glob('*.json'))+[folder/'config.json']
    # Existing non-attempt inputs keep their expected hashes, rather than blessing changed input.
    for path in paths:
        if str(path) in frozen['files']:
            assert sha(path)==frozen['files'][str(path)],'Frozen input changed'
    frozen.update(experiment='B034_MEMORY_BUDGET_01',files={str(path):sha(path) for path in paths})
    for name in ('freeze.json','PREREGISTERED_CODE.json'):
        (folder/name).write_text(json.dumps(frozen,indent=2))
    summary[stage]={'freeze_sha256':sha(folder/'freeze.json'),'files':len(paths),
                    'historical_allowlist_equal':cfg['allowed_gpu_processes']==json.loads((source/'config.json').read_text())['allowed_gpu_processes']}
(root/'reports/layout.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary))
