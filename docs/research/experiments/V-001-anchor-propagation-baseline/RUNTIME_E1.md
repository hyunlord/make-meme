# E1 setup and observational entry

Code: `Lightricks/LTX-2` at `e98f6d927d83c92ef2be6aec76c8440b19306e39`.
Setup started 2026-11-03 14:56:35 UTC; its 90-minute deadline is 16:26:35 UTC.
This note records preparation, not a successful model run.

The dedicated E1 environment reads the existing research and ComfyUI Python
site-packages through an explicit `.pth`. It does not replace their files.
Torch remains `2.14.0+cu130`, torchvision `0.29.0+cu130`.
Local overlays, all installed with `--no-deps`:

- transformers 5.14.1 and tokenizers 0.22.1 (official LTX dependency range);
- colour-science 0.4.7, cloudpickle 3.1.2, OpenImageIO 3.2.2.0;
- uv_build 0.9.30; editable ltx-core and ltx-pipelines 1.5.0;
- imageio-ffmpeg 0.6.0 and easydict 1.13 for the separate depth preprocessing.

The official CLI `--help` imported successfully with CUDA devices hidden and
network model fetching disabled. OpenImageIO emitted nanobind shutdown leak
warnings; these are retained, not represented as clean warning-free startup.
The initial editable install lacked the environment `bin` in PATH and failed
before installation. Repeating the same install with that PATH corrected it.
The first CLI import rejected shared tokenizers 0.23.3; the local 0.22.1 overlay
resolved that requirement. No weights were loaded in either check.

## Actual defaults and bounded probe

The official IC-LoRA route is two-stage, BF16, without quantization, compilation,
tiling, prompt enhancement or custom stages. The requested 1024 by 576 dimensions
are divisible by 64. Stage one is 512 by 288. Stage two uses the supplied official
spatial upsampler and refines at 1024 by 576. Union LoRA is applied in stage one;
the unmodified default stage two runs the base distilled checkpoint.

Schedules retained verbatim:

```
stage 1: [1, .99375, .9875, .98125, .975, .909375, .725, .421875, 0]
stage 2: [.909375, .725, .421875, 0]
```

`code/e1_entry.py --config PRIVATE.json [--cpu-only]` accepts exactly `mode`,
`receipt`, `official_args`, `output`. The CPU path validates the frozen arguments,
weights, Gemma shards and media dimensions/fps with stdlib and ffprobe only.
It forwards the validated inference arguments to the official CLI. Its
observer wraps the official Euler loop's denoiser; it does not replace the
sampler, sigma grid, model result or arithmetic. It requires `SimpleDenoiser`,
whose implementation makes one joint audio/video transformer invocation.
Probe mode raises its dedicated termination exception at entry to step index 1,
after index 0's video and audio Euler updates, before a second forward or decode.
The official model context then disposes its weights normally.

Generation mode observes both complete stages, expecting 11 denoiser calls and
11 completed scheduler steps. A CPU test checks the one-step termination
boundary and 8+3 accounting. Hardware execution remains a separate guard-owned
action. An interrupted receipt is not a successful generation.

First-step timing covers the half-resolution stage, so multiplication by 11
alone underestimates a potentially more expensive full-resolution second stage.
Any projected time must label this uncertainty and separate the measured step
from assumptions about stage two and decode.
For the approved 73-frame probe, the receipt reports 20 to 56 first-step
equivalents: eight stage-one steps plus three stage-two steps at respectively
4x spatial token cost or 16x quadratic attention cost. Observed setup time is
added once. The parent uses 56 for the scheduling decision. The 49-frame fallback
projection applies 0.7 to sampling cost (7 versus 10 temporal latent positions),
retaining setup time. These are conservative scheduling heuristics, not measured
second-stage timing or proven upper bounds; unmeasured decode is excluded and
must retain time reserve. No second probe is authorized by these calculations.

## Memory policy

E1 retains the existing 64 GiB worker limit. No E2-only exception is applied.
Official `PromptEncoder` releases Gemma before loading the embedding processor;
default `gpu_model` contexts dispose parameter storage to meta and trim memory.
`DiffusionStage` similarly releases weights between stages. Therefore summing
Gemma and DiT download sizes does not describe required simultaneous residency.
The largest model plus transient loading, activations and decode still requires
actual guard monitoring; the lifecycle review is not a peak-memory measurement.

