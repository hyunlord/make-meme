"""Pinned exact-index download only; never loads model tensors or installs packages."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import time


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8*1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main(plan_path: Path, destination: Path) -> None:
    plan = json.loads(plan_path.read_text())
    assert plan['revision'] == '539c162b1387eac9dc4c20bd3f74671309e76a4c'
    assert plan['repository'] == 'Wan-AI/Wan2.1-VACE-14B'
    shards = plan['shards']
    index = json.loads((destination/'diffusion_pytorch_model.safetensors.index.json').read_text())
    assert sorted(s['rfilename'] for s in shards) == sorted(set(index['weight_map'].values()))
    assert sum(s['size'] for s in shards) < 80*1024**3
    assert shutil.disk_usage(destination).free > sum(s['size'] for s in shards)+2*1024**3
    started = time.monotonic()
    def fetch(entry):
        name = entry['rfilename']
        assert Path(name).name == name and name.endswith('.safetensors')
        target = destination/name
        receipt_path = destination/(name+'.verified.json')
        if target.exists():
            receipt = json.loads(receipt_path.read_text())
            assert target.stat().st_size == entry['size'] and receipt['sha256'] == entry['lfs']['sha256']
            return {**receipt,'reused':True,'new_transfer_bytes':0}
        partial = destination/(name+'.part')
        before = partial.stat().st_size if partial.exists() else 0
        tick = time.monotonic()
        url = f"https://huggingface.co/{plan['repository']}/resolve/{plan['revision']}/{name}"
        result = subprocess.run(['curl','--fail','--location','--silent','--show-error','--continue-at','-',
                                 '--max-filesize',str(entry['size']),'--output',str(partial),url],check=False)
        record = {'file':name,'returncode':result.returncode,'transfer_seconds':time.monotonic()-tick,
                  'initial_partial_bytes':before,'new_transfer_bytes':partial.stat().st_size-before if partial.exists() else 0}
        if result.returncode:
            (destination/(name+'.failed.json')).write_text(json.dumps(record,indent=2)+'\n')
            raise RuntimeError(f'Transfer failed: {name}; partial retained for explicit same-file resume')
        assert partial.stat().st_size == entry['size']
        hash_started = time.monotonic()
        digest = sha(partial)
        assert digest == entry['lfs']['sha256']
        partial.rename(target)
        record.update({'bytes':entry['size'],'sha256':digest,'remote_lfs_sha256':entry['lfs']['sha256'],
                       'hash_seconds':time.monotonic()-hash_started,'reused':False})
        receipt_path.write_text(json.dumps(record,indent=2)+'\n')
        print(json.dumps(record),flush=True)
        return record
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(fetch,shards))
    report = {'status':'COMPLETE','repository':plan['repository'],'revision':plan['revision'],
              'elapsed_seconds':time.monotonic()-started,'files':results,
              'new_transfer_bytes':sum(r['new_transfer_bytes'] for r in results),
              'hash_policy':'one streamed SHA256 per newly completed shard; future reuse reads receipt and size',
              'parallel_downloads':3,'model_loads':0}
    (destination/'download-receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':'COMPLETE','seconds':report['elapsed_seconds'],'bytes':report['new_transfer_bytes']}))


if __name__ == '__main__':
    main(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
