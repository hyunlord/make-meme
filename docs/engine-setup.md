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

## Option B — free cloud GPU (Kaggle / Colab)

Open [`notebooks/remote_comfyui.ipynb`](../notebooks/remote_comfyui.ipynb) on Kaggle (GPU T4, Internet on)
or Colab (T4), run all cells, and copy the printed `COMFY_URL`:

```bash
claude mcp add make-meme -e COMFY_URL=https://<random>.trycloudflare.com -- uvx make-meme-mcp
```

The first run downloads ~23 GB inside the notebook (10–20 min). The tunnel URL is public while the
notebook runs — don't share it.

## Model licenses

Models are downloaded by you from their original hosts; make-meme does not redistribute weights.

| Model | Used by | License |
|---|---|---|
| MoCha (Orange-3DV-Team; GGUF by vantagewithai, fp8 by Kijai) | `mocha_swap` | AGPL-3.0 (weights) |
| Wan 2.1 VAE, umt5-xxl text encoder, lightx2v distill LoRA | `mocha_swap` | Apache-2.0 |
| SAM 3.1 (Meta, via Comfy-Org) | `sam3_detect` | SAM License |

Custom node packs: ComfyUI-WanVideoWrapper (Apache-2.0). ComfyUI itself is GPL-3.0; make-meme
only talks to it over HTTP.
