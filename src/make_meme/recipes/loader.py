"""Recipes: a ComfyUI API-format workflow plus a manifest describing its inputs,
models, custom nodes, hardware profiles and quality presets.

Adding a new generation "direction" (image-to-video, image edit, ...) means adding a
directory with `recipe.yaml` + `workflow.json`; see CONTRIBUTING.md.
"""

from __future__ import annotations

import copy
import json
import logging
import os
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

Target = tuple[str, str]  # (node_id, input_name)


class RecipeError(ValueError):
    """Invalid recipe manifest or inputs; message is user-facing."""


@dataclass
class InputSpec:
    name: str
    type: str  # video | image | mask | string | int | float | bool | enum
    targets: list[Target]
    required: bool = True
    default: Any = None
    choices: list[Any] | None = None
    description: str = ""
    unlink_if_missing: list[Target] = field(default_factory=list)


@dataclass
class ModelVariant:
    file: str  # value placed in the loader widget, relative to `dir`
    dir: str  # ComfyUI models/ subdirectory
    repo: str  # HuggingFace repo id
    path: str  # file path inside the repo
    size_gb: float = 0.0
    license: str = "unknown"


@dataclass
class ModelSpec:
    id: str
    targets: list[Target]
    profiles: dict[str, ModelVariant]


@dataclass
class CustomNodeSpec:
    name: str
    repo: str
    ref: str | None = None
    provides: list[str] = field(default_factory=list)  # node class_types used to detect it
    # Packages to install instead of the pack's requirements.txt (e.g. when it pins a
    # CUDA-only wheel such as onnxruntime-gpu that doesn't exist on every platform).
    pip: list[str] | None = None
    pip_cuda: list[str] | None = None  # replaces `pip` on CUDA profiles (e.g. onnxruntime-gpu)


@dataclass
class Recipe:
    name: str
    kind: str
    title: str
    description: str
    root: Path
    workflow: dict[str, Any]
    inputs: dict[str, InputSpec]
    models: list[ModelSpec]
    custom_nodes: list[CustomNodeSpec]
    presets: dict[str, dict[str, Any]]
    profile_overrides: dict[str, dict[str, dict[str, Any]]]
    outputs: dict[str, str]  # output name -> node id
    constraints: dict[str, Any] = field(default_factory=dict)
    profile_presets: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)
    profile_constraints: dict[str, dict[str, Any]] = field(default_factory=dict)

    def constraint(self, name: str, profile: str | None = None, default: Any = None) -> Any:
        """A constraint (e.g. max_frames), with a hardware-specific override when one exists."""
        if profile is not None and name in self.profile_constraints.get(profile, {}):
            return self.profile_constraints[profile][name]
        return self.constraints.get(name, default)

    def required_class_types(self) -> set[str]:
        return {node["class_type"] for node in self.workflow.values()}

    def preset_values(self, preset: str, profile: str) -> dict[str, Any]:
        """Preset values, with hardware-specific overrides (e.g. smaller drafts on Macs)."""
        if preset not in self.presets:
            raise RecipeError(f"Unknown quality '{preset}' for {self.name}; choose from {sorted(self.presets)}")
        return {**self.presets[preset], **self.profile_presets.get(profile, {}).get(preset, {})}

    def build(self, values: dict[str, Any], *, profile: str, preset: str | None = None) -> dict[str, Any]:
        """Return a ComfyUI API prompt with inputs, preset and hardware profile applied.

        `values` maps input names to already-uploaded file names (for media) or literals.
        Preset values fill inputs the caller left unset; explicit values win."""
        merged: dict[str, Any] = {}
        if preset is not None:
            merged.update(self.preset_values(preset, profile))
        merged.update({k: v for k, v in values.items() if v is not None})

        unknown = set(merged) - set(self.inputs)
        if unknown:
            raise RecipeError(f"{self.name} does not accept inputs: {sorted(unknown)}")

        wf = copy.deepcopy(self.workflow)
        for spec in self.inputs.values():
            value = merged.get(spec.name, spec.default)
            if value is None:
                if spec.required:
                    raise RecipeError(f"{self.name} requires input '{spec.name}' ({spec.description or spec.type})")
                for node_id, inp in spec.unlink_if_missing:
                    _node(wf, node_id, self.name)["inputs"].pop(inp, None)
                continue
            value = _coerce(spec, value, self.name)
            for node_id, inp in spec.targets:
                _node(wf, node_id, self.name)["inputs"][inp] = value

        for model in self.models:
            variant = model.profiles.get(profile) or model.profiles.get("default")
            if variant is None:
                raise RecipeError(f"{self.name}: model '{model.id}' has no variant for hardware profile '{profile}'")
            for node_id, inp in model.targets:
                _node(wf, node_id, self.name)["inputs"][inp] = variant.file

        for node_id, patch in self.profile_overrides.get(profile, {}).items():
            _node(wf, node_id, self.name)["inputs"].update(patch)
        return _prune(wf, self.outputs.values())


