# E2 runtime differences and preflight

Official code `e6c2cf11843470b08491745947abcba9c3c6b079`, model revision `de8c4621d3ac75cc33efe3db8deaed2023e9ac8c`.

- ARM64 Python3.12.3; existing torch2.14.0+cu130 is read from the existing Comfy environment. No torch package installed or replaced. Official H100/CUDA12.4/torch2.5.1 environment was not reproduced.
- An isolated E2 venv contains transformers4.57.3,tokenizers0.22.1,huggingface-hub0.36.0,diffusers0.35.2,accelerate0.34.2,imageio-ffmpeg0.6.0,VeOmni0.1.11. All explicit package installs used --no-deps. Two existing research/Comfy site-package directories are linked by a local .pth; system-site-packages is disabled. This resolved torch discovery and unrelated distro OpenSSL/boto3 conflicts without editing the shared environment.
- No usable ARM64 decord distribution was present. `decord_compat.py` reads metadata with existing PyAV19.0.1 and RGB frames with existing FFmpeg. All73 fallback frames match the same FFmpeg RGB bytes (SHA2560856067deae53718b4d8116f53a62fbc1993ded77483bcf2018405886534a7e9). Equality to an actual decord execution is UNVERIFIED. No interpolation/resampling or corrupt-frame replacement is added.
- `e2_runtime.patch` changes two reader imports and defers full-planner-only imports until that path is selected. This avoids an irrelevant Qwen FlashAttention import exception for renderer-only inference. The entire BerniniRendererPipeline AST is unchanged. Real `import bernini.cli` succeeds after the patch. No external planner endpoint was called.
- E2 source media is FFV1 lossless,73frames24fps,1280×720→853×480 Lanczos→832×480 crop-left10. Anchor uses the same transform. This is input preparation, not output postprocessing.
- Historical amendment2 state: `e2_entry.py` preserves official defaults and instruments scheduler/shared_step for one-step timing. Four CPU fixture tests pass; this is not a real model execution. No timing probe or video was run because simultaneous static weights exceed the frozen64GiB worker cap. See E2_MEMORY_PREFLIGHT.json.

That historical amendment2 block was not a planner requirement, observed OOM, disk shortage or measured slowness. Partial download files and isolated environment are retained. Common guards and existing model environments remain unchanged.

## Amendment4: pre-materialized BF16 storage

The authorized CPU conversion completed on 2026-11-03 at 16:13:39 UTC in 298.342314 seconds using torch 2.14.0+cu130. It created a separate BF16 storage copy of both DiT experts, with originals retained. All 24 shards and all 2190 tensors passed atomic-save readback and bitwise equality against each original tensor cast with `to(torch.bfloat16)`. Source SHA256 matched before/after conversion; source and converted hashes are in `E2_BF16_CONVERSION.json`. Tensor payload changed from 114,307,932,672 bytes to 57,153,966,336 bytes. These are storage bytes, not a measured runtime memory reduction.

The official loader already requests BF16: `bernini/models/renderer.py:136` and `bernini/models/wan_diffusion.py:153`. The released root config has no dtype override. The converted snapshot retains config files and reuses T5, VAE, tokenizer and scheduler through symlinks; only DiT shard storage and index `total_size` changed. Source module hashes and exact line references are recorded in the conversion JSON.

The amendment4 probe config selects the converted snapshot. Static inspection of `bernini/pipeline.py:82` and `:224` confirms `_prefer_local_dir` selects that root: the released hub-id is absent as a local path in the actual worker cwd, while required tokenizer/text_encoder/vae entries exist in the converted root. This is static routing evidence; it does not claim a completed inference or sampler probe. Runtime execution and guard outcomes remain in the separate execution ledger.
