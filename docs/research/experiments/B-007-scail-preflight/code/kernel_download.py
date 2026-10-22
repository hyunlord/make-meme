"""Single pinned package download with cumulative byte accounting and hard ceiling."""
from pathlib import Path
import hashlib
import json
import sys
import urllib.request
import datetime as dt
import time
root=Path(sys.argv[1]);config=json.loads(Path(sys.argv[2]).read_text());ledger=root/'reports/downloads.jsonl';dest=root/'downloads'/config['filename'];dest.parent.mkdir(parents=True,exist_ok=True)
assert not dest.exists()
prior=sum(json.loads(line)['bytes'] for line in ledger.read_text().splitlines()) if ledger.exists() else 0
cap=2_000_000_000;received=0;status='FAILED';digest=hashlib.sha256();deadline=dt.datetime.fromisoformat('2026-10-22T08:01:33+00:00').timestamp()
try:
    with urllib.request.urlopen(config['url'],timeout=30) as response, dest.open('xb') as output:
        length=int(response.headers.get('Content-Length','0'))
        assert length==config['bytes'] and prior+length<=cap
        while block:=response.read(1024*1024):
            received+=len(block)
            assert prior+received<=cap and received<=config['bytes'] and time.time()<deadline
            output.write(block);digest.update(block)
    assert received==config['bytes'] and digest.hexdigest()==config['sha256']
    status='VERIFIED'
finally:
    with ledger.open('a') as handle:handle.write(json.dumps({'filename':config['filename'],'bytes':received,'prior_bytes':prior,'cap':cap,'status':status,'sha256':digest.hexdigest(),'url':config['url']})+'\n')
print(status,received)