def _prune(wf: dict[str, Any], output_nodes: Any) -> dict[str, Any]:
    """Drop nodes no output depends on (e.g. a loader whose optional input was unlinked),
    so ComfyUI never validates their placeholder values."""
    keep: set[str] = set()
    stack = [n for n in output_nodes if n in wf]
    while stack:
        node_id = stack.pop()
        if node_id in keep:
            continue
        keep.add(node_id)
        for value in wf[node_id]["inputs"].values():
            if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str) and value[0] in wf:
                stack.append(value[0])
    return {k: v for k, v in wf.items() if k in keep} if keep else wf


def _node(wf: dict[str, Any], node_id: str, recipe: str) -> dict[str, Any]:
    try:
        return wf[node_id]
    except KeyError:
        raise RecipeError(f"recipe {recipe} references missing workflow node {node_id}") from None


def _coerce(spec: InputSpec, value: Any, recipe: str) -> Any:
    try:
        if spec.type == "int":
            value = int(value)
        elif spec.type == "float":
            value = float(value)
        elif spec.type == "bool":
            value = bool(value)
        elif spec.type in ("string", "video", "image", "mask", "enum"):
            value = str(value)
    except (TypeError, ValueError):
        raise RecipeError(f"{recipe}: input '{spec.name}' must be {spec.type}, got {value!r}") from None
    if spec.choices is not None and value not in spec.choices:
        raise RecipeError(f"{recipe}: input '{spec.name}' must be one of {spec.choices}")
    return value


def _targets(raw: Any) -> list[Target]:
    return [(str(t[0]), str(t[1])) for t in (raw or [])]


def load_recipe(root: Path) -> Recipe:
    manifest_path = root / "recipe.yaml"
    try:
        m = yaml.safe_load(manifest_path.read_text())
        workflow = json.loads((root / m.get("workflow", "workflow.json")).read_text())
    except (OSError, yaml.YAMLError, json.JSONDecodeError) as e:
        raise RecipeError(f"Cannot load recipe at {root}: {e}") from e

    inputs = {
        name: InputSpec(
            name=name,
            type=spec["type"],
            targets=_targets(spec.get("targets")),
            required=spec.get("required", spec.get("default") is None),
            default=spec.get("default"),
            choices=spec.get("choices"),
            description=spec.get("description", ""),
            unlink_if_missing=_targets(spec.get("unlink_if_missing")),
        )
        for name, spec in (m.get("inputs") or {}).items()
    }
    models = [
        ModelSpec(
            id=mid,
            targets=_targets(spec.get("targets")),
            profiles={p: ModelVariant(**v) for p, v in spec["profiles"].items()},
        )
        for mid, spec in (m.get("models") or {}).items()
    ]
    nodes = [CustomNodeSpec(**n) for n in (m.get("custom_nodes") or [])]
    return Recipe(
        name=m["name"],
        kind=m["kind"],
        title=m.get("title", m["name"]),
        description=m.get("description", "").strip(),
        root=root,
        workflow=workflow,
        inputs=inputs,
        models=models,
        custom_nodes=nodes,
        presets=m.get("presets") or {},
        profile_overrides={
            p: {str(k): v for k, v in nodes_.items()} for p, nodes_ in (m.get("profile_overrides") or {}).items()
        },
        outputs={k: str(v) for k, v in (m.get("outputs") or {}).items()},
        constraints=m.get("constraints") or {},
        profile_presets=m.get("profile_presets") or {},
        profile_constraints=m.get("profile_constraints") or {},
    )


def recipe_dirs() -> list[Path]:
    """Built-in recipes shipped in the package, plus user recipes from
    $MAKE_MEME_RECIPES (os.pathsep-separated directories)."""
    dirs: list[Path] = []
    builtin = resources.files("make_meme") / "builtin_recipes"
    if builtin.is_dir():
        dirs.append(Path(str(builtin)))
    for extra in filter(None, os.environ.get("MAKE_MEME_RECIPES", "").split(os.pathsep)):
        dirs.append(Path(extra).expanduser())
    return dirs


@lru_cache(maxsize=1)
def all_recipes() -> dict[str, Recipe]:
    found: dict[str, Recipe] = {}
    for base in recipe_dirs():
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if (child / "recipe.yaml").is_file():
                try:
                    recipe = load_recipe(child)
                except (RecipeError, KeyError, TypeError, AttributeError, ValueError) as e:
                    logger.error("skipping invalid recipe %s: %s", child, e)
                    continue
                found[recipe.name] = recipe  # later dirs override built-ins
    return found


def get_recipe(name: str) -> Recipe:
    recipes = all_recipes()
    if name not in recipes:
        raise RecipeError(f"Unknown recipe '{name}'. Available: {sorted(recipes)}")
    return recipes[name]


def recipes_of_kind(kind: str) -> list[Recipe]:
    return [r for r in all_recipes().values() if r.kind == kind]
