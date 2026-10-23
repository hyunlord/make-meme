"""CPU contracts: no model, no GPU and no learned preprocessing."""
import torch
import pytest
import alg


def test_disabled_and_ratio_one_preserve_baseline_order_and_values():
    # Given original CFG predicts positive then negative.
    for settings in (alg.AlgSettings(enabled=False), alg.AlgSettings(ratio=1.0)):
        calls = []
        def predict(branch):
            calls.append(branch)
            return torch.tensor(3.0 if branch == "c_orig" else 2.0)
        # When ALG is disabled or the filter is identity.
        result = alg.guided_prediction(predict, settings, 0, 40, 5.0)
        # Then the exact baseline order/arithmetic is retained.
        assert calls == ["c_orig", "u_orig"]
        assert result == 7.0
        assert settings.expected_calls(40) == 80


def test_active_formula_and_schedule():
    # Given distinct branch predictions distinguish ALG from naive low CFG.
    settings = alg.AlgSettings()
    values = {"u_orig": 2.0, "u_low": 3.0, "c_low": 7.0, "c_orig": 11.0}
    calls = []
    def predict(branch):
        calls.append(branch)
        return torch.tensor(values[branch])
    # When every sampling step is evaluated.
    results = [alg.guided_prediction(predict, settings, i, 40, 5.0) for i in range(40)]
    # Then eight ALG steps and 32 baseline steps produce 88 calls.
    assert results[0] == results[7] == 22.0
    assert results[8] == results[39] == 47.0
    assert calls[:3] == ["u_orig", "u_low", "c_low"]
    assert calls[24:26] == ["c_orig", "u_orig"]
    assert len(calls) == settings.expected_calls(40) == 88


@pytest.mark.parametrize("shape", [(16,1,112,64),(2,3,4,12,8)])
def test_filter_isolates_planes_and_preserves_input_and_rng(shape):
    # Given independently valued signed channel/frame planes.
    value = torch.arange(torch.tensor(shape[:-2]).prod().item(), dtype=torch.float32).reshape(*shape[:-2],1,1)-12
    original = value.expand(shape).clone()
    before = original.clone(); rng = torch.get_rng_state().clone()
    # When spatial down/up is applied.
    filtered = alg.low_pass_reference(original, 0.4)
    # Then no channels/frames/batches mix and signed values are not clamped.
    assert filtered.shape == original.shape and filtered.dtype == original.dtype and filtered.device == original.device
    assert torch.allclose(filtered, original, atol=1e-5, rtol=1e-6)
    assert torch.equal(original,before) and torch.equal(rng,torch.get_rng_state())
    assert filtered.data_ptr() != original.data_ptr()


def test_impulse_stays_in_its_channel_frame_and_batch():
    # Given one impulse in one plane.
    value=torch.zeros(2,3,4,112,64);value[1,2,3,50,30]=100
    # When filtered spatially.
    result=alg.low_pass_reference(value,.4)
    # Then only that plane changes and resolution is the registered round rule.
    assert alg.spatial_size(112,64,.4)==(45,26)
    assert result[1,2,3].abs().sum()>0
    result[1,2,3]=0
    assert torch.count_nonzero(result)==0


def test_branch_kwargs_only_replace_reference_without_parent_mutation():
    # Given two branches sharing visual containers and different text.
    reference=torch.ones(16,1,12,8);filtered=alg.low_pass_reference(reference,.4)
    common={'ref_latents':[reference],'clip_fea':torch.ones(1),'ref_masks':[torch.ones(1)],
            'pose_latents':[torch.ones(1)],'driving_masks':[torch.ones(1)],'seq_len':1e10,
            'history_mask':None,'replace_flag':False,'additional_ref_latents':None,'additional_ref_masks':None}
    positive={**common,'context':[torch.ones(2)]};negative={**common,'context':[torch.zeros(2)]}
    # When every branch kwargs is selected.
    branches={name:alg.branch_condition(name,positive,negative,filtered) for name in ('c_orig','u_orig','c_low','u_low')}
    # Then only a fresh low-reference container changes; all other fields retain identity.
    for name,actual in branches.items():
        original=positive if name.startswith('c_') else negative
        for key in original:
            if key!='ref_latents':assert actual[key] is original[key]
        assert actual['ref_latents'][0] is (filtered if name.endswith('low') else reference)
    assert positive['ref_latents'] is negative['ref_latents'] is common['ref_latents']
    assert torch.equal(reference,torch.ones_like(reference))


def test_checked_extraction_rejects_changed_prediction_source():
    # Given the actual pinned source file supplied by the fixture command.
    import os
    from pathlib import Path
    from alg_extract import alg_sample_source
    source=Path(os.environ['SCAIL_SOURCE']).read_text()
    # When the exact original block is extracted and an altered block is attempted.
    patched=alg_sample_source(source)
    # Then the patch is singular and fails closed on a changed model call.
    assert patched.count('noise_pred = alg_predict(')==1
    with pytest.raises(AssertionError):
        alg_sample_source(source.replace('noise_pred_cond = self.model(', 'noise_pred_cond = other_model('))


