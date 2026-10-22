"""CPU-only contract checks, not a claim about real memory or video quality."""
from pathlib import Path
import json
from unittest.mock import Mock, patch
import pytest
import torch
import runtime_transition as transition
from runtime_patch import OLD, STEP, patch as patch_source


def test_exact_patch_keeps_prior_cpu() -> None:
    original='self.model.cpu()\n'+STEP+OLD
    result=patch_source(original)
    assert result.count('self.model.cpu()')==1
    assert 'preserve_final(x0, history_latent, seg_idx, seg_start, seg_end, len(segments))' in result
    assert 'step_completed(t, sample_scheduler)' in result
    with pytest.raises(RuntimeError): patch_source(original+OLD)


def test_skip_only_final_move_keep_cache_and_decode() -> None:
    model,vae=Mock(),Mock()
    x0=[torch.ones(1)]
    with patch.object(transition,'phase'),patch.object(torch.cuda,'empty_cache') as cache:
        transition.post_sampler_decode(model,vae,x0,True,0)
    model.cpu.assert_not_called();cache.assert_called_once();vae.decode.assert_called_once_with(x0)


def test_original_option_keeps_move() -> None:
    model,vae=Mock(),Mock()
    with patch.object(transition,'phase'),patch.object(torch.cuda,'empty_cache'):
        transition.post_sampler_decode(model,vae,[],True,0,skip_cpu=False)
    model.cpu.assert_called_once()


def test_save_then_decode_failure_preserves_exact_value(tmp_path: Path) -> None:
    transition._destination=tmp_path
    transition._steps=40;transition._calls=80
    transition._provenance={'fixture':True};transition._last={'completed_steps':40,'actual_model_calls':80}
    (tmp_path/'run.json').write_text(json.dumps({'initial_noise':{'fixture':True}}))
    value=torch.arange(24,dtype=torch.float32).reshape(2,3,4)
    with patch.object(transition,'phase'),patch.object(torch.cuda,'is_initialized',return_value=False):
        transition.preserve_final([value],None,0)
        with patch.object(torch.cuda,'empty_cache'),pytest.raises(RuntimeError):
            transition.post_sampler_decode(Mock(),Mock(decode=Mock(side_effect=RuntimeError('fixture decode fail'))),[value],True,0)
    assert transition.load_file(str(tmp_path/'final_latent.safetensors'))['x0'].equal(value)
    assert json.loads((tmp_path/'final_latent.json').read_text())['readback_exact']
    assert not list(tmp_path.glob('*.tmp'))
