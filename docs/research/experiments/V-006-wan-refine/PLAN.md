# V-006 preregistration

Recorded 2026-11-06T14:01:52.349448+00:00, before model load, download, conversion or generation. Parent a95a66b3a5c92d7057dc9bd8f4d1aa9d7448f55f.

## Contract
The attached scene configuration is authoritative for all scene values. Preserve V-004 S2-s1 RAW, Lab scale and original evidence. Execute W1-a, intermediate uncompressed delivery, W1-b, W2, CPU reinsertion, measurements, SAMPLE parent links, final delivery. Maximum3 generations, no imagegen/training/quality retry. Six hours excluding waits/download/conversion, last30minutes delivery. Scheduler/expert contract resolved using the official DiffSynth example defaults before downstream work.

## Intake
Research branch clean at parent; separate feature worktree preserved. Spark reachable, same recorded boot as V-005; BIOS5.36_0ACUM08. hw.csv advancing; no GPU compute processes observed at intake. MemAvailable123638161408bytes, disk available441900158976bytes. These snapshots do not constitute heavy admission. Recheck all guards before heavy work.

## Pre-generation sigma conflict
Status PREREGISTERED_DIFFSYNTH_DEFAULTS. Official Wan T2V-A14B defaults are UniPC,shift12,40steps,CFG3(low)/4(high),boundary0.875. The preferred local DiffSynth pipeline defaults are Euler flow,shift5,50steps,CFG5. Its denoising_strength is pre-shift noise, not actual sigma or a fraction of a sliced50-step schedule. Both options produce distinct start sigmas, so the identical-sigma stop is NOT triggered.

CPU evaluation of the existing scheduler (no model loaded):

|Shift/steps|strength|actual start sigma|steps at/above boundary|
|---|---|---|---|
|12/40|0.35|0.8659793734550476|0|
|12/40|0.55|0.936170220375061|14|
|5/50|0.35|0.7291666269302368|0|
|5/50|0.55|0.859375|0|

The shift12 rows evaluate DiffSynth's grid using Wan's shift/step defaults; they do not claim that official UniPC was executed. Official Wan has no native v2v strength convention to silently substitute. W1-b cannot use this shift12 grid with only the low-noise expert. Choosing DiffSynth defaults rather than official model defaults changes experiment settings, so the user-preferred official DiffSynth example resolves the interpretation: use Euler/50steps/shift5/CFG5. Do not clamp sigma, modify strengths, force low expert above boundary, or load high expert.

Scheduler file hash43abe34773144e7f3ce660d40bf5f3ee25fe5538cbc7654c3992b9e40a761486. CPU module loaded directly with CUDA_VISIBLE_DEVICES empty; no pipeline/model import.

## Remaining validation
Check original T2V weight provenance; Bernini adapted weights are not substitutes. Inspect tensor headers before conversion; preserve originals and verify bf16 casts bitwise. Keep200GiB disk free. Establish112GiB admission and inherited guards, hwlog and NVRM watch. Record actual latent shapes rather than claiming inferred dimensions as measured. Project time from first actual step, stop under approved time rule.

Static W2 review found a possible multi-reference v2v latent-length inconsistency in the existing DiffSynth input embedding path; this is unverified and requires shape validation before support is claimed. No unsupported ref merge/drop is authorized.

## Evaluation and handoff
Use frozen V005 metrics as reference only, no automatic winner. Preserve RAW33frames and separately label both CPU reinsertion derivatives. Intermediate delivery follows W1-a; no W1-a output yet. Per-output SAMPLE links S2-s1 parent. HUMAN_REVIEW_PENDING, temporal UNVERIFIED. No follow-up jobs.

## Sources
https://github.com/Wan-Video/Wan2.2/blob/main/wan/configs/wan_t2v_A14B.py
https://github.com/modelscope/DiffSynth-Studio

## Resolved before execution
Official DiffSynth A14B example calls the pipeline without scheduler overrides. Therefore use its defaults, not Wan CLI defaults; the user prioritizes this runner. W1-a/W1-b actual start sigma0.7291666269302368/0.859375,50steps each, both below0.875. No settings were selected from generated results. Source: https://github.com/modelscope/DiffSynth-Studio/blob/08fdc0da8f41426885d9432e9007e6e460a4c30d/examples/wanvideo/model_inference/Wan2.2-T2V-A14B.py

## W2 support gate, before any model execution
CPU fixture executes the existing input-video unit body with shape doubles: single reference input/noiseT10/10 passes; requestedtwo references input/noiseT10/11 mismatch. W2 NOT_SUPPORTED underexplicitworkorderbranch, noW2download/load/generation. SeeW2_SUPPORT.md. W1remainsindependent.
