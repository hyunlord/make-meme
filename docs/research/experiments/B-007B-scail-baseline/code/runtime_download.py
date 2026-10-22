# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Pinned selected-file downloads; exact existing files reused without mutation."""
# Run: python runtime_download.py ROOT MANIFEST EXISTING_VACE_MODEL_ROOT
from pathlib import Path
import datetime as dt
import hashlib,json,shutil,subprocess,sys,time

root,manifest_path,reuse=map(Path,sys.argv[1:4]);manifest=json.loads(manifest_path.read_text())
assert manifest['revision']=='150cc0ca4e98e50e60b9295dacde39442fdccab2'
assert sum(row['size'] for row in manifest['files'])<=85_000_000_000
models=root/'models';models.mkdir(exist_ok=True);reports=root/'reports';reports.mkdir(exist_ok=True)
ledger=reports/'downloads.jsonl'
def hashes(path: Path) -> tuple[str,str]:
    sha=hashlib.sha256();git=hashlib.sha1();git.update(f'blob {path.stat().st_size}\0'.encode())
    with path.open('rb') as handle:
        while chunk:=handle.read(8*1024*1024):sha.update(chunk);git.update(chunk)
    return sha.hexdigest(),git.hexdigest()
for row in sorted(manifest['files'],key=lambda row:row.get('reuse') is None):
    target=models/row['path'];target.parent.mkdir(parents=True,exist_ok=True)
    existing=reuse/row['reuse'] if row.get('reuse') else target
    if existing.is_file():
        actual,blob=hashes(existing)
        assert existing.stat().st_size==row['size']
        assert actual==row['sha256'] if row.get('sha256') else blob==row['blob_id']
        if not target.exists():target.symlink_to(existing)
        record={'file':row['path'],'status':'REUSED','bytes_downloaded':0,'sha256':actual,'source':str(existing)}
    else:
        partial=target.with_name(target.name+'.partial');before=partial.stat().st_size if partial.exists() else 0
        assert shutil.disk_usage(models).free>=300_000_000_000+row['size']-before+66_000_000_000
        received=sum(json.loads(x)['bytes_downloaded'] for x in ledger.read_text().splitlines()) if ledger.exists() else 0
        assert received+row['size']-before<=85_000_000_000
        deadline=dt.datetime.fromisoformat('2026-10-22T13:45:00+00:00').timestamp();remaining=int(deadline-time.time()-3600);assert remaining>0
        url=f"https://huggingface.co/{manifest['repo']}/resolve/{manifest['revision']}/{row['path']}"
        start=time.time()
        result=subprocess.run(['curl','--fail','--location','--silent','--show-error','--continue-at','-','--max-time',str(remaining),'--max-filesize',str(row['size']),'--output',str(partial),url],check=False)
        after=partial.stat().st_size if partial.exists() else before
        record={'file':row['path'],'status':'TRANSFER_COMPLETE' if result.returncode==0 else 'TRANSFER_FAILED','bytes_downloaded':after-before,'seconds':time.time()-start,'returncode':result.returncode}
        with ledger.open('a') as handle:handle.write(json.dumps(record)+'\n')
        assert result.returncode==0 and after==row['size'],record
        actual,blob=hashes(partial)
        assert actual==row['sha256'] if row.get('sha256') else blob==row['blob_id']
        partial.rename(target)
        record={'file':row['path'],'status':'VERIFIED','bytes_downloaded':0,'sha256':actual,'bytes':after}
    with ledger.open('a') as handle:handle.write(json.dumps(record)+'\n')
    print(json.dumps(record),flush=True)
