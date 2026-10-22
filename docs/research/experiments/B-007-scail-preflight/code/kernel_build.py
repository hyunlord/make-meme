"""Install only pinned local FA source into own venv; existing torch sites read-only."""
from pathlib import Path
import importlib.util
import json
import os
import subprocess
import sys
import venv
root, base_python, archive, cuda = map(Path, sys.argv[1:5])
envroot=root/'environment'
venv.EnvBuilder(with_pip=False,system_site_packages=False).create(envroot)
site=next((envroot/'lib').glob('python*/site-packages'))
base_site=subprocess.check_output([str(base_python),'-c','import sysconfig;print(sysconfig.get_paths()["purelib"])'],text=True).strip()
(site/'readonly-existing-torch.pth').write_text('import site; site.addsitedir('+repr(base_site)+')\n')
python=envroot/'bin/python'
ninja_bin=subprocess.check_output([str(python),'-c','import ninja;print(ninja.BIN_DIR)'],text=True).strip()
env=dict(os.environ,CUDA_HOME=str(cuda),PATH=str(cuda/'bin')+os.pathsep+ninja_bin+os.pathsep+os.environ['PATH'],MAX_JOBS='4',NVCC_THREADS='1',FLASH_ATTENTION_FORCE_BUILD='TRUE',FLASH_ATTN_CUDA_ARCHS='120',PIP_NO_INDEX='1',PIP_DISABLE_PIP_VERSION_CHECK='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
command=[str(python),'-m','pip','install','--no-index','--no-deps','--no-build-isolation','--no-cache-dir','--verbose','--prefix',str(envroot),str(archive)]
(root/'reports/build_configuration.json').write_text(json.dumps({'max_jobs':4,'nvcc_threads':1,'arch':'120','existing_site_readonly':base_site,'own_prefix':str(envroot),'command':command},indent=2))
subprocess.run(command,env=env,check=True)
