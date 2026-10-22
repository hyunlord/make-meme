"""CPU integration of isolated parser, exact patched save call and pinned writer.
No fake pipeline/model call: original prepared RGB is the explicit test tensor.
Usage: python writer_integration.py B007B_ROOT
"""
import argparse,ast,hashlib,json,os,random,sys
from pathlib import Path
from types import SimpleNamespace
import imageio
import numpy as np
from PIL import Image
import torch
import torchvision
from writer_patch import patch_writer

root=Path(sys.argv[1]);torch.set_num_threads(4)
source=root/'inputs/upstream-code/generate.py';utils=root/'inputs/upstream-code/utils.py'
isolated=root/'isolated_writer/generate.py';patch_writer(source,isolated)
# Only explicit function nodes execute; no wan/model imports or main entrypoint.
def nodes(path: Path, names: set[str]) -> ast.Module:
    tree=ast.parse(path.read_text());selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    assert {n.name for n in selected}==names
    return ast.Module(body=selected,type_ignores=[])

namespace={'argparse':argparse,'sys':sys,'random':random,'torch':torch,'torchvision':torchvision,'imageio':imageio,'osp':os.path,
           'SCAIL_CONFIGS':{'SCAIL-14B':None},'SCAIL_CONFIG_PATHS':{'SCAIL-14B':'unused-CPU-parser-test'}}
exec(compile(nodes(utils,{'cache_video','str2bool'}),str(utils),'exec'),namespace)
exec(compile(nodes(isolated,{'_validate_args','_parse_args'}),str(isolated),'exec'),namespace)
original_argv=sys.argv[:]
sys.argv=['generate.py','--image','CPU-input-alias','--pose','CPU-driver-alias','--base_seed','20261022','--output_fps','24']
args=namespace['_parse_args']();assert args.output_fps==24
sys.argv[-1]='0'
try:namespace['_parse_args']()
except ValueError:zero_rejected=True
else:raise AssertionError('Nonpositive FPS accepted')
sys.argv=original_argv
video=torch.stack([torch.from_numpy(np.array(Image.open(root/'inputs/lab/driver'/f'{i:03d}.png').convert('RGB'),copy=True)).permute(2,0,1) for i in range(17)],dim=1).float()/127.5-1
output=root/'outputs/writer_integration';output.mkdir(parents=True,exist_ok=True);save_file=str(output/'original-rgb-explicit24fps.mp4')
generate_tree=ast.parse(isolated.read_text());function=next(n for n in generate_tree.body if isinstance(n,ast.FunctionDef) and n.name=='generate_video')
calls=[n for n in ast.walk(function) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='cache_video'];assert len(calls)==1
namespace.update({'args':args,'cfg':SimpleNamespace(sample_fps=16),'video':video,'save_file':save_file})
result=eval(compile(ast.Expression(calls[0]),str(isolated),'eval'),namespace);assert result==save_file
import subprocess
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=avg_frame_rate,nb_read_frames,width,height,duration','-of','json',save_file]));stream=probe['streams'][0]
assert stream['avg_frame_rate']=='24/1' and int(stream['nb_read_frames'])==17 and (stream['width'],stream['height'])==(512,896)
report={'status':'COMPLETED_CPU_REAL_ENCODING','torch':torch.__version__,'torchvision':torchvision.__version__,'imageio':imageio.__version__,
        'exact_upstream_writer_sha256':hashlib.sha256(utils.read_bytes()).hexdigest(),'pinned_generate_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'isolated_generate_sha256':hashlib.sha256(isolated.read_bytes()).hexdigest(),
        'explicit_output_fps':24,'cfg_default_fps':16,'zero_fps_rejected':zero_rejected,'test_tensor_shape':list(video.shape),'probe':probe,'output_sha256':hashlib.sha256(Path(save_file).read_bytes()).hexdigest(),
        'scope':'Actual pinned cache_video CPU encoding, exact patched call and parser. No fullmodel imports, no diffusion; prepared source RGB only. Sampling/training prior unchanged.'}
(root/'reports/writer_integration.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
