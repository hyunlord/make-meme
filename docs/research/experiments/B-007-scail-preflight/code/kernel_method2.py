"""Second preregistered method: official commit archives, no source edits."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,tarfile,time,urllib.request
root=Path(sys.argv[1]); deadline=1792655193
archives=[('flash-attention','Dao-AILab/flash-attention','2bdeddd15af6f1c44cd41e6f5b08b9e544398397'),('cutlass','NVIDIA/cutlass','7127592069c2fe01b041e174ba4345ef9b279671')]
ledger=root/'reports/downloads.jsonl'
for name,repo,revision in archives:
    used=sum(json.loads(x)['bytes'] for x in ledger.read_text().splitlines())
    url=f'https://codeload.github.com/{repo}/tar.gz/{revision}'
    target=root/'downloads'/f'{name}-{revision}.tar.gz'; assert not target.exists()
    count=0; digest=hashlib.sha256(); status='PARTIAL'
    try:
        with urllib.request.urlopen(url,timeout=60) as response,target.open('wb') as output:
            while chunk:=response.read(1024*1024):
                assert time.time()<deadline and used+count+len(chunk)<=2_000_000_000
                output.write(chunk);digest.update(chunk);count+=len(chunk)
        status='COMPLETE'
    finally:
        with ledger.open('a') as output:output.write(json.dumps(dict(url=url,revision=revision,bytes=count,sha256=digest.hexdigest(),status=status))+'\n')
    with tarfile.open(target) as archive:archive.extractall(root/'source-method2',filter='data')
source=root/'source-method2'/('flash-attention-'+archives[0][2]); cutlass=root/'source-method2'/('cutlass-'+archives[1][2])
(source/'csrc/cutlass').rmdir();cutlass.rename(source/'csrc/cutlass')
envroot=root/'environment';python=envroot/'bin/python'
ninja=subprocess.check_output([str(python),'-c','import ninja;print(ninja.BIN_DIR)'],text=True).strip()
env=dict(os.environ,CUDA_HOME='/usr/local/cuda-13.0',PATH='/usr/local/cuda-13.0/bin:'+ninja+':'+os.environ['PATH'],MAX_JOBS='4',NVCC_THREADS='1',FLASH_ATTENTION_FORCE_BUILD='TRUE',FLASH_ATTN_CUDA_ARCHS='121',PIP_NO_INDEX='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
subprocess.run([str(python),'-m','pip','install','--no-index','--no-deps','--no-build-isolation','--no-cache-dir','--verbose','--prefix',str(envroot),str(source)],env=env,check=True)
