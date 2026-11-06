# W2 combined-input contract

**Decision: `NOT_SUPPORTED` for the requested unchanged runner contract.**
This is a technical input-contract result, not a model quality judgment.
No W2 model loading, download, VAE call, or generation was needed for this finding.

The official DiffSynth example supports VACE control plus a single reference.
The requested W2 additionally initializes video-to-video from S2-s1 and supplies
two separate reference photos. The installed pipeline exposes all these arguments,
but its input-video unit and its VACE/noise units disagree on reference time length.
No photo is dropped or combined, and no runtime patch adds multi-reference support.

## CPU evidence

`code/test_v006_w2_contract.py` extracts the actual
`WanVideoUnit_InputVideoEmbedder.process` AST, retaining its body, and executes it
with temporal-shape doubles. It imports no model library or torch. The VAE double
uses the inspected Wan VAE rule `1 + (T - 1) // 4`.
The scene frame count and requested reference count come from the scene JSON.

| Case | Input latent T | Noise T | Observed result |
|---|---:|---:|---|
| Single reference control | 10 | 10 | PASS |
| Requested two references | 10 | 11 | Expected shape mismatch |

Executed on Spark with `CUDA_VISIBLE_DEVICES="" python3` on 2026-11-06;
exit 0, both contract cases passed, model loads 0, GPU calls 0.
This fixture proves the temporal interface inconsistency under the inspected
encoder rule; it does **not** claim to run the VAE or prove image quality.

Reproduction (UPSTREAM and CONFIG are private absolute paths):

```sh
CUDA_VISIBLE_DEVICES="" python3 code/test_v006_w2_contract.py \
  "$UPSTREAM/diffsynth/pipelines/wan_video.py" "$CONFIG"
```

## Source identity and exact locations

Installed `diffsynth/pipelines/wan_video.py` SHA256:
`e3ab58df6db88987661813f92bca601de1397aa6a2986f2a9dda6e2771183bcc`.
It is a frozen local source tree, not a Git checkout; the online revision below
is a separately verified official reference, not a claimed local checkout SHA.

- `wan_video.py:399–407`: noise includes one slot per reference.
- `wan_video.py:432–437`: the input-video path encodes both photos together as
  a two-frame video; this yields one reference time slot.
- `wan_video.py:719–729`: VACE encodes the photos separately and prefixes two slots.
- `wan_video_vae.py:984–988`: encoder temporal rule; `:1218–1233` distinguishes
  batch items from frames within an item.
- `flow_match.py:457–463`: adding noise requires matching latent shapes.

Official evidence pinned during inspection:
[DiffSynth pipeline](https://github.com/modelscope/DiffSynth-Studio/blob/08fdc0da8f41426885d9432e9007e6e460a4c30d/diffsynth/pipelines/wan_video.py),
[VAE](https://github.com/modelscope/DiffSynth-Studio/blob/08fdc0da8f41426885d9432e9007e6e460a4c30d/diffsynth/models/wan_video_vae.py),
[VACE-Fun example](https://github.com/modelscope/DiffSynth-Studio/blob/08fdc0da8f41426885d9432e9007e6e460a4c30d/examples/wanvideo/model_inference/Wan2.2-VACE-Fun-A14B.py).

The model card's general control/reference capability does not establish this
particular video-to-video plus two-photo path. The work order explicitly permits
`NOT_SUPPORTED` for unsupported W2 combinations. W1 execution remains independent.
