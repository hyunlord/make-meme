# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Create a separate source tree and interpreter, preserving the upstream checkout."""
# Run: python runtime_prepare.py UPSTREAM NEW_ROOT B007A_SITE
from pathlib import Path
import hashlib,json,shutil,sys,venv
source,root,existing_site=map(Path,sys.argv[1:4])
target=root/'upstream'; assert not target.exists()
shutil.copytree(source,target,ignore=shutil.ignore_patterns('.git','__pycache__'))
path=target/'wan/scail.py';before=path.read_text()
old='''        self.model = SCAIL2Model.from_config(scail_config_path)
        state_dict = load_file(scail_safetensors_path)
        self.model.load_state_dict(state_dict)'''
new='''        from runtime_loader import load_model
        self.model = load_model(scail_config_path, scail_safetensors_path)'''
assert before.count(old)==1;path.write_text(before.replace(old,new))
# CPU mmap load avoids eager checkpoint allocation; copy-load remains upstream semantics.
for relative in ('wan/modules/t5.py','wan/modules/clip.py'):
 p=target/relative;text=p.read_text();needle="torch.load(checkpoint_path, map_location='cpu')"
 assert text.count(needle)==1
 p.write_text(text.replace(needle,"torch.load(checkpoint_path, map_location='cpu', weights_only=True, mmap=True)"))
p=target/'wan/utils/scail_utils.py';text=p.read_text()
assert text.count('import decord\n')==1 and text.count('from decord import VideoReader\n')==1
text=text.replace('import decord\n','').replace('from decord import VideoReader\n','')
assert text.count('def load_video_for_pose_sample(video_data):\n')==1
text=text.replace('def load_video_for_pose_sample(video_data):\n','def load_video_for_pose_sample(video_data):\n    import decord\n    from decord import VideoReader\n')
p.write_text(text)
venv.EnvBuilder(with_pip=False).create(root/'environment')
site=next((root/'environment/lib').glob('python*/site-packages'))
(site/'readonly-b007a.pth').write_text('import site; site.addsitedir('+repr(str(existing_site))+')\n')
(root/'reports').mkdir(exist_ok=True)
(root/'reports/runtime_prepare.json').write_text(json.dumps({'scope':'isolated tree, meta mixedBF16 DiT loader, mmap CPU T5/CLIP checkpoint loads','files':{str(p.relative_to(target)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (target/'wan/scail.py',target/'wan/modules/t5.py',target/'wan/modules/clip.py',target/'wan/utils/scail_utils.py')}},indent=2))
