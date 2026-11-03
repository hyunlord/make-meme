# E2 runtime differences and preflight

Official code `e6c2cf11843470b08491745947abcba9c3c6b079`, model revision `de8c4621d3ac75cc33efe3db8deaed2023e9ac8c`.

- ARM64 Python3.12.3; existing torch2.14.0+cu130 is read from the existing Comfy environment. No torch package installed or replaced. Official H100/CUDA12.4/torch2.5.1 environment was not reproduced.
- An isolated E2 venv contains transformers4.57.3,tokenizers0.22.1,huggingface-hub0.36.0,diffusers0.35.2,accelerate0.34.2,imageio-ffmpeg0.6.0,VeOmni0.1.11. All explicit package installs used --no-deps. Two existing research/Comfy site-package directories are linked by a local .pth; system-site-packages is disabled. This resolved torch discovery and unrelated distro OpenSSL/boto3 conflicts without editing the shared environment.
- No usable ARM64 decord distribution was present. `decord_compat.py` reads metadata with existing PyAV19.0.1 and RGB frames with existing FFmpeg. All73 fallback frames match the same FFmpeg RGB bytes (SHA2560856067deae53718b4d8116f53a62fbc1993ded77483bcf2018405886534a7e9). Equality to an actual decord execution is UNVERIFIED. No interpolation/resampling or corrupt-frame replacement is added.
- `e2_runtime.patch` changes two reader imports and defers full-planner-only imports until that path is selected. This avoids an irrelevant Qwen FlashAttention import exception for renderer-only inference. The entire BerniniRendererPipeline AST is unchanged. Real `import bernini.cli` succeeds after the patch. No external planner endpoint was called.
- E2 source media is FFV1 lossless,73frames24fps,1280×720→853×480 Lanczos→832×480 crop-left10. Anchor uses the same transform. This is input preparation, not output postprocessing.
- `e2_entry.py` preserves official defaults and instruments scheduler/shared_step for one-step timing. Four CPU fixture tests pass; this is not a real model execution. No timing probe or video was run because simultaneous static weights exceed the frozen64GiB worker cap. See E2_MEMORY_PREFLIGHT.json.

The current block is not a planner requirement, observed OOM, disk shortage or measured slowness. Partial download files and isolated environment are retained. Common guards and existing model environments remain unchanged.
