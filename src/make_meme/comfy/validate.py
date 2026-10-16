"""Check that a ComfyUI instance can run a recipe: custom nodes present, model files
visible to their loader nodes. Works for remote instances too because it only uses
/object_info (loader widgets enumerate the model files ComfyUI can see)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from make_meme.recipes.loader import ModelVariant, Recipe


@dataclass
class RecipeReadiness:
    recipe: str
    profile: str
    missing_nodes: list[str] = field(default_factory=list)  # class_types
    missing_node_packs: list[str] = field(default_factory=list)  # repo URLs to install
    missing_models: list[ModelVariant] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return not (self.missing_nodes or self.missing_node_packs or self.missing_models)

    def summary(self) -> dict[str, Any]:
        out: dict[str, Any] = {"recipe": self.recipe, "profile": self.profile, "ready": self.ready}
        if self.missing_node_packs or self.missing_nodes:
            out["missing_custom_nodes"] = self.missing_node_packs or self.missing_nodes
        if self.missing_models:
            out["missing_models"] = [
                {"file": f"models/{m.dir}/{m.file}", "from": f"hf://{m.repo}/{m.path}", "size_gb": m.size_gb}
                for m in self.missing_models
            ]
        if not self.ready:
            out["fix"] = f"make-meme install {self.recipe}"
        return out


def _enum_options(object_info: dict[str, Any], class_type: str, input_name: str) -> list[str] | None:
    spec = object_info.get(class_type, {}).get("input", {})
    for section in ("required", "optional"):
        entry = spec.get(section, {}).get(input_name)
        if entry and isinstance(entry[0], list):
            return [str(x) for x in entry[0]]
    return None


def _norm(path: str) -> str:
    return path.replace("\\", "/")


def check_recipe(recipe: Recipe, object_info: dict[str, Any], profile: str) -> RecipeReadiness:
    result = RecipeReadiness(recipe=recipe.name, profile=profile)
    available = set(object_info)
    result.missing_nodes = sorted(recipe.required_class_types() - available)
    for pack in recipe.custom_nodes:
        if not set(pack.provides) <= available:
            result.missing_node_packs.append(pack.repo)

    for model in recipe.models:
        variant = model.profiles.get(profile) or model.profiles.get("default")
        if variant is None:
            continue
        for node_id, input_name in model.targets:
            class_type = recipe.workflow[node_id]["class_type"]
            options = _enum_options(object_info, class_type, input_name)
            if options is None:
                continue  # node missing (reported above) or free-text input
            if _norm(variant.file) not in {_norm(o) for o in options}:
                result.missing_models.append(variant)
                break
    return result
