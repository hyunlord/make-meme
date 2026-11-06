# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Snapshot actual CPU reports: aggregate_metrics.py SCENE PRIVATE_RUNTIME OUTPUT.

Runtime variants/refereferences/local_composites map names to status/reason plus
report path keys base, scaled, leg, processing, manifest, confirmation. Missing
artifacts remain unavailable; this script never runs a model or ranks outputs.
New output only. Human PENDING fields must never be populated from proxies.
"""
from pathlib import Path
import hashlib
import json
import sys
from datetime import datetime,timezone


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect(spec: dict, count: int) -> dict:
    result={'status':spec['status'],'evidence':{}}
    if 'reason' in spec:result['reason']=spec['reason']
    for key in ('base','scaled','leg','processing','manifest','confirmation'):
        if key not in spec:
            continue
        path=Path(spec[key])
        if not path.is_file():
            result['evidence'][key]={'status':'UNAVAILABLE'}
            continue
        data=load(path)
        text=json.dumps(data)
        if '/home/' in text or '/Users/' in text:
            raise ValueError(f'Private path in {key} report: sanitize source before publication')
        if key in ('base','scaled','leg'):
            rows=data['frames']
            if len(rows)!=count or {r['frame'] for r in rows}!=set(range(count)):
                raise ValueError(f'Incomplete or duplicate frame metrics: {key}')
        result[key]=data
        result['evidence'][key]={'status':'AVAILABLE','sha256':sha(path)}
    if spec['status']=='MEASURED' and any(result['evidence'].get(k,{}).get('status')!='AVAILABLE'
                                         for k in spec.get('required',[])):
        raise ValueError('MEASURED claim lacks required artifacts')
    return result


def main() -> None:
    scene,runtime,output=map(Path,sys.argv[1:])
    if output.exists():raise FileExistsError(output)
    config=load(scene);spec=load(runtime);count=config['scene']['segment']['frames']
    result={'quality':'HUMAN_REVIEW_PENDING','temporal':'UNVERIFIED','automatic_ranking':False,
            'collected_at_utc':datetime.now(timezone.utc).isoformat(),'scene_sha256':sha(scene),
            'measurement_policy':config['measurement_policy'],'frame_count':count}
    for group in ('variants','references','local_composites'):
        result[group]={name:collect(item,count) for name,item in spec.get(group,{}).items()}
    hash_groups={}
    for name,row in result['variants'].items():
        raw_hash=row.get('processing',{}).get('raw_mp4_sha256')
        if raw_hash:
            hash_groups.setdefault(raw_hash,[]).append(name)
    result['byte_identical_raw_groups']=[{'sha256':key,'runs':names} for key,names in hash_groups.items() if len(names)>1]
    result['limitations']=['Byte-identical outputs are not independent effective-strength contrasts; separate execution receipts remain preserved.',
                          'Luma is a gray-pixel proxy, not a recovered physical alpha.',
                          'Laplacian variance can measure noise and texture as well as crispness.',
                          'Kling differs in lighting and size and is reference only.',
                          'Missing observations remain null with coverage, never silently zero.',
                          'Proxy changes are not human judgments of motion, identity or usable quality.']
    temporary=output.with_suffix(output.suffix+'.tmp')
    with temporary.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    load(temporary);temporary.replace(output)


if __name__=='__main__':main()