## Selected weight revisions

| Role | Official repository and revision | Selected file / bytes |
|---|---|---|
| Distilled | Lightricks/LTX-2.3 @ c1521179de480464f366a98a9d9b2acc4cc097b9 | ltx-2.3-22b-distilled.safetensors / 46,149,345,038 |
| Upsampler | same | ltx-2.3-spatial-upscaler-x2-1.1.safetensors / 995,743,560 |
| Union | Lightricks/LTX-2.3-22b-IC-LoRA-Union-Control @ 20a580c8606c06a0988d40375a61309e0fe5893d | ltx-2.3-22b-ic-lora-union-control-ref0.5.safetensors / 654,465,352 |
| Text encoder | google/gemma-3-12b-it @ 96b6f1eccf38110c56df3a15bffe176da04bfd80 | snapshot / 24,414,163,446 |
| Depth | depth-anything/Video-Depth-Anything-Large @ 7aafbcb5c6af0bac741aad2b6471894fb4761afa | video_depth_anything_vitl.pth / 1,538,392,012 |

Total listed payload: 73,752,109,408 bytes. These are remote metadata sizes, not
download-integrity receipts. Text encoder access was rechecked under amendment 3;
the earlier 403 is retained as historical evidence. LTX weights link `LICENSE-2`;
VDA-Large is CC-BY-NC-4.0. The parent ledger owns actual downloads and access checks.

## VDA preprocessing packaging failure and bounded CPU recovery

The actual depth inference completed one `infer_video_depth` invocation and four
internal model forwards in 44.708544848 seconds. All 73 normalized lossless depth
PNGs and the raw depth NPZ were saved before the official MP4 writer failed:
installed Matplotlib no longer exposes `matplotlib.cm.get_cmap`. The official
`save_video` references that API even when its grayscale path does not use the
palette. This is a packaging failure, not a request to run depth inference again.

The preserved NPZ SHA256 is
`11debd60bfdd02cea8e7fe3d52a02f0f626c7023a9cf55ae9a20644d53fd9181`.
`code/vda_package.py` is a separate CPU-only recovery entry. Before packaging it
checks that exact hash, the recorded one-call/four-forward budget, and all 73 PNGs
against the official whole-clip min/max normalization. It supplies the missing
`cm.get_cmap` compatibility alias from `matplotlib.colormaps.get_cmap` and calls
the unchanged official grayscale/libx264/CRF18 writer. It imports no Torch or
model module, writes a new packaging receipt, and verifies the original failure
receipt remains byte-identical. `vda_entry.py` and its prior freeze remain unchanged.

The parent's saved `packaging-recovery.json` subsequently records
`CPU_PACKAGING_RECOVERED`: 73 PNGs matched exactly, 1024 by 576 at 24 fps,
control MP4 SHA256
`799df9ff516abe604d54ba31915825be67d19d7923b4657e3d75691099dc9f2c`.
The recovery added zero model loads and zero depth calls.

## Observed ref0.5 geometry failure

The first E1 probe attempt failed during reference VAE encoding, before any
denoiser or scheduler call. Its receipt has empty grids, 0 denoiser calls,
0 completed steps and 18.981282936991192 seconds elapsed. No timing estimate
or generated video was obtained.

The earlier 64-pixel divisibility check covered the top-level two-stage recipe
but missed the stricter reference VAE requirement. Direct standard-library
inspection of the downloaded Union safetensors header confirms
`reference_downscale_factor = "2"`. The official path therefore computes:

```
requested output:       1024 x 576
first stage:             512 x 288
ref0.5 control encode:   256 x 144
VAE spatial divisor:    32
144 / 32 = 4.5: invalid
```

`iclora_utils.py` derives reference dimensions from the stage, then resizes the
supplied control video to those dimensions. Changing the control file's stored
resolution cannot repair this. The observed tensor `[1,1024,20,9,16]` failed the
next spatial divide-by-two operation, consistent with that geometry.
This combination requires output dimensions divisible by 128; height 576 is
not. Preserving the approved resolution, reference factor and official default
recipe leaves no input-only mechanical correction. Changing output geometry,
padding inside the VAE, altering reference factor, or adopting a different stage
recipe would change the approved experiment. No such modification was made.

Technical classification: `ENGINE_BLOCKED_ENV`, geometry incompatibility;
this is not a model-quality failure or an observed runtime-speed result.
