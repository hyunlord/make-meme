"""CPU-only fresh continuation layout; preserve all prior stages and producer receipts."""
from pathlib import Path
import datetime,hashlib,json,shutil,sys
parent=Path(sys.argv[1]).resolve();code=Path(sys.argv[2]).resolve();root=parent/'continuation/CONTINUATION_01';task=parent/'tasks/rigid_R1'
assert not (root/'stages').exists(),'Existing continuation stages: do not duplicate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
support=root/'support';assert sha(support/'MASK_FREEZE.json')=='3fb5ad5396fd696354259eeb94f1f247ecf31706d92aaeba7e58e055e95478de'
assert sha(support/'inputs/mask_latent.safetensors')=='faf6e317a383a59bf50a42627c340a5d243cc1f85bab8c41a4b50a1196b64bab'
assert sha(parent/'video_code/clean_constraint.py')=='7c24c3c14d39e07ea77f01fd45ffe13c051e1c7ef14be77f8329348ed120aebb'
old=json.loads((parent/'recovery/RECOVERY_01/config.json').read_text())
for stage in ('CONTROL_D','STEP_S','STEP_D'):
    folder=root/'stages'/stage
    for name in ('reports','configs','artifacts','inputs','outputs'):(folder/name).mkdir(parents=True)
    for name,target in [('code',code),('upstream',Path(old['upstream'])),('models',Path(old['models'])),('experiment',task)]: (folder/name).symlink_to(target)
    for item in (task/'inputs').iterdir():(folder/'inputs'/item.name).symlink_to(item)
    for name in ('edit_px.npy','mask_latent.safetensors'):
        target=folder/'inputs'/name
        if target.is_symlink():target.unlink()
        target.symlink_to(support/'inputs'/name)
    for item in (task/'configs').glob('*.json'):shutil.copyfile(item,folder/'configs'/item.name)
    execution=json.loads((task/'stages/STEP_S/configs/execution.json').read_text());execution.update(stage=stage,method='STEP' if stage.startswith('STEP') else 'FINAL_ONLY',predecessor=None,deadline='2026-10-27T09:46:43Z',artifact_consumer='B034_CONTINUATION_01')
    (folder/'configs/execution.json').write_text(json.dumps(execution,indent=2))
    for name in ('conditions.safetensors','conditions.json','conditions_receipt.json','initial_noise.pt','source_latent.safetensors','source_latent.json'):(folder/'artifacts'/name).symlink_to(task/'shared'/name)
    cfg={**old,'stage':stage,'unit':'make-meme-b034-cont01-'+stage.lower().replace('_','-'),'deadline_epoch':datetime.datetime.fromisoformat('2026-10-27T09:46:43+00:00').timestamp(),'worker_max_seconds':4800 if stage=='STEP_S' else 600,'video_code':str(parent/'video_code'),'source_latent':str(task/'shared/source_latent.safetensors'),'mask_latent':str(support/'inputs/mask_latent.safetensors'),'step_latent':str(root/'stages/STEP_S/artifacts/final_latent.safetensors')}
    (folder/'config.json').write_text(json.dumps(cfg,indent=2))
    (folder/'PREREGISTERED_INPUTS.json').symlink_to(task/'PREREGISTERED_INPUTS.json')
    paths=list(code.glob('*.py'))+list((parent/'video_code').glob('*.py'))+list((folder/'configs').glob('*.json'))+[folder/'config.json',support/'MASK_FREEZE.json',support/'inputs/mask_latent.safetensors',task/'PREREGISTERED_CODE.json',task/'ENC_FREEZE.json']
    for name in ('conditions.safetensors','conditions.json','conditions_receipt.json','initial_noise.pt','source_latent.safetensors','source_latent.json'):paths.append(task/'shared'/name)
    for name in ('wan/scail.py','wan/modules/vae.py','wan/modules/model_scail2.py','wan/utils/fm_solvers_unipc.py'):paths.append(Path(old['upstream'])/name)
    freeze={'experiment':'B034_CONTINUATION_01','files':{str(p):sha(p) for p in paths},'original_producer':sha(task/'PREREGISTERED_CODE.json'),'budget':{'samplers':1,'control_decode':1,'step_decode':1,'source_decode':0,'base_decode':0}}
    (folder/'freeze.json').write_text(json.dumps(freeze,indent=2));(folder/'PREREGISTERED_CODE.json').write_text(json.dumps(freeze,indent=2))
print(json.dumps({'root':str(root),'stages':['CONTROL_D','STEP_S','STEP_D']}))
