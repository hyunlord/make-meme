# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Copy pinned source and reuse dependencies through a new isolated interpreter."""
# Run: python runtime_prepare.py B007B_ROOT B007D_ROOT NEW_ROOT
from pathlib import Path
import hashlib
import json
import shutil
import sys
import venv

old, converted, root = map(Path, sys.argv[1:4])
target = root/'upstream'
assert not target.exists()
shutil.copytree(old/'source-original',target,ignore=shutil.ignore_patterns('.git','__pycache__'))
p = target/'wan/scail.py'; text = p.read_text()
needle = '''        self.model = SCAIL2Model.from_config(scail_config_path)
        state_dict = load_file(scail_safetensors_path)
        self.model.load_state_dict(state_dict)'''
assert text.count(needle)==1
text=text.replace(needle,'''        from staged_loader import load_model
        self.model = load_model(scail_config_path, scail_safetensors_path, phase_hook=phase)''')
text=text.replace('        self.device = torch.device(f"cuda:{device_id}")','        from runtime_observe import phase\n        phase("pipeline_init")\n        self.device = torch.device(f"cuda:{device_id}")')
for anchor,label in [('        self.text_encoder = T5EncoderModel(', 't5_start'),('        self.vae_stride = config.vae_stride','t5_complete'),('        self.vae = WanVAE(', 'vae_start'),('        self.clip = CLIPModel(', 'vae_complete_clip_start'),('        logging.info(f"Creating WanSCAILModel', 'clip_complete')]:
    assert text.count(anchor)==1
    text=text.replace(anchor,'        phase('+repr(label)+')\n'+anchor)
p.write_text(text)
for relative in ('wan/modules/t5.py','wan/modules/clip.py'):
    p=target/relative;text=p.read_text();needle="torch.load(checkpoint_path, map_location='cpu')"
    assert text.count(needle)==1
    text=text.replace(needle,"torch.load(checkpoint_path, map_location='cpu', weights_only=True, mmap=True)")
    label=Path(relative).stem
    anchor='    with torch.device(device):\n        model = model_cls(**kwargs)'
    assert text.count(anchor)==1
    text=text.replace(anchor,'    from runtime_observe import phase\n    phase('+repr(label+'_constructor_start')+')\n'+anchor+'\n    phase('+repr(label+'_constructor_complete')+')')
    anchor='    model = model.to(dtype=dtype, device=device)'
    assert text.count(anchor)==1
    text=text.replace(anchor,anchor+'\n    phase('+repr(label+'_dtype_device_cast_complete')+')')
    anchor="        logging.info(f'loading {checkpoint_path}')"
    assert text.count(anchor)==1
    text=text.replace(anchor,"        from runtime_observe import phase\n        phase("+repr(label+'_checkpoint_load_start')+")\n"+anchor)
    if label=='t5':
        anchor='        self.model = model'
    else:
        anchor='    def visual(self, videos):'
    assert text.count(anchor)==1
    text=text.replace(anchor,'        phase('+repr(label+'_checkpoint_load_complete')+')\n'+anchor)
    p.write_text(text)
p=target/'wan/utils/scail_utils.py';text=p.read_text()
assert text.count('import decord\n')==1 and text.count('from decord import VideoReader\n')==1
text=text.replace('import decord\n','').replace('from decord import VideoReader\n','')
needle='def load_video_for_pose_sample(video_data):\n'; assert text.count(needle)==1
p.write_text(text.replace(needle,needle+'    import decord\n    from decord import VideoReader\n'))
venv.EnvBuilder(with_pip=False).create(root/'environment')
site=next((root/'environment/lib').glob('python*/site-packages'))
prior_site=next((old/'environment/lib').glob('python*/site-packages'))
(site/'readonly-prior.pth').write_text('import site; site.addsitedir('+repr(str(prior_site))+')\n')
(root/'models').mkdir()
for path in (old/'models').iterdir():
    if path.name!='model':(root/'models'/path.name).symlink_to(path)
(root/'models/SCAIL.safetensors').symlink_to(converted/'output/conversion/wan-model.safetensors')
(root/'inputs').symlink_to(old/'inputs')
(root/'reports/prepare.json').write_text(json.dumps({'source_scope':'isolated patched copy; originals unchanged','patch_hashes':{str(p.relative_to(target)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (target/'wan/scail.py',target/'wan/modules/t5.py',target/'wan/modules/clip.py',target/'wan/utils/scail_utils.py')}},indent=2))
