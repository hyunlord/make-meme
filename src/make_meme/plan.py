"""MemePlan: a declarative, inspectable description of one meme render.

plan_meme builds it (segment, shots, performers, photo identities, who-becomes-whom,
style, prompts, estimate, warnings); the caller shows it to the user, optionally edits
fields via render_meme overrides, and render_meme executes exactly what it says. Keeping
every decision in one JSON document is what makes results consistent no matter which MCP
client (or model) drives the tools.
"""

from __future__ import annotations

import json
import secrets
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from make_meme.config import get_settings


@dataclass
class IdentityRef:
    id: str
    label: str
    description: str
    coat: str
    photos: int
    confidence: float
    ref_full: str | None  # background-cleaned full-body crop
    ref_head: str | None  # head close-up crop
    ref_head_alt: str | None = None
    ref_full_alt: str | None = None
    advice: list[str] = field(default_factory=list)
    # style name -> designed character reference (qwen_character), e.g. the pet standing upright
    characters: dict[str, str] = field(default_factory=dict)

    def ref_for(self, kind: str) -> str | None:
        return {"full": self.ref_full, "head": self.ref_head, "head_alt": self.ref_head_alt,
                "full_alt": self.ref_full_alt}.get(kind)


@dataclass
class MemePlan:
    id: str
    intent: str
    source_asset: str
    source_title: str | None
    segment: dict[str, Any]  # start, end, basis
    clip_asset: str  # trimmed (and reframed) clip the render works on
    aspect: str
    style: str | None
    style_candidates: list[str]
    quality: str
    seed: int
    shots: list[dict]  # pipelines.shots.Shot.to_json()
    performers: list[dict]  # id, label, bbox (main shot)
    identities: list[IdentityRef]
    cast: dict[str, str]  # performer id -> identity id
    prompts: dict[str, str]  # performer id -> prompt
    negative_prompt: str
    scene: str = ""
    estimate: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    renders: list[dict] = field(default_factory=list)  # {job_id, style, created_at}
    created_at: float = field(default_factory=time.time)

    def identity(self, ident: str) -> IdentityRef | None:
        return next((i for i in self.identities if i.id == ident), None)

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> MemePlan:
        d = dict(d)
        d["identities"] = [IdentityRef(**i) for i in d.get("identities", [])]
        return cls(**d)


def new_plan_id() -> str:
    return f"plan_{secrets.token_hex(4)}"


def plans_dir() -> Path:
    d = get_settings().home / "plans"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_plan(plan: MemePlan) -> Path:
    path = plans_dir() / f"{plan.id}.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(plan.to_json(), indent=2, ensure_ascii=False, default=str))
    tmp.replace(path)
    return path


def load_plan(plan_id: str) -> MemePlan | None:
    path = plans_dir() / f"{plan_id}.json"
    if not path.is_file():
        return None
    return MemePlan.from_json(json.loads(path.read_text()))
