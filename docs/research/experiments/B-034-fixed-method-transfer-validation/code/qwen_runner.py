# /// script
# requires-python = ">=3.12"
# dependencies = ["torch", "diffusers==0.41.0", "transformers==5.20.1", "pydantic>=2", "pillow", "numpy"]
# ///
"""One frozen fixed-case official multi-image run; no retry or extra forward."""
# Run: locked Python qwen_runner.py PRIVATE_B034_ROOT
from __future__ import annotations
import json
import os
import sys
import time
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from safetensors.torch import save_file
from diffusers import QwenImageEditPlusPipeline
from diffusers.pipelines.qwenimage.pipeline_qwenimage_edit_plus import calculate_dimensions, CONDITION_IMAGE_SIZE, VAE_IMAGE_SIZE
from qwen_contract import ImageContract
from qwen_freeze import verify_freeze
from qwen_observe import observe, tensor_hash, tiny_cuda, file_hash


def main() -> None:
    """Run at most two reserved calls in fixed order under the external memory/deadline guard."""
    root = Path(sys.argv[1]).resolve()
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    verify_freeze(root)
    contract = ImageContract.model_validate_json((root/'inputs/INPUT_CONTRACT.json').read_text())
    contract.check_order()
    for case in contract.cases:
        contract.checked_images(root,case)
        assert not (root/'anchors'/case.case_id/'attempt.json').exists(), 'Duplicate attempt prohibited'
    global_record = root/'environment/reports/qwen-run.json'
    with global_record.open('x') as stream:
        json.dump({'status':'LOADING','started':time.time(),'image_attempts':0},stream)
    anchor = tiny_cuda(root)
    observe(root,'load_cpu_begin')
    pipeline = QwenImageEditPlusPipeline.from_pretrained(root/'models/qwen-image-edit-2511', torch_dtype=torch.bfloat16, low_cpu_mem_usage=True, local_files_only=True)
    observe(root,'load_cpu_end')
    for name in ('text_encoder','vae','transformer'):
        observe(root,name+'_cuda_begin')
        getattr(pipeline,name).to('cuda')
        observe(root,name+'_cuda_end')
    pipeline.set_progress_bar_config(disable=False)
    pipeline.transformer.set_attention_backend('native')
    module_report = {name:{'class':type(getattr(pipeline,name)).__name__,'parameter_bytes':sum(p.numel()*p.element_size() for p in getattr(pipeline,name).parameters()),'dtype':str(next(getattr(pipeline,name).parameters()).dtype),'device':str(next(getattr(pipeline,name).parameters()).device)} for name in ('text_encoder','vae','transformer')}
    (root/'environment/reports/loaded-modules.json').write_text(json.dumps(module_report,indent=2))
    for case in contract.cases:
        images = contract.checked_images(root,case)
        output = root/'anchors'/case.case_id
        output.mkdir(parents=True,exist_ok=True)
        effective = output/'effective-inputs'
        effective.mkdir(exist_ok=True)
        input_rows = []
        for index,image in enumerate(images,1):
            ratio = image.width/image.height
            vision_wh = calculate_dimensions(CONDITION_IMAGE_SIZE,ratio)
            vae_wh = calculate_dimensions(VAE_IMAGE_SIZE,ratio)
            pipeline.image_processor.resize(image,vision_wh[1],vision_wh[0]).save(effective/f'image{index}-vision.png')
            vae_pixels = pipeline.image_processor.preprocess(image,vae_wh[1],vae_wh[0]).unsqueeze(2)
            Image.fromarray(((vae_pixels[0,:,0].permute(1,2,0).numpy()+1)*127.5).round().clip(0,255).astype(np.uint8)).save(effective/f'image{index}-vae.png')
            input_rows.append({'input_index':index,'native_wh':list(image.size),'vision_wh':vision_wh,'vae_wh':vae_wh,'vae_shape':list(vae_pixels.shape),'vae_normalized_sha256':tensor_hash(vae_pixels),'pixel_min':float(vae_pixels.min()),'pixel_max':float(vae_pixels.max())})
            del vae_pixels
        generator = torch.Generator(device='cpu').manual_seed(contract.image_seed)
        record = {'case_id':case.case_id,'status':'ATTEMPTED','started':time.time(),'input_order':['image1.png','image2.png'],'input_sha256':[case.files[name].sha256 for name in case.image_order],'equivalent_preprocess_exports':input_rows,'generator_state_before':tensor_hash(generator.get_state()),'steps':0,'transformer_forwards':0,'attention_backend':'native','model_revision':'6f3ccc0b56e431dc6a0c2b2039706d7d26f22cb9'}
        with (output/'attempt.json').open('x') as stream:
            json.dump(record,stream,indent=2)
        def before_forward(module: torch.nn.Module, args: tuple, kwargs: dict[str,torch.Tensor]) -> None:
            """Observe the first actual branch input without additional model work."""
            record['transformer_forwards'] += 1
            if record['transformer_forwards'] <= 2:
                row = {'forward':record['transformer_forwards'],'hidden_shape':list(kwargs['hidden_states'].shape),'hidden_sha256':tensor_hash(kwargs['hidden_states']),'text_shape':list(kwargs['encoder_hidden_states'].shape),'text_sha256':tensor_hash(kwargs['encoder_hidden_states'])}
                with (output/'first-branches.jsonl').open('a') as stream:
                    stream.write(json.dumps(row)+'\n')
                observe(root,case.case_id+'_forward_'+str(record['transformer_forwards']))
        def step_callback(pipe: QwenImageEditPlusPipeline, index: int, timestep: torch.Tensor, values: dict[str,torch.Tensor]) -> dict[str,torch.Tensor]:
            """Record actual completion and preserve final packed latent losslessly."""
            record['steps'] = index+1
            assert torch.isfinite(values['latents']).all().item(), 'Non-finite latent'
            observe(root,case.case_id+'_step_'+str(index+1))
            (output/'progress.json').write_text(json.dumps(record,indent=2))
            if index == 39:
                packed = values['latents'].detach().cpu().contiguous()
                temporary = output/'final-image-latent.safetensors.tmp'
                save_file({'packed_latent':packed},str(temporary))
                temporary.replace(output/'final-image-latent.safetensors')
                record['final_packed_latent'] = {'shape':list(packed.shape),'dtype':str(packed.dtype),'tensor_sha256':tensor_hash(packed),'file_sha256':file_hash(output/'final-image-latent.safetensors')}
                del packed
            return values
        def encoder_input(module: torch.nn.Module, args: tuple, kwargs: dict[str,torch.Tensor]) -> None:
            """Capture existing encoder calls, without recomputing any encoding."""
            tensors = {}
            for key,value in kwargs.items():
                if torch.is_tensor(value):
                    tensors[key] = {'shape':list(value.shape),'dtype':str(value.dtype),'sha256':tensor_hash(value)}
            if args and torch.is_tensor(args[0]):
                tensors['arg0'] = {'shape':list(args[0].shape),'dtype':str(args[0].dtype),'sha256':tensor_hash(args[0])}
            with (output/'actual-encoder-inputs.jsonl').open('a') as stream:
                stream.write(json.dumps({'module':type(module).__name__,'tensors':tensors})+'\n')
        handle = pipeline.transformer.register_forward_pre_hook(before_forward,with_kwargs=True)
        encoder_handles = [module.register_forward_pre_hook(encoder_input,with_kwargs=True) for module in (pipeline.text_encoder,pipeline.vae.encoder)]
        try:
            with torch.inference_mode():
                result = pipeline(image=images,prompt=case.prompt,negative_prompt=contract.negative_prompt,height=512,width=896,num_inference_steps=40,true_cfg_scale=4.0,guidance_scale=1.0,num_images_per_prompt=1,generator=generator,output_type='np',callback_on_step_end=step_callback)
            raw = result.images[0]
            assert raw.shape == (512,896,3) and np.isfinite(raw).all()
            assert record['steps'] == 40 and record['transformer_forwards'] == 80
            np.save(output/'raw-image.npy',raw)
            Image.fromarray((raw*255).round().clip(0,255).astype(np.uint8)).save(output/'A0.png')
            record.update(status='COMPLETED',finished=time.time(),shape=list(raw.shape),finite=True,raw_sha256=file_hash(output/'raw-image.npy'),png_sha256=file_hash(output/'A0.png'),generator_state_after=tensor_hash(generator.get_state()))
            (output/'result.json').write_text(json.dumps(record,indent=2))
            observe(root,case.case_id+'_decoded_saved')
            del raw,result
        finally:
            handle.remove()
            for encoder_handle in encoder_handles:
                encoder_handle.remove()
            (output/'last-observed.json').write_text(json.dumps(record,indent=2))
    del pipeline,anchor
    torch.cuda.empty_cache()
    observe(root,'pipeline_released')
    global_record.write_text(json.dumps({'status':'COMPLETED','finished':time.time(),'image_attempts':len(contract.cases)},indent=2))

if __name__ == '__main__':
    main()
