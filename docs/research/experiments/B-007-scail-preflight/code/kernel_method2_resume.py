"""Resume identical method 2 using existing Ninja executable; no source edits."""
from pathlib import Path
import json,os,subprocess,sys
root=Path(sys.argv[1]);ninja_dir=Path(sys.argv[2]);python=root/'environment/bin/python'
assert (ninja_dir/'ninja').is_file()
subprocess.run([str(ninja_dir/'ninja'),'--version'],check=True)
source=root/'source-method2/flash-attention-2bdeddd15af6f1c44cd41e6f5b08b9e544398397'
env=dict(os.environ,CUDA_HOME='/usr/local/cuda-13.0',PATH='/usr/local/cuda-13.0/bin:'+str(ninja_dir)+':'+os.environ['PATH'],MAX_JOBS='4',NVCC_THREADS='1',FLASH_ATTENTION_FORCE_BUILD='TRUE',FLASH_ATTN_CUDA_ARCHS='121',PIP_NO_INDEX='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
(root/'reports/method2_launcher_correction.json').write_text(json.dumps({'change':'PATH points to existing ninja executable; no dependency install or source change','ninja_directory':str(ninja_dir),'original_method_deadline':os.environ['KERNEL_METHOD_DEADLINE']},indent=2))
subprocess.run([str(python),'-m','pip','install','--no-index','--no-deps','--no-build-isolation','--no-cache-dir','--verbose','--prefix',str(root/'environment'),str(source)],env=env,check=True)
