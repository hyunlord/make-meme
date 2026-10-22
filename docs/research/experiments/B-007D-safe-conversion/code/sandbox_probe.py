"""Run only inside the restricted container; dummy canaries, never checkpoints."""
import json
import os
from pathlib import Path
import socket
import sys


def denied_read(path: str) -> dict:
    try:
        with open(path,'rb') as handle: handle.read(1)
        return {'denied':False}
    except OSError as error: return {'denied':True,'errno':error.errno}


def main() -> None:
    config=json.loads(Path('/code/probe_config.json').read_text())
    status=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
    result={'uid':os.getuid(),'gid':os.getgid(),'effective_caps':status['CapEff'].strip(),'no_new_privileges':status['NoNewPrivs'].strip(),'seccomp':status['Seccomp'].strip(),'environment_keys':sorted(os.environ),'parent_secret_absent':'B007D_PARENT_SECRET_CANARY' not in os.environ,'private_file':denied_read(config['outside_canary']),'host_unix_socket_visible':Path(config['outside_socket']).exists(),'docker_socket_visible':Path('/var/run/docker.sock').exists(),'gpu_devices':list(str(p) for p in Path('/dev').glob('nvidia*')),'network_interfaces':sorted(p.name for p in Path('/sys/class/net').iterdir()),'routes':Path('/proc/net/route').read_text()}
    result['readonly_fixture_readable']=Path('/input/readonly_canary').read_text()=='B007D_DUMMY_READONLY'
    try:
        Path('/input/readonly_canary').write_text('SHOULD_NOT_WRITE');result['input_write_denied']=False
    except OSError as error:result['input_write_denied']=True;result['input_write_errno']=error.errno
    try:
        Path('/tmp/b007d-must-not-write').write_text('x');result['root_write_denied']=False
    except OSError as error:result['root_write_denied']=True;result['root_write_errno']=error.errno
    Path('/output/probe-write.txt').write_text('output-only');result['output_write_ok']=True
    connections=[]
    for host,port in [('127.0.0.1',config['host_listener_port']),('1.1.1.1',443)]:
        try:
            with socket.create_connection((host,port),timeout=1):pass
            connections.append({'target_kind':'host_listener' if host=='127.0.0.1' else 'external_route','denied':False})
        except OSError as error:connections.append({'target_kind':'host_listener' if host=='127.0.0.1' else 'external_route','denied':True,'errno':error.errno})
    result['network_connections']=connections
    import torch
    import numpy as np
    result['runtime']={'python':sys.version.split()[0],'torch':torch.__version__,'torch_git':torch.version.git_version,'numpy':np.__version__,'cuda_available':torch.cuda.is_available(),'torch_path':torch.__file__,'numpy_path':np.__file__}
    sys.path.insert(0, '/legacy')
    import converter_mapping
    from scoped_loader import check_ambient, FakeTensorMode
    ambient=json.loads(Path('/code/ambient_contract.json').read_text())
    check_ambient(set(torch.serialization.get_safe_globals()),ambient['post_import'])
    with FakeTensorMode(): pass
    check_ambient(set(torch.serialization.get_safe_globals()),ambient['post_fake'])
    result['ambient_contract']='PASS exact pre/post FakeTensor names and identities; no checkpoint load'
    result['status']='PASS' if all([result['uid']!=0,int(result['effective_caps'],16)==0,result['no_new_privileges']=='1',result['seccomp']=='2',result['parent_secret_absent'],result['private_file']['denied'],not result['host_unix_socket_visible'],not result['docker_socket_visible'],not result['gpu_devices'],result['readonly_fixture_readable'],result['input_write_denied'],result['root_write_denied'],result['output_write_ok'],all(row['denied'] for row in connections),result['network_interfaces']==['lo'],not result['runtime']['cuda_available']]) else 'FAIL'
    Path('/output/sandbox_probe.json').write_text(json.dumps(result,indent=2))
    assert result['status']=='PASS'


if __name__=='__main__':main()
