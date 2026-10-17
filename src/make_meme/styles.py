"""Style packs: how a kind of meme is made, as data.

A style picks the engine (`swap`: a generation recipe replaces the subject; `paste`: a
tracked cut-out of the pet's head is pasted on, no generation), which region of each
on-screen subject is replaced (`mask`: head | full_body), which kind of reference crops
are used, and prompt templates. New meme looks are added by dropping a `style.yaml` into builtin_styles/ or a
directory listed in $MAKE_MEME_STYLES — no code changes.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

ENGINES = ("swap", "paste", "animate")
MASK_MODES = ("head", "full_body")
REF_KINDS = ("full", "head", "head_alt", "full_alt")


class StyleError(ValueError):
    """Message is user-facing."""


@dataclass
class Style:
    name: str
    title: str
    description: str
    recipe: str
    mask: str
    refs: dict[str, str]
    prompt: str
    negative: str
    keywords: list[str] = field(default_factory=list)
    defaults: dict[str, Any] = field(default_factory=dict)
    engine: str = "swap"
    params: dict[str, Any] = field(default_factory=dict)  # engine-specific knobs (e.g. paste scale)
    # animate styles: how the character reference is designed from the pet photo first
    design_prompt: str = ""
    design_outfit: bool = False  # give the designer a crop of the performer to copy the outfit from
    design_size: tuple[int, int] = (768, 1344)

    def render_design_prompt(self, *, subject_desc: str, coat: str = "") -> str:
        values = _Defaults(subject_desc=subject_desc, subject_desc_cap=_cap(subject_desc), coat=coat or "its")
        return re.sub(r"\s+", " ", self.design_prompt.format_map(values)).strip()

    def render_prompt(self, *, subject_desc: str, coat: str = "", scene: str = "") -> str:
        values = _Defaults(subject_desc=subject_desc, subject_desc_cap=_cap(subject_desc), coat=coat or "its",
                           scene=(scene.strip() + " ") if scene.strip() else "")
        return re.sub(r"\s+", " ", self.prompt.format_map(values)).strip()

    def summary(self) -> dict[str, Any]:
        return {"name": self.name, "title": self.title, "description": self.description, "engine": self.engine,
                "mask": self.mask, "defaults": self.defaults}


class _Defaults(dict):
    def __missing__(self, key: str) -> str:
        return ""


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def load_style(path: Path) -> Style:
    try:
        m = yaml.safe_load(path.read_text()) or {}
    except (OSError, yaml.YAMLError) as e:
        raise StyleError(f"Cannot read style {path}: {e}") from e
    try:
        style = Style(
            name=m["name"], title=m.get("title", m["name"]), description=str(m.get("description", "")).strip(),
            recipe=m["recipe"] if m.get("engine", "swap") in ("swap", "animate") else str(m.get("recipe") or ""),
            mask=m.get("mask", "full_body"), refs=dict(m.get("refs") or {"ref1": "full"}),
            prompt=m.get("prompt", "{subject_desc}"), negative=m.get("negative", ""),
            keywords=[str(k).lower() for k in m.get("keywords") or []], defaults=dict(m.get("defaults") or {}),
            engine=str(m.get("engine", "swap")), params=dict(m.get("params") or {}),
            design_prompt=str(m.get("design_prompt", "")).strip(), design_outfit=bool(m.get("design_outfit", False)),
            design_size=tuple(m.get("design_size") or (768, 1344)),
        )
    except KeyError as e:
        raise StyleError(f"Style {path} is missing {e}") from e
    if style.engine not in ENGINES:
        raise StyleError(f"Style {style.name}: engine must be one of {ENGINES}")
    if style.engine == "animate" and not style.design_prompt:
        raise StyleError(f"Style {style.name}: animate styles need a design_prompt for the character reference")
    if style.mask not in MASK_MODES:
        raise StyleError(f"Style {style.name}: mask must be one of {MASK_MODES}")
    bad = [k for k in style.refs.values() if k not in REF_KINDS]
    if bad:
        raise StyleError(f"Style {style.name}: unknown ref kinds {bad}; use {REF_KINDS}")
    return style


def style_dirs() -> list[Path]:
    dirs = [Path(str(resources.files("make_meme") / "builtin_styles"))]
    dirs += [Path(p).expanduser() for p in os.environ.get("MAKE_MEME_STYLES", "").split(os.pathsep) if p]
    return dirs


@lru_cache(maxsize=1)
def all_styles() -> dict[str, Style]:
    found: dict[str, Style] = {}
    for base in style_dirs():
        if not base.is_dir():
            continue
        for f in sorted(base.glob("*/style.yaml")):
            try:
                s = load_style(f)
            except StyleError as e:
                logger.error("skipping style: %s", e)
                continue
            found[s.name] = s
    return found


def get_style(name: str) -> Style:
    styles = all_styles()
    if name not in styles:
        raise StyleError(f"Unknown style {name!r}. Available: {sorted(styles)}")
    return styles[name]


def guess_style(intent: str, replacement_label: str | None) -> tuple[str | None, list[str]]:
    """Pick a style from the user's wording. Returns (style or None if ambiguous, candidates)."""
    text = intent.lower()
    styles = all_styles()
    pet = replacement_label == "animal"
    candidates = [n for n in styles if n.startswith("pet_")] if pet else ["person_swap"]
    hits = [n for n in candidates if any(k in text for k in styles[n].keywords)]
    if len(hits) == 1:
        return hits[0], candidates
    if not pet and "person_swap" in styles:
        return "person_swap", candidates
    return None, candidates
