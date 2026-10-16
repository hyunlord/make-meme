# make-meme

An MCP server that lets Claude turn a music video (or any short clip) plus photos of people or
animals into a subject-swapped meme video. You describe what you want in chat; make-meme handles
finding/loading the video, finding/loading reference photos, detecting subjects, and running the
AI video-generation pipeline (in [ComfyUI](https://github.com/comfyanonymous/ComfyUI)) to produce
the result.

make-meme is free and open source (Apache-2.0). It's built to be extended: new generation modes
plug in as "recipes" without touching the MCP server itself.

## Install

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), and `ffmpeg`/`ffprobe` on your `PATH`
(`brew install ffmpeg` on macOS).

```bash
git clone https://github.com/kwanhyeonpark-ctrl/make-meme
cd make-meme
uv sync
```

## Register with Claude

**Claude Code:**

```bash
claude mcp add make-meme -- uv run --directory /path/to/make-meme make-meme-mcp
```

**Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "make-meme": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/make-meme", "make-meme-mcp"]
    }
  }
}
```

## How it works

Tools are designed to be chained together in conversation:

1. `search_media` / `load_media` — find or load a source video and reference photos (local files,
   direct URLs, or links like YouTube/TikTok/Instagram).
2. `inspect_media` — see a storyboard and suggested trim points for a loaded video.
3. `detect_subjects` — find the numbered people/animals in the video to replace.
4. `swap_subjects` (or the one-shot `make_swap_meme`) — kick off generation; returns a `job_id`.
5. `get_job` — poll progress until the result is ready.

Everything you load or generate is tracked as an **asset** (with an id you can pass back into
other tools), so results can be chained into further edits.

Run `check_setup()` any time to verify ffmpeg, the media-fetching backend, and ComfyUI are all
reachable, with fix hints for anything that's missing.

## Engine setup

Generation runs in ComfyUI using free, open models — [MoCha](https://github.com/Orange-3DV-Team/MoCha)
for subject replacement (works for animals: no pose skeleton) and SAM 3 for finding subjects:

```bash
uv run make-meme install       # ComfyUI + custom nodes + models (~23 GB), idempotent
uv run make-meme comfy start   # keep running while you make memes
```

No suitable GPU? Run ComfyUI for free on Kaggle/Colab with
[`notebooks/remote_comfyui.ipynb`](notebooks/remote_comfyui.ipynb) and set `COMFY_URL`.
Details, performance numbers and model licenses: [docs/engine-setup.md](docs/engine-setup.md).

## Extending

Generation modes are **recipes** (a ComfyUI workflow + a small YAML manifest), link fetchers and
search backends are **plugins**. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Responsible use

Only use photos of people who agreed (or your pets). Outputs are tagged as AI-generated in their
metadata. See [RESPONSIBLE_USE.md](RESPONSIBLE_USE.md).

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE). Model weights have their own licenses
(listed in docs/engine-setup.md) and are downloaded from their original hosts.

[한국어 README](README.ko.md)
