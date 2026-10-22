"""Apply one exact isolated E source transition, retaining all earlier moves."""
from pathlib import Path
import difflib
import hashlib
import json
import sys

OLD = '''                if offload_model:
                    self.model.cpu()
                    torch.cuda.empty_cache()

                if self.rank == 0:
                    videos = self.vae.decode(x0)
                return videos'''
NEW = '''                from runtime_transition import preserve_final, post_sampler_decode
                preserve_final(x0, history_latent, seg_idx, seg_start, seg_end, len(segments))
                return post_sampler_decode(self.model, self.vae, x0, offload_model, self.rank)'''
STEP = '''                    del latent_model_input, timestep
'''
STEP_NEW = STEP + '''                    from runtime_transition import step_completed
                    step_completed(t, sample_scheduler)
'''


def patch(source: str) -> str:
    if source.count(OLD)!=1 or source.count(STEP)!=1:
        raise RuntimeError('Pinned E source anchors mismatch')
    return source.replace(OLD,NEW).replace(STEP,STEP_NEW)


if __name__=='__main__':
    source_path, target_path, report_path=map(Path,sys.argv[1:])
    source=source_path.read_text(); target=patch(source)
    if target_path.exists(): raise FileExistsError(target_path)
    target_path.parent.mkdir(parents=True,exist_ok=True)
    target_path.write_text(target)
    report_path.write_text(json.dumps({'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'patched_sha256':hashlib.sha256(target.encode()).hexdigest(),'diff':''.join(difflib.unified_diff(source.splitlines(True),target.splitlines(True),fromfile='B007E/scail.py',tofile='B007F/scail.py'))},indent=2))
