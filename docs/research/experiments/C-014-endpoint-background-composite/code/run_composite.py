# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run: existing-research-python run_composite.py PRIVATE_MANIFEST ROOT --cpu-only
"""Sequential CPU-only composition. No evaluator/oracle/model imports here."""
from pathlib import Path
import argparse
import hashlib
import json
import resource
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from PIL import Image
from compositor import alpha, blend, build_plate, load_rgb, save_rgb_new, ContractError


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def memory_check() -> int:
    peak = max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
               resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss) * 1024
    if peak > 2 * 1024**3:
        raise ContractError('CPU_RSS_BUDGET_EXCEEDED')
    return peak


def probe(path: Path) -> dict:
    result = subprocess.check_output(['/usr/bin/ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height,nb_frames,r_frame_rate,duration', '-of', 'json', str(path)])
    stream = json.loads(result)['streams'][0]
    if (stream['width'], stream['height'], stream['nb_frames'], stream['r_frame_rate']) != (416, 240, '33', '16/1'):
        raise ContractError('Video dimensions/frame count/fps mismatch')
    return stream


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest', type=Path); parser.add_argument('root', type=Path)
    parser.add_argument('--cpu-only', action='store_true', required=True)
    args = parser.parse_args(); root = args.root; started = time.monotonic()
    manifest = json.loads(args.manifest.read_text())
    paths = json.loads((root/'PATHS.json').read_text())
    expected_names = ['I50_S1', 'S_S1', 'ON2048_S2_A']
    if list(manifest['cases']) != expected_names or set(paths) != set(expected_names):
        raise ContractError('Frozen three-case contract mismatch')
    for row in manifest['files']:
        if sha(Path(row['path'])) != row['sha256']:
            raise ContractError('Input hash mismatch: '+row['role'])
    subprocess.run([sys.executable, '-m', 'unittest', 'test_compositor', '-v'], cwd=Path(__file__).parent, check=True)
    (root/'FIXTURES.json').write_text(json.dumps({'status':'PASS','suite':'test_compositor','purpose':'CPU contracts, not quality evidence'}))
    plate_dir = root/'plate'; plate_dir.mkdir(exist_ok=False)
    start = load_rgb(Path(manifest['anchors']['start'])); end = load_rgb(Path(manifest['anchors']['end']))
    plate = build_plate(start, end)
    save_rgb_new(plate_dir/'background_from_endpoints.png', plate.image)
    Image.fromarray(plate.source_map).save(plate_dir/'source_map.png')
    for name, mask in [('U0',plate.start_valid),('UT',plate.end_valid)]:
        Image.fromarray(mask.astype(np.uint8)*255).save(plate_dir/(name+'.png'))
    provenance = {'status':'ENDPOINT_PLATE_ESTABLISHED','label':'KNOWN_SIZE_AND_PATH / ENDPOINT_OBSERVED_BACKGROUND',
        'inputs':[{k:v for k,v in row.items() if k!='path'} for row in manifest['files']],
        'plate_sha256':sha(plate_dir/'background_from_endpoints.png'), 'source_map_sha256':sha(plate_dir/'source_map.png'),
        'source_map_values':{'unknown':0,'anchor0':1,'anchor32':2},
        'source_counts':{'anchor0':int((plate.source_map==1).sum()),'anchor32':int((plate.source_map==2).sum()),'unknown':int((plate.source_map==0).sum())},
        'common_valid_pixels':int((plate.start_valid & plate.end_valid).sum()),'common_rgb_exact':True,
        'same_coordinate_source_bytes_exact':bool(np.array_equal(plate.image[plate.start_valid],start[plate.start_valid]) and np.array_equal(plate.image[~plate.start_valid],end[~plate.start_valid])),
        'oracle_audit':'NOT_RUN; compositor receives no oracle paths'}
    (root/'INPUTS_AND_PLATE.json').write_text(json.dumps(provenance,indent=2))
    contract = {}
    for name in expected_names:
        source = Path(manifest['cases'][name]['raw_frames'])
        expected = [f'{t:03d}.png' for t in range(33)]
        if sorted(p.name for p in source.glob('*.png')) != expected or len(paths[name])!=33:
            raise ContractError('Frame-index contract mismatch')
        if paths[name][0]!=[104,120] or paths[name][-1]!=[312,120]:
            raise ContractError('Endpoint coordinate contract mismatch')
        out = root/'outputs'/name; (out/'frames').mkdir(parents=True,exist_ok=False)
        (out/'alpha').mkdir(); rows = []
        for t, center in enumerate(paths[name]):
            raw = load_rgb(source/f'{t:03d}.png'); a = alpha(tuple(center))
            post = save_rgb_new(out/'frames'/f'{t:03d}.png', blend(raw,plate.image,a))
            core = bool(np.array_equal(post[a==1],raw[a==1])); outside = bool(np.array_equal(post[a==0],plate.image[a==0]))
            if not core or not outside: raise ContractError('Stored PNG pixel contract failed')
            np.save(out/'alpha'/f'{t:03d}.npy', a, allow_pickle=False)
            Image.fromarray(np.rint(a*255).astype(np.uint8)).save(out/'alpha'/f'{t:03d}.png')
            rows.append({'frame':t,'core_exact':core,'outside_exact':outside,'alpha_float64_sha256':sha(out/'alpha'/f'{t:03d}.npy'),'post_png_sha256':sha(out/'frames'/f'{t:03d}.png')})
            memory_check()
        subprocess.run(['/usr/bin/ffmpeg','-v','error','-n','-threads','2','-framerate','16','-i',str(out/'frames/%03d.png'),
            '-c:v','libx264','-threads','2','-pix_fmt','yuv420p','-crf','18',str(out/'composite.mp4')],check=True)
        contract[name]={'frames':rows,'raw_video':probe(Path(manifest['cases'][name]['raw_mp4'])),'post_video':probe(out/'composite.mp4')}
    for row in manifest['files']:
        if sha(Path(row['path']))!=row['sha256']:raise ContractError('RAW_MUTATED')
    receipt={'status':'COMPOSITE_PIXEL_CONTRACT_PASS','raw_immutable':True,'cases':contract,
        'elapsed_seconds':time.monotonic()-started,'peak_rss_bytes':memory_check(),'thread_cap':2,
        'new_post_mp4':3,'frames_composited':99,'model_load':0,'sampler':0,'vae_encode':0,'vae_decode':0,
        'training':0,'gpu_compute':0,'download':0,'install':0,'quality_retry':0,'torch_imported':'torch' in sys.modules}
    if receipt['torch_imported']:raise ContractError('Unexpected torch import')
    (root/'COMPOSITE_RUN.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps({k:v for k,v in receipt.items() if k!='cases'}),flush=True)


if __name__=='__main__':main()
