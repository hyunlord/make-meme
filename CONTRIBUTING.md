# Contributing to make-meme

Thanks for helping! make-meme is built so most contributions don't touch the MCP server:

| You want to… | Add/modify | Section |
|---|---|---|
| support a new generation mode (image→video, image edit, lip-sync, …) or a better model | a **recipe** | [Recipes](#adding-a-recipe) |
| fix or add a site for link fetching (Threads changed its HTML again…) | a **fetcher** | [Sources](#adding-a-fetcher-or-search-provider) |
| add a search backend (Pexels, Pixabay, …) | a **search provider** | [Sources](#adding-a-fetcher-or-search-provider) |
| make a recipe run on new hardware | a **profile variant** in `recipe.yaml` | [Profiles](#hardware-profiles) |

## Dev setup

```bash
uv sync
uv run ruff check
uv run pytest -q                              # offline, no GPU needed
MAKE_MEME_NETWORK_TESTS=1 uv run pytest -q    # also hits YouTube/Openverse/etc.
```

To try changes against a real ComfyUI: `uv run make-meme install` (or point `COMFY_URL` at yours),
`uv run make-meme comfy start`, then use the MCP Inspector:
`npx @modelcontextprotocol/inspector uv run make-meme-mcp`.

## Adding a recipe

A recipe is a directory with two files, found in `src/make_meme/builtin_recipes/` (shipped) or any
directory listed in `MAKE_MEME_RECIPES` (local, overrides built-ins by name).

1. Build the workflow in ComfyUI, then **Workflow → Export (API)** → save as `workflow.json`.
   Put obvious placeholders (`"__video__"`) in the widgets the recipe fills.
   Prefer ComfyUI core nodes; every custom node pack you add is something users must install.
2. Write `recipe.yaml`:

```yaml
name: my_recipe            # unique id
kind: swap                 # swap | detect | (new kinds need a pipeline/tool, open an issue first)
title: Short human title
description: >             # Claude reads this to decide when to use the recipe — be concrete
  What it does, what inputs work best, limitations.
inputs:                    # name -> where the value goes: [[node_id, input_name], ...]
  video:  {type: video, targets: [["1", "file"]]}
  ref2:   {type: image, required: false, targets: [["6", "image"]], unlink_if_missing: [["14", "ref2"]]}
  prompt: {type: string, default: "…", targets: [["13", "positive_prompt"]]}
presets:                   # quality levels exposed to users
  draft: {width: 832, height: 480, steps: 4}
profile_presets:           # optional per-hardware overrides of presets
  mps: {draft: {width: 512, height: 288}}
models:                    # downloaded by `make-meme install`, checked by check_setup
  main:
    targets: [["11", "model"]]
    profiles:
      default: {file: sub/dir/model.safetensors, dir: diffusion_models, repo: org/repo,
                path: path/in/repo.safetensors, size_gb: 9.7, license: Apache-2.0}
custom_nodes:
  - {name: ComfyUI-Foo, repo: https://github.com/x/ComfyUI-Foo, ref: <commit sha>, provides: [FooNode]}
profile_overrides:         # widget values per hardware profile
  mps: {"11": {attention_mode: comfy}}
outputs: {frames: "17"}    # output name -> node id
```

3. Add a test in `tests/` that builds the workflow for each profile (see `tests/test_recipes.py`).
4. In the PR, include: hardware you tested on, time per run, and a before/after frame.

Rules: pin custom nodes to a commit; record model licenses accurately; models are downloaded by
the user from their original hosts — never commit weights.

## Adding a fetcher or search provider

Fetchers and search providers live in `src/make_meme/sources/` and implement the `Fetcher` /
`SearchProvider` protocols in `sources/base.py`. Third-party packages can register their own via
entry points (no PR needed):

```toml
[project.entry-points."make_meme.fetchers"]
my_site = "my_pkg.fetcher:MySiteFetcher"
[project.entry-points."make_meme.search_providers"]
my_search = "my_pkg.search:MySearch"
```

Site HTML changes often. When fixing a fetcher, add the (trimmed) HTML that broke it as a fixture
under `tests/sources/fixtures/` so it stays fixed. Never commit cookies or personal data in fixtures.

## Hardware profiles

`mps` (Apple Silicon), `cuda` (≥ 20 GB VRAM), `cuda_lowvram` (< 20 GB, e.g. free T4), `cpu`.
A recipe chooses model files and widget values per profile; `default` applies to all.

## Pull requests

- Keep PRs focused; run `uv run ruff check` and `uv run pytest -q`.
- By contributing you agree your contribution is licensed under Apache-2.0.
- Features that mainly enable non-consensual or deceptive use (see RESPONSIBLE_USE.md) won't be merged.
