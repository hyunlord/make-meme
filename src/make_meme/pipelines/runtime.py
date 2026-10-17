"""Shared runtime helpers for pipelines: ComfyUI client creation, hardware profile,
recipe execution with readiness checks."""

from __future__ import annotations

import logging
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from make_meme.comfy.client import ComfyClient, ComfyError, ExecutionResult, ProgressCallback
from make_meme.comfy.validate import check_recipe
from make_meme.config import get_settings
from make_meme.recipes.loader import Recipe

logger = logging.getLogger(__name__)

_object_info_cache: dict[str, dict[str, Any]] = {}


@asynccontextmanager
async def comfy_session():
    client = ComfyClient(get_settings().comfy_url)
    try:
        yield client
    finally:
        await client.aclose()


async def hardware_profile(client: ComfyClient) -> str:
    """'mps' | 'cuda' | 'cpu', from MAKE_MEME_PROFILE or the ComfyUI device list."""
    forced = os.environ.get("MAKE_MEME_PROFILE")
    if forced:
        return forced
    stats = await client.system_stats()
    device = (stats.get("devices") or [{}])[0]
    kind = device.get("type", "cpu")
    if kind == "cuda":
        return "cuda_lowvram" if device.get("vram_total", 0) < 20 * 1024**3 else "cuda"
    return kind if kind == "mps" else "cpu"


_unified_cache: dict[str, bool] = {}


async def unified_memory(client: ComfyClient) -> bool:
    """True for GPUs that share system RAM (DGX Spark / GB10: ComfyUI reports VRAM == RAM)."""
    if client.base_url not in _unified_cache:
        try:
            stats = await client.system_stats()
            device = (stats.get("devices") or [{}])[0]
            ram = float((stats.get("system") or {}).get("ram_total") or 0)
            vram = float(device.get("vram_total") or 0)
            _unified_cache[client.base_url] = device.get("type") == "cuda" and ram > 0 and abs(vram - ram) / ram < 0.05
        except (ComfyError, AttributeError, TypeError, ValueError):
            _unified_cache[client.base_url] = False
    return _unified_cache[client.base_url]


async def _check_free_memory(client: ComfyClient, recipe: Recipe) -> None:
    """Refuse a heavy run on a unified-memory GPU when the machine doesn't have the memory:
    there, GPU memory can't be swapped, and running out froze a shared DGX Spark."""
    need = float(recipe.constraints.get("min_free_gb", 0) or 0)
    if not need or not hasattr(client, "stats"):
        return
    stats = await client.stats() or {}
    avail = stats.get("system_available_bytes")
    if avail is None:
        return
    # ComfyUI may already hold some of this recipe's models; count them as available.
    held = float(stats.get("allocated_bytes") or 0)
    if (avail + held) / 2**30 < need:
        raise ComfyError(
            f"{recipe.name} needs about {need:.0f} GB free on the GPU server, which has {avail / 2**30:.0f} GB "
            f"available right now (other programs are using the rest). Free memory there and retry; on a "
            f"unified-memory machine running out freezes the whole system."
        )


async def object_info(client: ComfyClient, refresh: bool = False) -> dict[str, Any]:
    if refresh or client.base_url not in _object_info_cache:
        _object_info_cache[client.base_url] = await client.object_info()
    return _object_info_cache[client.base_url]


async def ensure_ready(client: ComfyClient, recipe: Recipe, profile: str) -> None:
    info = await object_info(client)
    readiness = check_recipe(recipe, info, profile)
    if not readiness.ready:
        info = await object_info(client, refresh=True)  # models may have been installed since
        readiness = check_recipe(recipe, info, profile)
    if not readiness.ready:
        s = readiness.summary()
        raise ComfyError(
            f"ComfyUI is missing what recipe '{recipe.name}' needs: "
            f"{ {k: v for k, v in s.items() if k.startswith('missing')} }. Fix: run `{s['fix']}`."
        )


async def run_recipe(
    client: ComfyClient,
    recipe: Recipe,
    *,
    media: dict[str, Path],
    values: dict[str, Any],
    profile: str,
    preset: str | None = None,
    on_progress: ProgressCallback | None = None,
    cancelled=None,
    stage: str = "generating",
) -> ExecutionResult:
    """Upload media inputs, build the workflow, run it and return the result."""
    uploaded = {name: await client.upload(path) for name, path in media.items()}
    if hasattr(client, "drop_cache") and await unified_memory(client):
        # Page-cached model files and GPU allocations share RAM there, and the driver doesn't
        # reclaim the cache: without this a 40 GB model failed to load with 110 GB "available".
        await client.drop_cache()
        await _check_free_memory(client, recipe)
    workflow = recipe.build({**values, **uploaded}, profile=profile, preset=preset)
    timeout = recipe.constraints.get("timeout_sec")
    node = recipe.constraints.get("progress_node")
    steps = workflow.get(node, {}).get("inputs", {}).get("steps") if node else None
    return await client.run(
        workflow, on_progress=on_progress, cancelled=cancelled, stage=stage,
        progress_node=node,
        front=bool(recipe.constraints.get("front", False)),
        progress_steps=int(steps) if isinstance(steps, int) else None,
        timeout=float(timeout) if timeout else None,
    )


def node_text_outputs(result: ExecutionResult, node_id: str) -> list[str]:
    out = result.raw.get("outputs", {}).get(node_id, {})
    text = out.get("text", [])
    return [t for t in text if isinstance(t, str)]


def _file_order(name: str) -> tuple:
    """SaveImage names files prefix_00001_.png; sort by that counter numerically so order
    survives counters wider than 5 digits."""
    nums = re.findall(r"\d+", name)
    return (int(nums[-1]) if nums else -1, name)


def node_files(result: ExecutionResult, node_id: str) -> list:
    """Files a node wrote, in batch order (SaveImage's counter increases per image)."""
    return sorted((o for o in result.outputs if o.node_id == node_id), key=lambda o: _file_order(o.filename))
