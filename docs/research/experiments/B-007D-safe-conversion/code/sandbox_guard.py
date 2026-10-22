"""Own-container deadline/resource guard; no changes to other workloads."""
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import time
from sandbox_command import command

GIB=1024**3
DEADLINE=dt.datetime.fromisoformat('2026-10-22T14:34:00+00:00').timestamp()


def memory() -> dict:
    return {line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemAvailable:','SwapTotal:','SwapFree:'))}


def main() -> int:
    root=Path(sys.argv[1]);stage=sys.argv[2];assert stage in ('metadata','conversion')
    report=root/'reports'/f'{stage}-process.json';assert not report.exists()
    proof=json.loads((root/'os-proof.json').read_text());assert proof['status']=='PASS'
    fresh=memory();assert fresh['MemAvailable']>=40*GIB
    import hashlib
    assert proof['mount_manifest_sha256']==hashlib.sha256((root/'mounts.json').read_bytes()).hexdigest()
    mounts=json.loads((root/'mounts.json').read_text())
    cap=8*GIB if stage=='metadata' else min(32*GIB,fresh['MemAvailable']-24*GIB)
    seconds=min(1200 if stage=='metadata' else 3600,int(DEADLINE-time.time()-60));assert seconds>0
    name='make-meme-b007d-'+stage
    args=[stage,'/input/checkpoint.pt','/input/convert.py','/legacy','/graph-code','/input/os-proof.json','/output/ledger','/output/conversion']
    argv=command(name,root/'output',mounts,'/code/convert_stage.py',args,cap)
    info={'command':argv,'started':time.time(),'deadline':time.time()+seconds,'global_deadline':DEADLINE,'memory_cap':cap,'initial_memory':fresh,'reason':'process_exit','container':name}
    with (root/'reports'/f'{stage}.log').open('x') as log:
        child=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT);info['pid']=child.pid;report.write_text(json.dumps(info,indent=2))
        while child.poll() is None:
            current=memory();sample={'time':time.time(),'system_memory':current}
            inspect=subprocess.run(['docker','inspect',name],capture_output=True,text=True,timeout=10)
            if inspect.returncode==0:
                container=json.loads(inspect.stdout)[0];sample['state']=container['State'];pid=container['State'].get('Pid',0)
                proc=Path('/proc')/str(pid)
                if pid and proc.exists():
                    for item in ('status','io','cgroup'):
                        try:sample[item]=(proc/item).read_text()
                        except OSError as error:sample[item]=str(error)
                    cgroup=next((line.split('::',1)[1] for line in str(sample.get('cgroup','')).splitlines() if '::' in line),None)
                    if cgroup:
                        for item in ('memory.current','memory.peak','memory.stat','memory.events'):
                            try:sample[item]=(Path('/sys/fs/cgroup')/cgroup.lstrip('/')/item).read_text()
                            except OSError as error:sample[item]=str(error)
            with (root/'reports'/f'{stage}-resources.jsonl').open('a') as handle:handle.write(json.dumps(sample)+'\n')
            swap=current['SwapTotal']-current['SwapFree'];swap0=fresh['SwapTotal']-fresh['SwapFree']
            queue=subprocess.run(['curl','-fsS','--max-time','2','http://127.0.0.1:8190/queue'],capture_output=True,text=True,timeout=10)
            other=False
            if queue.returncode != 0:
                raise RuntimeError('Service queue observation failed; outer supervisor must stop owned container')
            if queue.returncode==0:
                q=json.loads(queue.stdout);other=bool(q['queue_running'] or q['queue_pending'])
            reason='other_work_started' if other else 'system_memory_below24GiB' if current['MemAvailable']<24*GIB else 'swap_growth' if swap>swap0 else 'deadline' if time.time()>=info['deadline'] else None
            if reason:
                info['reason']=reason;subprocess.run(['docker','stop','--time','10',name],capture_output=True,timeout=20);break
            time.sleep(1)
        info['returncode']=child.wait(timeout=30);info['finished']=time.time()
        final=subprocess.run(['docker','inspect',name],capture_output=True,text=True,timeout=10)
        info['final_container']=json.loads(final.stdout)[0] if final.returncode==0 else {'error':final.stderr}
        report.write_text(json.dumps(info,indent=2))
    return info['returncode']


if __name__=='__main__':raise SystemExit(main())
