"""Narrow checked extraction from frozen upstream; no new sampling algorithm."""
import ast
import hashlib
import textwrap
from pathlib import Path
from types import FunctionType

START='            def sample_func(latent, arg_c, arg_null, history_latent):\n'
END='            for seg_idx, (seg_start, seg_end) in enumerate(segments):\n'
TAIL='''    if offload_model:
        self.model.cpu()
        torch.cuda.empty_cache()

    if self.rank == 0:
        videos = self.vae.decode(x0)
    return videos
'''


def sample_source(source: str, *, separated: bool) -> str:
    assert source.count(START)==1 and source.count(END)==1
    result=textwrap.dedent(START+source.split(START)[1].split(END)[0])
    if separated:
        assert result.count(TAIL)==1
        result=result.replace(TAIL,"    complete(x0, history_latent)\n    return x0\n")
        result=result.replace('    if offload_model:\n        self.model.to(self.device)','    if offload_model:\n        phase("dit_to_device_start")\n        self.model.to(self.device)\n        torch.cuda.synchronize()\n        phase("dit_to_device_end")')
        result=result.replace('        del latent_model_input, timestep','        del latent_model_input, timestep\n        completed(t, sample_scheduler)')
    return result


def install_prepare(module, save_conditions) -> tuple[FunctionType, str]:
    source=Path(module.__file__).read_text()
    tree=ast.parse(source)
    cls=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='SCAIL2Pipeline')
    method=next(node for node in cls.body if isinstance(node,ast.FunctionDef) and node.name=='generate')
    function=textwrap.dedent(''.join(source.splitlines(True)[method.lineno-1:method.end_lineno]))
    nested=sample_source(source,separated=False)
    # The function's own body uses eight-space indentation for nested sample_func.
    replacement='def sample_func(latent, arg_c, arg_null, history_latent):\n    save_conditions(latent, arg_c, arg_null, history_latent, seed_g, sample_scheduler, seg_idx, seg_start, seg_end)\n'
    old=textwrap.indent(nested,'        ')
    assert function.count(old)==1
    function=function.replace(old,textwrap.indent(replacement,'        ')+'\n')
    namespace=dict(vars(module));namespace['save_conditions']=save_conditions
    exec(compile(function,'<pinned-prepare-extraction>','exec'),namespace)
    return namespace['generate'],hashlib.sha256(function.encode()).hexdigest()
