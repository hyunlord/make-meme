# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""CPU-only orchestration: process_output.py PRIVATE_RUNTIME.json [--check-only].

Runtime has explicit scene, metrics_scene, parent_code, source_frames/summary,
raw_frames, output_summary, raw_mp4, output_dir, reports_dir, name, frame_count,
fps, native_size, generation_completion, sam_completion, anchors, scaled_summary,
scaled_control_report. Optional input_summary/input_base_metrics/base_frames
requests R1 retention/local derivative. Existing model outputs are read-only.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys


def read(path: Path) -> dict:
    return json.loads(path.read_text())


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, payload: dict) -> None:
    with path.open('x') as stream:
        json.dump(payload,stream,indent=2,allow_nan=False)
        stream.write('\n')
    assert read(path)==payload


def encode(frames: Path, output: Path, runtime: dict) -> None:
    subprocess.run([runtime['ffmpeg'],'-nostdin','-v','error','-n','-threads','2','-framerate',str(runtime['fps']),
                    '-i',str(frames/'%03d.png'),'-an','-c:v','libx264','-threads','2','-crf','18',
                    '-pix_fmt','yuv420p','-movflags','+faststart',str(output)],check=True)


def main() -> None:
    runtime_path=Path(sys.argv[1]);r=read(runtime_path)
    if 'generation_contract' in r:
        r['generation_completion']=read(Path(r['generation_contract']))['generation_supervisor']
    for key in ('generation_completion','sam_completion'):
        receipt=read(Path(r[key]))
        assert receipt['status']=='COMPLETE' and receipt['worker_returncode']==0 and receipt['normal_exit_recorded']
    count=int(r['frame_count'])
    raw=Path(r['raw_frames']);summary=Path(r['output_summary'])
    assert [p.name for p in sorted(raw.glob('*.png'))]==[f'{i:03d}.png' for i in range(count)]
    sam=read(summary)
    assert sam['status']=='SAM_ANALYSIS_COMPLETED' and sam['frame_count']==count
    assert sam['coordinate_size']==r['native_size']
    raw_mp4=Path(r['raw_mp4']);raw_sha=digest(raw_mp4)
    if '--check-only' in sys.argv:
        print(json.dumps({'status':'CPU_ENTRY_PASS','name':r['name'],'frames':count}));return
    work=Path(r['output_dir'])/'postprocess';work.mkdir(exist_ok=False)
    reports=Path(r['reports_dir']);parent=Path(r['parent_code']);own=Path(__file__).parent
    scene=Path(r['scene']);metrics_scene=Path(r['metrics_scene'])
    post=Path(r['output_dir'])/'post';post_mp4=Path(r['output_dir'])/'post.mp4'
    base_path=reports/f"metrics-{r['name']}.json"
    env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2')
    def invoke(script: Path, config: dict, config_name: str, args: list[str]) -> None:
        runtime=work/config_name;write(runtime,config)
        subprocess.run([sys.executable,str(script),*args,str(runtime)],check=True,env=env)
    compositor={'source_frames':r['source_frames'],'raw_frames':str(raw),
                'source_summary':r['source_summary'],'output_summary':str(summary),'output_dir':str(post)}
    invoke(parent/'post_composite.py',compositor,'post.json',[str(metrics_scene)])
    encode(post,post_mp4,r)
    base={'source_frames':r['source_frames'],'raw_frames':str(raw),'post_frames':str(post),
          'source_summary':r['source_summary'],'output_summary':str(summary),'output':str(base_path),
          'anchors':r['anchors']}
    invoke(parent/'output_metrics.py',base,'base.json',[str(metrics_scene)])
    scaled={'base_metrics':str(base_path),'output_summary':str(summary),
            'scaled_summary':r['scaled_summary'],'scaled_control_report':r['scaled_control_report']}
    scaled_runtime=work/'scaled.json';write(scaled_runtime,scaled)
    subprocess.run([sys.executable,str(parent/'scaled_output_metrics.py'),str(metrics_scene),str(scaled_runtime),
                    str(reports/f"scaled-metrics-{r['name']}.json")],check=True,env=env)
    leg={'raw_frames':str(raw),'output_summary':str(summary),'base_metrics':str(base_path),
         'native_size':r['native_size'],'frame_count':count}
    for key in ('input_summary','input_base_metrics'):
        if key in r:leg[key]=r[key]
    leg_runtime=work/'leg.json';write(leg_runtime,leg)
    subprocess.run([sys.executable,str(own/'leg_metrics.py'),str(scene),str(leg_runtime),
                    str(reports/f"leg-metrics-{r['name']}.json")],check=True,env=env)
    if 'base_frames' in r:
        local={**leg,'base_frames':r['base_frames'],'refined_frames':str(raw),
               'output_dir':str(Path(r['output_dir'])/'local')}
        invoke(own/'leg_local.py',local,'local.json',[str(scene)])
        encode(Path(local['output_dir']),Path(r['output_dir'])/'local.mp4',r)
    assert digest(raw_mp4)==raw_sha
    receipt={'status':'CPU_POST_AND_METRICS_COMPLETE','name':r['name'],'frames':count,
             'raw_mp4_sha256':raw_sha,'raw_mp4_unchanged':True,'post_mp4_sha256':digest(post_mp4),
             'base_metrics_sha256':digest(base_path),'scene_sha256':digest(scene),
             'metrics_scene_sha256':digest(metrics_scene),'runtime_sha256':digest(runtime_path),
             'quality':'HUMAN_REVIEW_PENDING','temporal':'UNVERIFIED'}
    write(reports/f"processing-{r['name']}.json",receipt)
    print(json.dumps(receipt))


if __name__=='__main__':
    main()
