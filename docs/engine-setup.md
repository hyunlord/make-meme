# Engine setup (ComfyUI)

make-meme's MCP server is lightweight; the AI work runs in [ComfyUI](https://github.com/comfyanonymous/ComfyUI),
either on your computer or on a free cloud GPU. The MCP server talks to it over HTTP (`COMFY_URL`).

## Option A — your own computer

```bash
uvx --from make-meme-mcp make-meme install      # ComfyUI + custom nodes + models (~23 GB)
uvx --from make-meme-mcp make-meme comfy start  # keep this running while you make memes
```

`install` is idempotent: re-run it after upgrading make-meme. It installs into
`~/.make-meme/ComfyUI` (override with `--comfy-dir` or `COMFY_DIR`) and auto-detects a hardware
profile (`mps`, `cuda`, `cuda_lowvram`, `cpu`; override with `--profile`).

Already have ComfyUI? `make-meme install --skip-comfy --comfy-dir /path/to/ComfyUI`, start it as usual and
set `COMFY_URL` if it isn't `http://127.0.0.1:8188`.

### What to expect

| Hardware | `draft` | `high` | Notes |
|---|---|---|---|
| Apple Silicon, 36 GB (measured, M4 Max) | 512×288, ~50 s per sampling step for a 1 s clip | 832×480 | 480p+ needs most of the RAM free — close other apps. A 5 s clip is several times slower than 1 s. |
| NVIDIA ≥ 20 GB (`cuda`) | 832×480 | 1280×720 | fp8 weights |
| NVIDIA < 20 GB, e.g. free T4 (`cuda_lowvram`) | 832×480 | 832×480 | GGUF Q4 weights, text encoder on CPU |

Swaps run in chunks of 81 frames (≈ 5 s at 16 fps). Short clips (≤ 5 s) are one chunk and the
fastest way to iterate; use `quality="draft"` until you like the result.

### Apple Silicon notes

The bundled `make_meme_nodes` pack patches MoCha's rotary embeddings to avoid float64/complex128,
which Metal doesn't support, and recipes use ComfyUI's split attention on MPS. If generation is
extremely slow, check memory pressure (Activity Monitor): heavy swapping means the model doesn't
fit next to your other apps.

## Option C — your own GPU server (DGX Spark, any Linux + NVIDIA box)

The generated styles (`pet_idol_outfit`, `pet_idol_fur`) need about 40 GB at
720p (Wan2.2-Animate 14B fp8 + text encoder + activations); character design (Qwen-Image-Edit)
peaks around 35 GB, loaded one after the other. A laptop can drive a GPU server over your LAN or
Tailscale:

```bash
# on the GPU server
git clone https://github.com/<you>/make-meme && cd make-meme && uv sync
COMFY_DIR=~/make-meme/ComfyUI uv run make-meme install            # nodes + models for every recipe
COMFY_DIR=~/make-meme/ComfyUI uv run make-meme comfy start --listen 127.0.0.1 --port 8190 &
uv run make-meme comfy proxy --upstream http://127.0.0.1:8190 --listen <server LAN/Tailscale IP> --port 8191
#   prints a COMFY_TOKEN (or pass --token)

# on your laptop
claude mcp add make-meme -e COMFY_URL=http://<server IP>:8191 -e COMFY_TOKEN=<token> -- uvx make-meme-mcp
```

### DGX Spark / GB10: host tuning (needs sudo, once per boot)

Video models push GB10 from ~14 W to ~85 W the instant denoising starts; on some units that trips
overcurrent protection and the box powers off or hard-reboots **with no logs**. Approaching the
memory limit with swap on freezes it instead of failing cleanly. Before rendering:

```bash
sudo swapoff -a                    # unified memory: thrashing swap freezes the whole machine
sudo sysctl -w vm.swappiness=10
sudo nvidia-smi -pm 1              # persistence mode
sudo nvidia-smi -lgc 300,2100      # cap GPU clocks (~50 W); -pl is N/A on GB10
# undo: sudo nvidia-smi -rgc; sudo swapon -a
```

(Community findings: NVIDIA forum "Unlocking the Power of the Spark in ComfyUI", the
`bjarkebolding/spark-comfyui` project; `tune --persist` there makes this survive reboots.)
make-meme then starts ComfyUI with `--disable-mmap --cache-none --reserve-vram 20
--disable-pinned-memory --disable-cuda-malloc`, refuses heavy recipes when free memory is short,
and its companion nodes interrupt a prompt below 6 GB available.

Unified-memory boards (DGX Spark / GB10) report no VRAM through `nvidia-smi`; the installer uses
system RAM instead and picks the `cuda` profile. On Linux aarch64 it installs CUDA torch from
PyTorch's index (`MAKE_MEME_TORCH_INDEX` overrides it). Bind the proxy to a private address only;
ComfyUI itself has no login.

## Option B — free cloud GPU (Kaggle / Colab)

Open [`notebooks/remote_comfyui.ipynb`](../notebooks/remote_comfyui.ipynb) on Kaggle (GPU T4, Internet on)
or Colab (T4), run all cells, and copy the printed `COMFY_URL`:

```bash
claude mcp add make-meme -e COMFY_URL=https://<random>.trycloudflare.com -e COMFY_TOKEN=<token> -- uvx make-meme-mcp
```

The first run downloads ~23 GB inside the notebook (10–20 min). ComfyUI has no login, so the
notebook only exposes it through `make-meme comfy proxy`, which requires the printed
`COMFY_TOKEN` (sent as a bearer token by make-meme). Keep the token secret and stop the notebook
when you're done.

## Model licenses

Models are downloaded by you from their original hosts; make-meme does not redistribute weights.

| Model | Used by | License |
|---|---|---|
| MoCha (Orange-3DV-Team; GGUF by vantagewithai, fp8 by Kijai) | `mocha_swap` | AGPL-3.0 (weights) |
| Wan 2.1 VAE, umt5-xxl text encoder, lightx2v distill LoRA | `mocha_swap` | Apache-2.0 |
| SAM 3.1 (Meta, via Comfy-Org) | `sam3_detect`, `sam3_track` | SAM License |
| Wan2.2-Animate 14B (Wan-AI; fp8/GGUF by Kijai), relight LoRA, lightx2v I2V LoRA | `wan_animate_replace` | Apache-2.0 |
| CLIP ViT-H (OpenCLIP, via Comfy-Org) | `wan_animate_replace` | MIT |
| ViTPose-L wholebody ONNX (easy_ViTPose) | `wan_animate_replace` | Apache-2.0 |
| YOLOv10m ONNX (person boxes for ViTPose; shipped in the Wan2.2-Animate repo) | `wan_animate_replace` | AGPL-3.0 |
| Qwen-Image-Edit-2511 (fp8 by Comfy-Org), Qwen2.5-VL text encoder, Lightning LoRA (lightx2v) | `qwen_character` | Apache-2.0 |

Custom node packs: ComfyUI-WanVideoWrapper (Apache-2.0). ComfyUI itself is GPL-3.0; make-meme
only talks to it over HTTP.
