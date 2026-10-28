"""Explicit continuation consumers: unchanged STEP sampler and its single decode."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
from dataclasses import asdict
from bootstrap import bootstrap
root=Path(sys.argv[1]).resolve()
receipt=bootstrap(root)
from policy import load_policy
policy=load_policy(root)
if '--preflight-only' in sys.argv[2:]:
    from safety import observe,start_decision
    from memory import MemoryBudget
    cfg=json.loads((root/'config.json').read_text())
    live=observe(cfg['allowed_gpu_processes'],set(),False,policy)
    verdict=MemoryBudget().inspect(live['system_memory'],None,'BEFORE_CREATED',start=True,require_window=False)
    live['memory_verdict']=verdict
    if live['decision']=='CLEAR':live['decision']=verdict['decision']
    if live['available'] is not None and live['decision']=='CLEAR':
        live['decision']=start_decision(live['decision'],live['available']/2**30,cfg['deadline_epoch']-time.time())
    assert not live['service_policy']['research_worker_pids'],'DUPLICATE_RESEARCH_WORKER'
    assert live['decision']=='CLEAR',live
    assert 'torch' not in sys.modules and not any(name.startswith('wan') for name in sys.modules)
    print(json.dumps({'status':'PASS','policy_mode':policy['mode'],'live_safety':live,'bootstrap':asdict(receipt),'torch_imported':False,'model_imported':False,'loader_report_created':(root/'reports/loader.json').exists()}))
    raise SystemExit(0)
config=json.loads((root/'config.json').read_text());stage=config['stage']
(root/'reports/bootstrap.json').write_text(json.dumps(asdict(receipt),indent=2))
with (root/'reports/worker-attempt.json').open('x') as out:json.dump({'started':time.time(),'stage':stage,'pid':os.getpid()},out)
for path,digest in json.loads((root/'freeze.json').read_text())['files'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
assert json.loads((root/'reports/start-safety.json').read_text())['decision']=='CLEAR'
until=time.monotonic()+20
while not (root/'reports/worker-identity.json').exists():
    if time.monotonic()>until:raise RuntimeError('LIVE_IDENTITY_REGISTRATION_TIMEOUT')
    time.sleep(.1)
registered=json.loads((root/'reports/worker-identity.json').read_text());assert registered['pid']==os.getpid()
sys.path.insert(0,config['upstream']);sys.path.insert(0,config['video_code'])
import torch
from artifacts import load_tree,save_tree,atomic_json
from runtime_observe import initialize,phase
initialize(root/'reports/phases.jsonl')
if stage=='STEP_S':
    import phase_sample
    phase_sample.run(root,json.loads((root/'configs/public.json').read_text()))
    atomic_json(root/'reports/result.json',{'sampler':'PASS','finished':time.time()})
else:
    if stage=='STEP_D':
        tree,metadata=load_tree(Path(config['step_latent']),device='cpu');latent=tree['x0'][0]
        p=metadata['provenance'];assert p['method']=='STEP' and p['constraint_calls']==40 and p['counters']=={'model_calls':80,'completed_steps':40}
        assert p['history'] is None and not p['reference_prefix_included'] and not p['adapter_enabled']
    else:raise ValueError(stage)
    assert latent.dtype==torch.float32 and list(latent.shape)==[16,5,64,112] and bool(torch.isfinite(latent).all())
    from wan.modules.vae import WanVAE
    from wan.configs import SCAIL_CONFIGS
    from PIL import Image
    cfg=SCAIL_CONFIGS['SCAIL-14B'];checkpoint=Path(config['models'])/cfg.vae_checkpoint
    assert hashlib.sha256(checkpoint.read_bytes()).hexdigest()==config['vae_sha256']
    phase('vae_load_start');vae=WanVAE(vae_pth=str(checkpoint),device=torch.device('cuda:0'));phase('vae_load_complete')
    output=root/'outputs';output.mkdir(exist_ok=True)
    with (output/'decode-attempt.json').open('x') as out:json.dump({'decode':1,'stage':stage},out)
    phase('decode_start')
    with torch.no_grad(),torch.cuda.amp.autocast(dtype=cfg.param_dtype):raw=vae.decode([latent.to('cuda')])[0]
    torch.cuda.synchronize();phase('decode_complete')
    assert list(raw.shape)==[3,17,512,896] and bool(torch.isfinite(raw).all())
    raw=raw.cpu();torch.save(raw,output/'raw_output.pt');frames=output/'frames';frames.mkdir()
    pixels=((raw.float().clamp(-1,1)+1)*127.5).floor().to(torch.uint8).permute(1,2,3,0).numpy()
    for index,frame in enumerate(pixels):Image.fromarray(frame).save(frames/f'{index:03d}.png')
    phase('raw_and_png_saved')
    subprocess.run(['ffmpeg','-v','error','-framerate','24','-i',str(frames/'%03d.png'),'-vf','scale=in_range=full:out_range=tv:out_color_matrix=bt709,format=yuv420p','-c:v','libx264','-crf','18','-color_range','tv','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709',str(output/'output.mp4')],check=True)
    subprocess.run(['ffmpeg','-v','error','-i',str(output/'output.mp4'),'-f','null','-'],check=True)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(output/'output.mp4')]))['streams'][0]
    assert (int(probe['nb_frames']),probe['width'],probe['height'],probe['avg_frame_rate'])==(17,896,512,'24/1')
    phase('mp4_verified');atomic_json(root/'reports/result.json',{'decode':'PASS','shape':list(raw.shape),'dtype':str(raw.dtype),'finite':True,'probe':probe,'finished':time.time(),'stage':stage,'vae_decode':1,'source_decode':0})
phase('worker_complete')
