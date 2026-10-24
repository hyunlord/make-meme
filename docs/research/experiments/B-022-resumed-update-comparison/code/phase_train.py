# /// script
# requires-python = ">=3.12"
# dependencies = ["torch", "safetensors", "pydantic"]
# ///
"""Run via run_phase.py: resume one stored trajectory, bounded diagnostics and updates."""
from pathlib import Path
import gc
import hashlib
import json
import time
import torch
from safetensors.torch import load_file
from artifacts import atomic_json
from budget_contract import prediction_delta,save_checkpoint
from fm_contract import fixed_tuples,velocity_mse,check_parity
from lora_component import load_adapters
from resume_contract import checkpoint,restore,named_parameters,lowrank_action
from runtime_observe import phase
from tail_setup import prepare,hashes,digest,atomic_adapter,fa_nodes


def run(root:Path,cfg:dict)->None:
    env=prepare(root,cfg);parent=(root/'resume_parent').resolve()
    consumer=json.loads((root/'configs/consumer.json').read_text())
    assert hashlib.sha256((parent/'artifacts/restart-020.json').read_bytes()).hexdigest()==consumer['restart_sidecar_sha256']
    assert hashlib.sha256((parent/'artifacts/adapter-020.json').read_bytes()).hexdigest()==consumer['adapter20_sidecar_sha256']
    tree,checkpoint_meta=checkpoint(parent/'artifacts/restart-020.safetensors',consumer['restart_sha256'])
    assert checkpoint_meta['provenance']['experiment']=='B-021'
    assert checkpoint_meta['provenance']['code_sha256']==hashlib.sha256((parent/'PREREGISTERED_CODE.json').read_bytes()).hexdigest()
    old_path=env.producer/'artifacts/adapter-final.safetensors'
    new_path=parent/'artifacts/adapter-020.safetensors'
    assert hashlib.sha256(new_path.read_bytes()).hexdigest()==consumer['adapter20_sha256']
    old_values=load_file(str(old_path),device='cpu');new_values=load_file(str(new_path),device='cpu')
    assert all(torch.equal(value,new_values[name.replace('.','.lora_')]) for name,value in tree['adapter'].items())
    atomic_json(root/'reports/lowrank-action.json',lowrank_action(old_values,new_values))
    block,head,adapters=env.build();base_before=(hashes(block),hashes(head))
    predict=env.make_predict(block,head)
    parameters=list(named_parameters(adapters).values())
    optimizer=torch.optim.AdamW(parameters,lr=1e-4,weight_decay=0)
    evals=0;updates=20;backwards=0;rows=[];snapshots={};head_gradients={}
    provenance={'experiment':'B-022','label':'PRIVATE_ONE_CLIP_FM_OVERFIT_NOT_PRODUCTION','code_sha256':hashlib.sha256((root/'PREREGISTERED_CODE.json').read_bytes()).hexdigest(),'producer':'B-020','resume_parent':'B-021','restart_sha256':consumer['restart_sha256'],'adapter20_sha256':consumer['adapter20_sha256']}
    def evaluate(tuple_id):
        nonlocal evals
        assert evals<40
        evals+=1
        atomic_json(root/'reports/counters.json',{'tail_evaluations_reserved':evals,'updates':updates,'diagnostic_backward':backwards})
        with torch.no_grad():pred,target=predict(tuple_id)
        assert torch.isfinite(pred).all() and torch.isfinite(target).all()
        return pred,target
    def snapshot(step):
        current={};held=None
        for spec in fixed_tuples():
            pred,target=evaluate(spec.tuple_id)
            current[spec.tuple_id]={'loss':float(velocity_mse(pred,target)),'delta':prediction_delta(pred,env.cpu[spec.tuple_id]['baseline_velocity'])}
            if spec.tuple_id=='holdout':held=pred.detach().cpu()
        snapshots[str(step)]=current
        atomic_json(root/'reports/evaluation-snapshots.json',snapshots)
        assert held is not None
        return held
    def hook(_module,grad_input,_grad_output):
        value=grad_input[0];assert value is not None and torch.isfinite(value).all()
        head_gradients['input_norm']=float(value.float().norm())
    try:
        started=time.monotonic();old_predictions={};new_predictions={};comparison={}
        load_adapters(old_path,adapters)
        for spec in fixed_tuples():
            pred,target=evaluate(spec.tuple_id);old_predictions[spec.tuple_id]=pred.cpu()
        binding=restore(tree,adapters,optimizer)
        atomic_json(root/'reports/restored-binding.json',binding)
        for spec in fixed_tuples():
            pred,target=evaluate(spec.tuple_id);new_predictions[spec.tuple_id]=pred.cpu()
            comparison[spec.tuple_id]={'b021_vs_b020':prediction_delta(pred,old_predictions[spec.tuple_id]),'b021_vs_off':prediction_delta(pred,env.cpu[spec.tuple_id]['baseline_velocity']),'b020_vs_off':prediction_delta(old_predictions[spec.tuple_id],env.cpu[spec.tuple_id]['baseline_velocity']),'b020_loss':float(velocity_mse(old_predictions[spec.tuple_id],target.cpu())),'b021_loss':float(velocity_mse(pred,target))}
        atomic_json(root/'reports/velocity-comparison.json',comparison)
        assert (hashes(block),hashes(head))==base_before
        del block,head,adapters,parameters,optimizer,predict,pred,target
        block=None;head=None
        gc.collect();torch.cuda.empty_cache()
        block,head,adapters=env.build();parameters=list(named_parameters(adapters).values())
        optimizer=torch.optim.AdamW(parameters,lr=1e-4,weight_decay=0)
        predict=env.make_predict(block,head);restore(tree,adapters,optimizer)
        functional={}
        for spec in fixed_tuples():
            pred,target=evaluate(spec.tuple_id)
            parity=check_parity(pred,new_predictions[spec.tuple_id].to('cuda'));assert parity['passed']
            functional[spec.tuple_id]={'reload':parity}
        for layer in adapters.values():layer.enabled=False
        for spec in fixed_tuples():
            pred,target=evaluate(spec.tuple_id)
            parity=check_parity(pred,env.cpu[spec.tuple_id]['baseline_velocity'].to('cuda'));assert parity['passed']
            functional[spec.tuple_id]['off']=parity
        for layer in adapters.values():layer.enabled=True
        atomic_json(root/'reports/function-parity20.json',functional)
        handle=head.register_full_backward_hook(hook)
        repetitions=[];previous=None
        for repeat in range(3):
            restore(tree,adapters,optimizer);optimizer.zero_grad(set_to_none=True)
            assert evals<40
            evals+=1
            atomic_json(root/'reports/counters.json',{'tail_evaluations_reserved':evals,'updates':updates,'diagnostic_backward':backwards})
            pred,target=predict('train_2')
            loss=velocity_mse(pred,target);nodes=fa_nodes(loss);assert nodes==3 and torch.isfinite(loss)
            backwards+=1
            atomic_json(root/'reports/counters.json',{'tail_evaluations_reserved':evals,'updates':updates,'diagnostic_backward':backwards})
            loss.backward();torch.cuda.synchronize()
            gradients={name:p.grad.detach().cpu().clone() for name,p in named_parameters(adapters).items() if p.grad is not None}
            assert len(gradients)==4 and all(torch.isfinite(g).all() for g in gradients.values())
            assert head_gradients['input_norm']>0
            assert all(p.grad is None for p in list(block.parameters())+list(head.parameters()) if not p.requires_grad)
            current={'prediction':pred.detach().cpu(),'gradients':gradients}
            row={'repeat':repeat,'loss':float(loss.detach()),'fa_backward_nodes':nodes,'head_input_gradient_norm':head_gradients['input_norm'],'gradient_norms':{k:float(v.norm()) for k,v in gradients.items()}}
            if previous is not None:row['vs_first']={'prediction':prediction_delta(current['prediction'],previous['prediction']),'gradients':{k:prediction_delta(v,previous['gradients'][k]) for k,v in gradients.items()}}
            repetitions.append(row)
            if previous is None:previous=current
            assert all(torch.equal(p.detach().cpu(),tree['adapter'][name]) for name,p in named_parameters(adapters).items())
            del pred,target,loss,current,gradients
            atomic_json(root/'reports/repeatability.json',{'scope':'entire tail+head, not FA2-only causality','repeats':repetitions,'diagnostic_backward':backwards,'tail_evaluations':evals})
            assert time.monotonic()-started<1800,'DIAGNOSTIC_DEADLINE'
        restore(tree,adapters,optimizer)
        atomic_json(root/'reports/resume-before-update21.json',{'binding':restore(tree,adapters,optimizer),'step':20,'cursor':2,'next_tuple':'train_2','diagnostic_seconds':time.monotonic()-started,'rng_restored':True})
        save_checkpoint(root/'artifacts',adapters,optimizer,20,provenance)
        atomic_adapter(root/'artifacts/adapter-020.safetensors',adapters,provenance)
        snapshot(20)
        restore(tree,adapters,optimizer)
        holdout_prediction=None
        for index in range(20,100):
            optimizer.zero_grad(set_to_none=True);spec=fixed_tuples()[index%3]
            old=[p.detach().clone() for p in parameters]
            pred,target=predict(spec.tuple_id);loss=velocity_mse(pred,target)
            assert torch.isfinite(loss);nodes=fa_nodes(loss);assert nodes==3
            loss.backward();torch.cuda.synchronize()
            gradients={name:float(p.grad.float().norm()) for name,p in named_parameters(adapters).items() if p.grad is not None}
            assert len(gradients)==4 and all(p.grad is not None and torch.isfinite(p.grad).all() for p in parameters)
            assert all(p.grad is None for p in list(block.parameters())+list(head.parameters()) if not p.requires_grad)
            assert head_gradients['input_norm']>0
            optimizer.step();updates+=1
            row={'update':updates,'additional_update':updates-20,'tuple_id':spec.tuple_id,'loss':float(loss.detach()),'gradient_norms':gradients,'parameter_delta':{name:prediction_delta(p,prior) for (name,p),prior in zip(named_parameters(adapters).items(),old)},'base_grad_none':True,'fa_backward_nodes':nodes,'head_input_gradient_norm':head_gradients['input_norm'],'cuda_allocated':torch.cuda.memory_allocated(),'cuda_peak':torch.cuda.max_memory_allocated()}
            rows.append(row)
            atomic_json(root/'reports/train-progress.json',{'updates':rows,'tail_evaluations':evals,'diagnostic_backward':backwards})
            atomic_adapter(root/'artifacts/adapter-last-completed.safetensors',adapters,{**provenance,'completed_updates':str(updates)})
            assert all(torch.isfinite(p).all() for p in parameters)
            assert all(float(optimizer.state[p]['step'])==updates for p in parameters)
            assert any(not torch.equal(a,p) for a,p in zip(old,parameters))
            phase('train_update_'+str(updates));del pred,target,loss,old
            if updates in (50,100):
                atomic_adapter(root/'artifacts'/f'adapter-{updates:03d}.safetensors',adapters,{**provenance,'completed_updates':str(updates)})
                save_checkpoint(root/'artifacts',adapters,optimizer,updates,provenance)
                holdout_prediction=snapshot(updates)
        assert (hashes(block),hashes(head))==base_before
        atomic_adapter(root/'artifacts/adapter-final.safetensors',adapters,provenance)
        handle.remove();del block,head,adapters,parameters,optimizer,predict
        block=None;head=None
        gc.collect();torch.cuda.empty_cache()
        block,head,adapters=env.build();load_adapters(root/'artifacts/adapter-final.safetensors',adapters)
        predict=env.make_predict(block,head)
        assert holdout_prediction is not None
        pred,target=evaluate('holdout');reload=check_parity(pred,holdout_prediction.to('cuda'));assert reload['passed']
        for layer in adapters.values():layer.enabled=False
        pred,target=evaluate('holdout');off=check_parity(pred,env.cpu['holdout']['baseline_velocity'].to('cuda'));assert off['passed']
        assert updates==100 and evals==33 and backwards==3
        atomic_json(root/'artifacts/training_receipt.json',{'status':'FM_TAIL_UPDATE_RELOAD_PASS','updates':updates,'additional_updates':updates-20,'tail_evaluations':evals,'diagnostic_backward':backwards,'reload':reload,'off':off,'base_unchanged':(hashes(block),hashes(head))==base_before,'adapter_sha256':hashlib.sha256((root/'artifacts/adapter-final.safetensors').read_bytes()).hexdigest(),'prefix_receipt_sha256':hashlib.sha256((env.producer/'artifacts/prefix_receipt.json').read_bytes()).hexdigest(),'code_sha256':provenance['code_sha256'],'producer':'B-020','consumer':'B-022','resume_parent':'B-021','snapshots':snapshots})
    finally:
        base_status=(hashes(block),hashes(head))==base_before if block is not None and head is not None else None
        source_status=all(digest(v)==env.stored[k] for k,v in env.selected.items())
        status='NOT_REACHED' if base_status is None else 'PASS' if base_status and source_status else 'FAIL'
        atomic_json(root/'reports/final-base-check.json',{'status':status,'current_run_only':True,'base_values_unchanged':base_status,'source_storage_unchanged':source_status,'completed_updates':updates,'additional_updates':updates-20,'tail_evaluations':evals,'diagnostic_backward':backwards})
        if base_status is not None:assert base_status and source_status,'BASE_VALUE_CHANGED'
