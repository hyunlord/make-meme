# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run with existing research Python: live_parity_endpoint.py /absolute/config.json [--cpu-only]
"""C-011: independent generation-prepare encoding with condition_mode=endpoint vs the E cache (elephant, goat).

Uses the unchanged C-009 gen/generate_video.py condition() and the C-008 prepare-only runner (stops before the
first denoising iteration; no DiT forward).
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import sys

from pydantic import BaseModel, ConfigDict


class Config(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    upstream: Path
    weights: Path
    tokenizer: Path
    c008_code: Path
    c009_gen: Path
    generation_config_template: Path
    endpoint_cache: Path
    layout_cache: Path
    anchors_root: Path
    prompts: dict[str, str]
    output: Path


def main() -> None:
    config = Config.model_validate_json(Path(sys.argv[1]).read_text())
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', TOKENIZERS_PARALLELISM='false')
    sys.path.insert(0, str(config.upstream))
    sys.path.insert(0, str(config.c009_gen))
    sys.path.insert(0, str(config.c008_code))
    import torch
    spec = importlib.util.spec_from_file_location('c009_generate', config.c009_gen / 'generate_video.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    template = json.loads(config.generation_config_template.read_text())
    manifest = json.loads((config.endpoint_cache / 'CACHE_MANIFEST.json').read_text())
    assert manifest['condition_family'] == 'endpoint_gray127_v1'
    gconfigs = {}
    for clip, prompt in config.prompts.items():
        values = dict(template, condition_mode='endpoint', layout_dir=None, prompt=prompt,
                      start_anchor=str(config.anchors_root / clip / 'anchors/start.png'),
                      end_anchor=str(config.anchors_root / clip / 'anchors/end.png'),
                      output=str(config.output / f'unused-{clip}'))
        gconfigs[clip] = module.Config.model_validate(values)
        module.condition(gconfigs[clip])  # CPU contract check (gray127 middle, white mask) before any model load
    if '--cpu-only' in sys.argv[2:]:
        print(json.dumps({'status': 'CPU_PASS', 'cuda_initialized': torch.cuda.is_initialized()}))
        return
    config.output.mkdir(parents=True, exist_ok=False)
    from encode_probe import ProbeConfig, load_pipe, run_g_prepare, compare, VaeObserver
    probe = ProbeConfig(upstream=config.upstream, weights=config.weights, tokenizer=config.tokenizer,
                        c006_root=config.anchors_root.parent, c007_root=config.output, output=config.output,
                        path='G', clips=list(config.prompts))
    pipe = load_pipe(probe, full=True)  # same full 1.3B load as C-007/C-009 generation
    observer = VaeObserver(pipe)
    report = {}
    with torch.no_grad():
        for clip, gconfig in gconfigs.items():
            frames, masks, receipt, context = run_g_prepare(pipe, module, gconfig)
            e_cache = torch.load(config.endpoint_cache / f'{clip}.pt', map_location='cpu', weights_only=True)['vace_context']
            l_cache = torch.load(config.layout_cache / f'{clip}.pt', map_location='cpu', weights_only=True)['vace_context']
            report[clip] = {'condition_mode': receipt['condition_mode'], 'missing_rgb_uint8': receipt['missing_rgb_uint8'],
                            'live_vs_endpoint_cache': compare(context, e_cache),
                            'live_vs_layout_cache_should_differ': {k: v for k, v in compare(context, l_cache).items()
                                                                   if k in ('exact', 'rms', 'inactive_per_t_rms', 'reactive_per_t_rms', 'mask_per_t_rms')}}
    report['public_vae_encode_calls'] = len(observer.calls)
    report['dit_forward_calls'] = 0
    (config.output / 'parity.json').write_text(json.dumps(report, indent=1))
    print(json.dumps({clip: report[clip]['live_vs_endpoint_cache']['exact'] for clip in config.prompts}))


if __name__ == '__main__':
    main()
