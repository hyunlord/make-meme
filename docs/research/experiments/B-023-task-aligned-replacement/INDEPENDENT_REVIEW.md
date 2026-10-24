# B-023 independent review

Current status: postruntime technical PASS. The chronological preflight notes below preserve their original pending states. No GPU/model execution by reviewer.

## Read scope

Revised B-023 PLAN and 20261025 B-022 review decision. This is one same-identity natural-motion replacement pilot, not the superseded two-case meme experiment.

## Actual B-020 baseline

The preserved BASE_S adapter-selection receipt records enabled=false and SHA=null. Independently hashed baseline raw_output.pt: `50579b6aa7739de4d4b65d959255d1ba71c980248ad7f52fd91e26ea0dc9d00e`, matching the raw-export receipt. Receipt shape is [3,17,512,896]. Prior CPU preprocessing record describes17frames30fps and exact34/34decoded RGB/mask PNGs. This review has not rerun preprocessing/model inference.

## Actual masks

Read all18 existing lossless PNGs with PIL. Reference mask896x512 has RED37209pixels, WHITE421543pixels, no other colors; SHA `692b19a4935bf1b04f111584346c53b9ba1ca8ba6fd698af144217c620322b00`. All17driving masks are896x512 and contain only exact RED/WHITE. Reference/background semantics are not inferred from JPEG thresholds. No mask/RGB files changed by reviewer.

## Remaining gate

Verify new reference mask preserves all RED support and only WHITE->BLACK; pinned helper reconstructs old cached mask exactly, derives new packed prefix, keeps other14tensor leaves and actual noise/RNG/scheduler unchanged. Both CFG replace_flag=True, vanilla frozen model with no adapters/ALG/manualRoPE override. Runtime trace must demonstrate forwarded mode and official offsets, with no extra forward. One sampler40/80 and one decode maximum, final latent saved first.

Quality and temporal acceptance cannot be established by these CPU/provenance checks. Existing B020/B022 failures remain preserved.

## Preregistration verdict: PASS, no blocking finding

Read actual old/new cache headers and payload on Spark using Python standard library only. All16 tensor payload SHA256 values match their metadata in both files. Only t4/t10 differ. Entire metadata.structure is exactly equal after changing only arg_c/arg_null replace_flag scalars to true: original saved device positions and all other container/scalar contracts are preserved. No CUDA/model operation performed.

CPU derivation receipt reports exact reproduction of original helper-packed prefix and new reference [28,1,64,112] prefix via pinned helper, RED support preserved and WHITE channels removed;14tensor leaves unchanged including noise, generator state, timesteps and sigmas. This is P0, not an encoder rerun.

Reviewed finalized phase_sample: restored flags checked in both branches and each real model prehook;40block q/v remain exact nn.Linear with no LoRA parameter names; no adapter installation, ALG or custom RoPE. First block prehook records firsttwo CFG kwargs without changing values. Actual pinned Spark model_scail2.py lines830–856 agrees with expected official replacement T/H/W offsets (additional_ref count0). All final counters40/80 and finite shape retained; final latent saved before process-separated decode.

run_phase reserves each stage with exclusive attempt.json creation, validates preregistered code/upstream/input/cache hashes and requires previousstage clean exit and COMPLETED. Decoder checks config/counters/condition hash/adapterOFF/experimentID/shape. Runtime guards retain72GiBstart,24GiBrun headroom,swap0 and owned-process isolation. Fixed deadline2026-10-24T19:54Z was still future at review17:02UTC. No retry or new scientific intervention found.

Technical readiness is not successful sampler/decode or visual acceptance. Runtime and quality remain unobserved at this preflight review.

## Postruntime verdict: technical PASS, no blocking finding

Independently recomputed Mac hashes of all7 files listed in artifact-transfer-verification.json; every hash matches. Actual final latent safetensors payload is F32[16,5,64,112], every scalar finite, SHA9b325fef3e4dfebe4622414569bce28e6b6c517d817414d25e08b0f05c79ee8b. Metadata binds40completedsteps/80modelcalls, adapter_enabled=false and derivedcacheSHA6c531c132c359777d5a12fb535189e857321c44fad85b532126570c969eb3dad.

Loaded actual Spark raw_output.pt with existing Torch, weights_only=True and map_location=cpu only. F32[3,17,512,896], finite, range[-1,1], torch.cuda.is_initialized()==False. SHA51045949c0ab0c02ebe3bd18e646185e353c173c2a89e40e8db7a2b8a9736c2f. D receipt reports h264896x512,17frames30/1fps,duration0.566667 and VIDEO_OUTPUT_PASS.

Each PROBE/S/D exclusive attempt record is1,max1,retries0 and corresponding result COMPLETED. P0 and no optimizer/prefix execution. Actual firsttwo CFG block traces match official replacement T0/Href120/Wpose120, referenceT1/additionalrefT0. Actual vanilla-projection gate records activeLoRA0,ALGfalse,manualoverridefalse. Source checks and trace do not substitute for full independent per-layer runtime introspection.

Runtime summary: PROBE5.073963s; S1092.504294s (model-load94.608963s,sampler976.400239s); D15.170234s. Minimum samplerMemAvailable56,563,187,712bytes, CUDApeakallocated36,326,834,176bytes. These are distinct system/allocator quantities, not summed. Allsampledswap0; S cgroup high3197, max/oom/oom_kill0. Allthree terminal services MainPID0/inactive/success and guardreasonservice_exit. Final recorded ownedunits inactive; only preexisting ComfyUI GPU process remains, available95,881,039,872bytes,swap0. This verifies recorded cleanup, not an independently continuous system monitor.

This is output delivery and contract verification only. Reviewer did not visually inspect/replay video; temporal remains UNVERIFIED. Same-identity source copying can appear successful, so cross-ID/reference-necessity/generalization remain NOT_RUN or unestablished. No new GPU/model call, retry, preprocessing, or asset mutation was performed by this review.