def test_off_extracted_sampler_matches_original_cpu_loop():
    # Given the real extracted loop and a deterministic CPU scheduler/model fixture.
    import os
    from pathlib import Path
    from types import SimpleNamespace
    from extract import sample_source
    from alg_extract import alg_sample_source
    source=Path(os.environ['SCAIL_SOURCE']).read_text()
    def execute(patched,settings):
        calls=[];final=[];counter=[0]
        class Model:
            def __call__(self,latents,t,**kwargs):
                calls.append(kwargs['tag'])
                return [latents[0]*.01+kwargs['value']]
        class Scheduler:
            def step(self,pred,t,latent,**kwargs):return [latent-pred*.005]
        model=Model();positive={'tag':'c','value':3.0};negative={'tag':'u','value':2.0}
        def predict(latents,t,c,u):
            def branch(name):return model(latents,t=t,**(c if name.startswith('c_') else u))[0]
            return alg.guided_prediction(branch,settings,counter[0],40,5.)
        def completed(*unused):counter[0]+=1
        namespace={'torch':torch,'tqdm':lambda x:x,'self':SimpleNamespace(model=model,device=torch.device('cpu'),rank=0),
                   'offload_model':False,'apply_clean_history':lambda value,history:value,
                   'timesteps':torch.arange(40),'sample_scheduler':Scheduler(),'guide_scale':5.,'seed_g':None,
                   'completed':completed,'complete':lambda x,h:final.append(x[0].clone()),'phase':lambda x:None,'alg_predict':predict}
        exec(compile(patched,'<cpu-real-loop-fixture>','exec'),namespace)
        namespace['sample_func'](torch.ones(2,3),positive,negative,None)
        return final[0],calls,counter[0]
    # When original, OFF and identity-filter modes run the actual extraction.
    baseline=execute(sample_source(source,separated=True),alg.AlgSettings(enabled=False))
    off=execute(alg_sample_source(source),alg.AlgSettings(enabled=False))
    identity=execute(alg_sample_source(source),alg.AlgSettings(ratio=1))
    # Then output values and 80-call order are byte-identical with 40 steps.
    for actual in (off,identity):
        assert torch.equal(actual[0],baseline[0]) and actual[1:]==baseline[1:]
    assert baseline[1]==['c','u']*40 and baseline[2]==40


def test_parent_receipt_binds_original_code_not_new_execution_manifest(tmp_path):
    # Given immutable actual B013 P, its own code/input receipts and a new worker.
    import json
    import os
    import shutil
    from pathlib import Path
    from contracts import verify_cache_receipt
    actual=Path(os.environ['B015_ROOT'])
    shutil.copytree(actual/'configs',tmp_path/'configs')
    for name in ('artifacts','parent_records'):(tmp_path/name).symlink_to(actual/name,target_is_directory=True)
    (tmp_path/'PREREGISTERED_CODE.json').write_text('{"experiment":"B-015"}')
    # When the parent contract is verified independently of current execution code.
    receipt=verify_cache_receipt(tmp_path)
    # Then immutable provenance passes, while modified parent provenance is rejected.
    assert receipt['experiment']=='B-013'
    parent=tmp_path/'configs/parent_code.json'
    changed=json.loads(parent.read_text());changed['experiment']='B-015'
    parent.write_text(json.dumps(changed))
    with pytest.raises(AssertionError):verify_cache_receipt(tmp_path)


def test_pair_gate_rejects_changed_control_or_unchanged_driving():
    # Given a controlled text leaf and an explicitly changed driving leaf.
    from pair_audit import check_pair_leaf
    moving=torch.ones(2);still=moving.clone();changed=['root.arg_c.pose_latents[0]']
    # When an unregistered control changes or driving is accidentally unchanged.
    with pytest.raises(AssertionError):check_pair_leaf('root.noise',moving,still+1e-6,changed)
    with pytest.raises(AssertionError):check_pair_leaf(changed[0],moving,still,changed)
    # Then the intended changed driving leaf is accepted without relaxing controls.
    assert check_pair_leaf(changed[0],moving,still+1,changed) is False


def test_still_filter_rejects_MOV_parent_substitution():
    # Given the actual STILL-parent sidecar and immutable MOV comparison policy.
    import json
    import os
    from pathlib import Path
    root=Path(os.environ['B015_ROOT'])
    sidecar=json.loads((root/'artifacts/filtered_reference.json').read_text())
    receipt=json.loads((root/'artifacts/conditions_receipt.json').read_text())
    policy=json.loads((root/'configs/pair_baseline.json').read_text())
    # When actual parent and filter contracts are compared.
    parent=sidecar['provenance']['parent_cache_sha256']
    # Then values match MOV but parent binding must be the different STILL cache.
    assert parent==receipt['hashes']['conditions.safetensors'] and parent!=policy['old_cache_sha256']
    assert sidecar['provenance']['filtered_ref_sha256']==policy['filtered_ref_value_sha256']
