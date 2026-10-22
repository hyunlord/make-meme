"""Read-only B007A revalidation and separate Lab/official-example CPU staging.
Usage: python input_gate0.py B007A_ROOT PINNED_SCAIL_ROOT B007B_ROOT
"""
import hashlib,json,shutil,subprocess,sys
from pathlib import Path
from PIL import Image


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def probe(path: Path) -> dict:
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=avg_frame_rate,nb_read_frames,width,height,duration','-of','json',str(path)]))

old,upstream,root=map(Path,sys.argv[1:]);(root/'reports').mkdir(parents=True,exist_ok=True)
manifest=json.loads((old/'reports/input_preflight_artifacts.json').read_text())
for item in manifest['files']:assert sha(old/item['path'])==item['sha256'],item['path']
lab=root/'inputs/lab';lab.mkdir(parents=True,exist_ok=True);records=[]
for src,dst in [('reference-512x896.png','reference.png'),('reference-mask-512x896.png','reference-mask.png')]:
    source=old/'inputs/input_preflight'/src;target=lab/dst;shutil.copy2(source,target);assert sha(source)==sha(target)
    records.append({'alias':'lab/'+dst,'sha256':sha(target),'source_alias':'B007A/'+src})
for src,dst in [('prepared_driver','driver'),('prepared_mask_local_trim','mask')]:
    (lab/dst).mkdir(exist_ok=True)
    for i in range(17):
        source=old/'inputs/input_preflight'/src/f'{i:03d}.png';target=lab/dst/f'{i:03d}.png';shutil.copy2(source,target)
        assert sha(source)==sha(target) and Image.open(target).size==(512,896)
        records.append({'alias':str(target.relative_to(root/'inputs')),'sha256':sha(target),'source_alias':f'B007A/{src}/{i:03d}.png'})
for src,dst in [('prepared-rgb-24fps.mp4','driver-24fps.mp4'),('prepared-mask-local-trim-24fps.mp4','mask-24fps.mp4')]:
    source=old/'outputs/input_preflight'/src;target=lab/dst;shutil.copy2(source,target);assert sha(source)==sha(target)
    info=probe(target)['streams'][0];assert info['avg_frame_rate']=='24/1' and int(info['nb_read_frames'])==17
    records.append({'alias':'lab/'+dst,'sha256':sha(target),'probe':info})
revision='78fe19576bb06be96c2375e088574a262a300edb'
assert subprocess.check_output(['git','-C',str(upstream),'rev-parse','HEAD'],text=True).strip()==revision
code=root/'inputs/upstream-code';code.mkdir(parents=True,exist_ok=True)
for gitpath,name in [('generate.py','generate.py'),('wan/utils/utils.py','utils.py')]:
    blob=subprocess.check_output(['git','-C',str(upstream),'show',revision+':'+gitpath]);(code/name).write_bytes(blob)
example=root/'inputs/official-animation-001';example.mkdir(parents=True,exist_ok=True);official=[]
for name in ['ref.jpg','ref_mask.jpg','rendered_v2.mp4','rendered_mask_v2.mp4']:
    gitpath='examples/animation_001/'+name
    blob=subprocess.check_output(['git','-C',str(upstream),'show',revision+':'+gitpath]);assert len(blob)<10_000_000
    target=example/name;target.write_bytes(blob)
    official.append({'alias':name,'git_path':gitpath,'git_blob':subprocess.check_output(['git','-C',str(upstream),'rev-parse',revision+':'+gitpath],text=True).strip(),'bytes':len(blob),'sha256':sha(target)})
original_probes={name:probe(example/name) for name in ['rendered_v2.mp4','rendered_mask_v2.mp4']}
a,b=[original_probes[name]['streams'][0] for name in original_probes]
assert a['avg_frame_rate']==b['avg_frame_rate'] and min(int(a['nb_read_frames']),int(b['nb_read_frames']))>=17
assert (a['width'],a['height'])==(b['width'],b['height'])
# Preserve actual official timing, do not label a 16/25fps source as 24fps.
for filename,folder in [('rendered_v2.mp4','driver'),('rendered_mask_v2.mp4','mask')]:
    dest=example/folder;dest.mkdir(exist_ok=True)
    subprocess.run(['ffmpeg','-y','-v','error','-i',str(example/filename),'-frames:v','17','-fps_mode','passthrough','-start_number','0',str(dest/'%03d.png')],check=True,timeout=90)
    video=example/(folder+'-17frames.mp4')
    subprocess.run(['ffmpeg','-y','-v','error','-framerate',a['avg_frame_rate'],'-i',str(dest/'%03d.png'),'-frames:v','17','-fps_mode','passthrough','-c:v','libx264rgb','-crf','0','-pix_fmt','rgb24',str(video)],check=True,timeout=90)
    info=probe(video)['streams'][0];assert int(info['nb_read_frames'])==17 and info['avg_frame_rate']==a['avg_frame_rate']
    official.append({'alias':video.name,'sha256':sha(video),'probe':info,'method':'First17 decoded frames, no reordering/interpolation; lossless RGB encode at original FPS.'})
report={'status':'COMPLETED_CPU_INPUT_STAGING','prior_artifact_sha_checks':len(manifest['files']),'lab_files':records,'lab_geometry_hw':[896,512],'lab_mask_quality':'PARTIAL_UNRESOLVED: existing f0/f1 reflection/thin boundary residue preserved unchanged','lab_sample_times':'i/24;17/24 file duration;16/24 endpoint interval','official_revision':revision,'official_assets':official,'official_original_probes':original_probes,'official_visual_review':'PENDING','diffusion':'NOT_RUN'}
(root/'reports/input_gate0.json').write_text(json.dumps(report,indent=2)+'\n')
print('Input integrity and official source timing verified; static visual review pending.')
