# V-003 pinned LTX execution contract

The inspected Spark checkout is clean at `e98f6d927d83c92ef2be6aec76c8440b19306e39`. No upstream code changes, installation, model import, or GPU execution were performed for this inspection.

## Conditioning and the two stages

Source paths below are relative to the pinned LTX-2 repository.

- `packages/ltx-pipelines/src/ltx_pipelines/utils/args.py:189`: `ImageAction` accepts repeated `--image PATH FRAME_IDX STRENGTH [auto|replace|guide] [CRF]` and appends each item. `auto` replaces frame zero and guides later pixel frames.
- `utils/types.py:344`: replacement is valid only at zero or `1 + temporal_stride * k`. Pixel replacement maps to latent index zero, or `1 + (frame - 1) // temporal_stride` (`:355`). Guide accepts an arbitrary in-clip pixel index (`:152`).
- `utils/types.py:169`: replacement lowers to `VideoConditionByLatentIndex`; guide lowers to `VideoConditionByKeyframeIndex`.
- `packages/ltx-core/src/ltx_core/conditioning/types/keyframe_cond.py:10`: guide appends clean keyframe tokens with temporal positions; it does not overwrite the target latent plane. Strength one makes those additional tokens clean. `latent_cond.py:9` replaces the designated target clean-latent span and sets its denoise mask to `1 - strength`.
- `ic_lora.py:527`: images are encoded for both stages; reference video is included only where `apply_ic_lora` is true. The stage loop rebuilds conditionings at `:764`, at that stage's spatial resolution.
- `ic_lora.py:131`: the default first stage is half resolution with IC-LoRA, followed by full resolution without IC-LoRA. `utils/constants.py:17` and `:20` define the unchanged 8-step and 3-step sigma schedules. The inherited V-001 observer requires 11 completed steps and 11 denoiser calls, with grid lengths 9 and 4.
- `utils/constants.py:36`: the unchanged model-default image conditioning compression is CRF33. The original image remains preserved; official loading recompresses the conditioning internally. This is also the V-001 default.

## K2 official path

The IC-LoRA CLI requires a reference-video flag (`ic_lora.py:819`), but the official Python `ICLoraPipeline` accepts empty `loras` and `video_conditioning` lists. `chunks/conditionings.py:108` returns no reference items for an empty list; `ic_lora.py:771` then supplies no LoRA. The same two-stage recipe, image conditioning, scheduler and decode remain in use. V-003 uses this API for all variants, avoiding a separate pipeline for K2. The LoRA mapping is the same `LTXV_LORA_COMFY_RENAMING_MAP` used by official `LoraAction` (`utils/args.py:262`). No dummy video, zero-strength substitute, or upstream patch is used.

## Entry and private schema

`code/ltx_entry.py --config PRIVATE_RUNTIME.json --cpu-only` validates without importing torch or the engine. Remove `--cpu-only` only under the approved Spark heavy guard.

Private runtime keys: `scene_config`, `variant`, `seed`, `anchors` (list of `{frame,path}` accepted transformed images), `checkpoint`, `upsampler`, `gemma`, `lora`, `canny`, `engine_root`, `observer_path`, `output`, `receipt`, `ffprobe`. Every runtime path is absolute and remains private. `observer_path` identifies the preserved V-001 `e1_entry.py`; only its accounting classes/functions are imported, not its old scene validator. Outputs and receipts must not exist when starting.

Scene configuration supplies all scene choices. Machine fields needed under `generation.variants.<id>` are `image_binding`, `strength`, and for replacement `replace_frames`; existing `ic_lora_canny` controls both LoRA and reference presence. `generation.runtime_contract` supplies `engine_commit`, `spatial_multiple`, `temporal_stride`, `scheduler_steps`, `stage_sigma_lengths`. The wrapper derives nearest accepted anchor assignment, choosing the earlier anchor for an exact tie, and records signed `source_frame - target_frame` offsets.

The API uses the same model paths, BF16 default, unquantized/no compilation/no offload defaults, automatic tiled VAE, no prompt enhancement, no generated-keyframe decode mode, and official MP4 encoding defaults as V-001. It adds no model forward. CPU validation checks the pinned checkout and frame geometry; the heavy path also checks the actual imported pipeline source is inside that checkout.

Four CPU tests cover guide positions, nearest replacement assignment/offset, invalid causal replacement, and duplicate anchor rejection. This was the pre-generation CPU audit. All six guarded model runs subsequently completed with 11 scheduler steps and 11 denoiser calls each; the heavy source-import check passed inside each run. Original MP4 dimensions and frame counts were verified during CPU decoding. SAM, POST and final package verification are tracked separately in RUNS/METRICS/DELIVERY. No new dependencies were installed; local `ruff`/`basedpyright` executables were unavailable.
