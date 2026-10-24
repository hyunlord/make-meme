# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: use the existing CPU Python environment; see --help. No download required.
"""Private review archive; execute only after all experiment processes terminate.

python package_review.py PRIVATE_ROOT PUBLIC_EXPERIMENT OUTPUT_ZIP
    [--lesson LESSON_MD] [--real-output RELATIVE_DIRECTORY ...]
Real output roots must be explicit: never promote fixture tensors to real runs.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from fnmatch import fnmatchcase
from pathlib import Path
import zipfile

LIMIT = 300 * 1024**2
TEXT = {'.md', '.py', '.json', '.jsonl', '.csv', '.txt', '.log', '.diff', '.sh', '.html', '.yaml', '.yml'}
MEDIA: set[str] = {'.png', '.jpg', '.jpeg', '.mp4', '.webm', '.svg'}
DENY = {'weights','models','environment','.venv','upstream','source-original','__pycache__','.git','cache','latent_cache','prefixfeatures','prefix_features'}


def digest(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024**2),b''): h.update(block)
    return h.hexdigest()


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('private',type=Path)
    parser.add_argument('public',type=Path)
    parser.add_argument('zip',type=Path)
    parser.add_argument('--lesson',type=Path)
    parser.add_argument('--test-artifact',action='append',default=[],help='Exact private-relative small synthetic fixture/TEST_ONLY adapter; no base weights')
    parser.add_argument('--exclude',action='append',default=[], metavar='GLOB=REASON', help='Explicit private-relative omission; file SHA retained')
    parser.add_argument('--real-output',action='append',default=[])
    parser.add_argument('--artifact',action='append',default=[],help='Exact small adapter, final-sample latent or fixture; never base/prefix weights')
    parser.add_argument('--omitted-artifact',action='append',default=[],metavar='RELATIVE_PATH=REASON',help='Hash an excluded large prefix feature/cache without archiving it')
    args=parser.parse_args()
    if args.zip.exists(): raise FileExistsError(args.zip)
    private=args.private.resolve()
    selected: dict[str,Path]={}
    omitted=[]
    exclusions=[]
    for rule in args.exclude:
        pattern, separator, reason = rule.partition('=')
        if not separator or not pattern or not reason:
            raise ValueError('--exclude requires GLOB=REASON')
        exclusions.append((pattern, reason))
    def omit(path: Path, alias: str, reason: str) -> None:
        row={'archive_alias':alias,'local_path':str(path),'reason':reason}
        if path.is_symlink():
            target=os.readlink(path)
            row.update({'sha256':hashlib.sha256(os.fsencode(target)).hexdigest(),'hash_kind':'symlink text only; target NOT followed','link_target':target})
        elif path.is_file():
            row.update({'bytes':path.stat().st_size,'sha256':digest(path),'hash_kind':'file bytes'})
        omitted.append(row)
    def add_tree(root: Path,prefix: str,allowed: set[str],kind: str) -> None:
        if root.is_symlink():
            omit(root,prefix,'symlink root; not followed')
            return
        if not root.exists():
            omitted.append({'archive_alias':prefix,'local_path':str(root),'reason':'not present at packaging','sha256':None})
            return
        for path in sorted(root.rglob('*')):
            rel=path.relative_to(root)
            if path.is_symlink():
                omit(path,prefix+'/'+str(rel),'symlink; not followed')
                continue
            if not path.is_file(): continue
            if '__pycache__' in rel.parts:
                omit(path,prefix+'/'+str(rel),'regenerable Python bytecode; source retained')
                continue
            if any(part in {'.pytest_cache','.ruff_cache'} for part in rel.parts):
                omit(path,prefix+'/'+str(rel),'regenerable test/lint cache; full test and type diagnostics retained')
                continue
            if any(part in DENY for part in rel.parts):
                raise ValueError('Denied bulk directory inside selected root; narrow selection first')
            if path.suffix not in allowed and not path.name.endswith('LICENSE'):
                omit(path,prefix+'/'+str(rel),'extension outside explicit allowlist')
                continue
            reason=next((reason for pattern,reason in exclusions if path.is_relative_to(private) and fnmatchcase(str(path.relative_to(private)),pattern)),None)
            if reason is not None:
                omit(path,prefix+'/'+str(rel),reason)
                continue
            if path.name == 'preprocessed_inputs.pt':
                omitted.append({'archive_alias':prefix+'/'+str(rel),'reason':'Duplicate large preprocessed tensor; exact file hash recorded, original inputs and preprocessing code retained','bytes':path.stat().st_size,'sha256':digest(path)})
                continue
            fixture=any('fixture' in part.lower() or part.startswith('test_') for part in rel.parts)
            if fixture and path.suffix in MEDIA:
                omit(path,prefix+'/'+str(rel),'fixture tensor/media; not real output')
                continue
            if kind=='real' and fixture: raise RuntimeError('Explicit real output points into fixture tree')
            selected[prefix+'/'+str(rel)]=path
    add_tree(args.public,'public/experiment',TEXT,'public')
    if args.lesson: selected['public/lesson/'+args.lesson.name]=args.lesson
    for name in ['code','review_code','inventory','research','reports','scripts','tools','configs','public_snapshot','inputs']:
        add_tree(private/name,'private/'+name,TEXT | (MEDIA if name in {'reports','inputs'} else set()),'support')
    # Per-stage/case reports contain failures too; no tensor inclusion by implication.
    for parent in ['cases','stages']:
        base=private/parent
        if base.exists():
            for stage in sorted(base.iterdir()):
                if stage.is_dir() and not stage.is_symlink():
                    for name in ['reports','configs']:
                        add_tree(stage/name,f'private/{parent}/{stage.name}/{name}',TEXT | {'.png'},'support')
    for path in sorted(private.iterdir()):
        if path.is_file() and not path.is_symlink() and path.suffix in TEXT:
            selected['private/'+path.name]=path
    for rel in args.real_output:
        path=private/rel
        if path.is_symlink() or not path.is_dir() or not path.resolve().is_relative_to(private):
            raise ValueError('Real output must be an existing nonsymlink directory inside private root')
        add_tree(path,'private/'+str(path.relative_to(private)),TEXT | MEDIA,'real')
    for rel in args.test_artifact:
        path=private/rel
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(private):
            raise ValueError('Test artifact must be a concrete private file')
        if path.suffix not in {'.pt','.safetensors','.npz'} or path.stat().st_size > 32*1024**2:
            raise ValueError('Test artifact outside bounded tensor contract')
        if any(part in DENY for part in path.relative_to(private).parts):
            raise ValueError('Base/environment/cache directory forbidden')
        selected['private/'+str(path.relative_to(private))]=path
    for rel in args.artifact:
        path=private/rel
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(private):
            raise ValueError('Artifact must be concrete and private')
        if path.suffix not in {'.pt','.safetensors','.npz'} or path.stat().st_size > 128*1024**2:
            raise ValueError('Artifact outside small tensor contract')
        if any(part in DENY for part in path.relative_to(private).parts):
            raise ValueError('Base/prefix/cache artifact forbidden')
        selected['private/'+str(path.relative_to(private))]=path
    for rule in args.omitted_artifact:
        rel,separator,reason=rule.partition('=')
        path=private/rel
        if not separator or not reason or not path.is_relative_to(private) or '..' in Path(rel).parts:
            raise ValueError('Invalid omitted artifact record')
        omit(path,'private/'+rel,reason)
    omitted=[row for row in omitted if row['archive_alias'] not in selected]
    if not selected: raise RuntimeError('No payload')
    manifest={'schema':1,'explicit_tensor_artifacts':args.artifact,'test_only_artifacts':args.test_artifact,'test_artifact_status':'TEST_ONLY / NOT_FOR_INFERENCE','real_output_roots':args.real_output,'payload':[], 'omitted':omitted,
              'limits':['Base weights, environments, upstream trees and multi-GB prefix caches excluded. Small explicit adapter/optimizer/RNG checkpoints and final latents may be included with provenance.',
                        'B022 private same-checkpoint resumed-update research evidence. Actual training, sampling and visual outcomes are recorded separately in the final reports; file inclusion does not imply quality or generalization acceptance.',
                        'No conditions, latent or video is claimed unless its actual file is included.']}
    for name,path in selected.items():
        manifest['payload'].append({'path':name,'bytes':path.stat().st_size,'sha256':digest(path)})
    args.zip.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.zip,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for name,path in selected.items(): archive.write(path,name)
        archive.writestr('MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
    with zipfile.ZipFile(args.zip) as archive:
        if archive.testzip() is not None: raise RuntimeError('CRC failure')
        if len(archive.namelist()) != len(set(archive.namelist())): raise RuntimeError('Duplicate archive entries')
        actual=json.loads(archive.read('MANIFEST.json'))
        for row in actual['payload']:
            h=hashlib.sha256();size=0
            with archive.open(row['path']) as stream:
                for block in iter(lambda:stream.read(8*1024**2),b''):h.update(block);size+=len(block)
            if size!=row['bytes'] or h.hexdigest()!=row['sha256']:raise RuntimeError('Payload verification failure')
    receipt={'zip':str(args.zip.resolve()),'bytes':args.zip.stat().st_size,'sha256':digest(args.zip),'payload_count':len(selected),'crc_and_payload_hashes_verified':True,'within_300MiB':args.zip.stat().st_size<=LIMIT}
    args.zip.with_suffix(args.zip.suffix+'.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))
    if not receipt['within_300MiB']:raise RuntimeError('Archive exceeds target; retain archive and report rather than silently dropping failures')


if __name__=='__main__':main()
