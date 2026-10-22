"""Host-side dummy-canary probe using exact reviewed mount manifest."""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from sandbox_command import command


def main() -> None:
    root=Path(sys.argv[1]); mounts=json.loads((root/'mounts.json').read_text())
    output=root/'output';output.mkdir(exist_ok=True)
    (output/'tmp').mkdir(exist_ok=True);(output/'home').mkdir(exist_ok=True)
    outside=root/'host-private-canary';outside.write_text('DUMMY-NOT-A-CREDENTIAL')
    readonly=root/'readonly_canary';readonly.write_text('B007D_DUMMY_READONLY')
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1)
    unix=socket.socket(socket.AF_UNIX);unixpath=root/'host-private.sock';unix.bind(str(unixpath));unix.listen(1)
    config={'outside_canary':str(outside),'outside_socket':str(unixpath),'host_listener_port':listener.getsockname()[1]}
    (root/'code/probe_config.json').write_text(json.dumps(config))
    assert outside.is_file() and unixpath.exists()
    argv=command('make-meme-b007d-probe',output,mounts,'/code/sandbox_probe.py',[])
    try:
        result=subprocess.run(argv,env={**os.environ,'B007D_PARENT_SECRET_CANARY':'DUMMY_PARENT_VALUE'},capture_output=True,text=True,timeout=120)
        inspect=json.loads(subprocess.check_output(['docker','inspect','make-meme-b007d-probe']))[0]
        report={'returncode':result.returncode,'command':argv,'stdout':result.stdout,'stderr':result.stderr,'host_canary_existed':True,'host_unix_socket_existed':True,'host_listener_was_listening':True,'container_inspect':inspect,'readonly_canary_unchanged':readonly.read_text()=='B007D_DUMMY_READONLY'}
        (root/'reports/sandbox_preflight_private.json').write_text(json.dumps(report,indent=2))
        assert result.returncode==0, result.stderr
        proof=json.loads((output/'sandbox_probe.json').read_text());assert proof['status']=='PASS'
        proof['mount_manifest_sha256']=hashlib.sha256((root/'mounts.json').read_bytes()).hexdigest()
        (root/'os-proof.json').write_text(json.dumps(proof,indent=2))
    finally:
        listener.close();unix.close();unixpath.unlink(missing_ok=True)
        subprocess.run(['docker','stop','--time','2','make-meme-b007d-probe'],capture_output=True,check=False)


if __name__=='__main__':main()
