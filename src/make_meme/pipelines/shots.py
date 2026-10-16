"""Split a clip into shots (camera cuts) and follow the same performers across them.

Subject swapping locates its targets on a chunk's first frame, so a segment that spans
cuts must be processed shot by shot. Performers are defined on the "main" shot (the
longest shot showing the most subjects) and matched in every other shot by the colour of
their head/upper body (hair, which differs between performers even in matching outfits).
Shots without a confident match are left untouched.
"""

from __future__ import annotations

import asyncio
import itertools
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image

from make_meme import ingest
from make_meme.comfy.client import ComfyClient
from make_meme.pipelines.assign import hist_dist, subject_head_hist
from make_meme.pipelines.detect import Subject, detect_in_image

MIN_SHOT_SEC = 0.4
MATCH_MAX_DIST = 0.55


@dataclass
class Shot:
    index: int
    start: float  # seconds within the clip
    end: float
    subjects: list[Subject] = field(default_factory=list)
    frame_path: str | None = None
    # performer id ("P1", "P2", ...) -> subject id within this shot
    performers: dict[str, int] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        return self.end - self.start

    def to_json(self) -> dict:
        return {"index": self.index, "start": round(self.start, 3), "end": round(self.end, 3),
                "subjects": [s.to_json() for s in self.subjects], "frame_path": self.frame_path,
                "performers": self.performers}

    @classmethod
    def from_json(cls, d: dict) -> Shot:
        return cls(d["index"], d["start"], d["end"], [Subject.from_json(s) for s in d.get("subjects", [])],
                   d.get("frame_path"), dict(d.get("performers") or {}))


def split_shots(cuts: list[float], duration: float, min_len: float = MIN_SHOT_SEC) -> list[tuple[float, float]]:
    """Cut times -> [(start, end)], merging shots shorter than min_len into a neighbour."""
    bounds = [0.0] + sorted(c for c in cuts if 0.0 < c < duration) + [duration]
    spans = [(a, b) for a, b in itertools.pairwise(bounds) if b > a]
    merged: list[list[float]] = []
    for a, b in spans:
        if merged and (b - a < min_len or merged[-1][1] - merged[-1][0] < min_len):
            merged[-1][1] = b
        else:
            merged.append([a, b])
    if len(merged) > 1 and merged[-1][1] - merged[-1][0] < min_len:
        last = merged.pop()
        merged[-1][1] = last[1]
    return [(round(a, 3), round(b, 3)) for a, b in merged]


def main_shot(shots: list[Shot]) -> Shot:
    return max(shots, key=lambda s: (len(s.subjects), s.duration))


def match_performers(ref: list[tuple[str, np.ndarray]], cand: list[tuple[int, np.ndarray]],
                     max_dist: float = MATCH_MAX_DIST) -> dict[str, int]:
    """Best one-to-one assignment of reference performers to candidate subjects by colour
    distance; pairs above max_dist are dropped."""
    if not ref or not cand:
        return {}
    best: tuple[float, dict[str, int]] = (float("inf"), {})
    k = min(len(ref), len(cand))
    for ref_sel in itertools.combinations(range(len(ref)), k):
        for cand_perm in itertools.permutations(range(len(cand)), k):
            pairs = [(ref[r], cand[c]) for r, c in zip(ref_sel, cand_perm)]
            cost = sum(hist_dist(rh, ch) for (_, rh), (_, ch) in pairs)
            if cost < best[0]:
                best = (cost, {rid: cid for (rid, rh), (cid, ch) in pairs if hist_dist(rh, ch) <= max_dist})
    return best[1]


async def analyze_shots(
    client: ComfyClient, clip: Path, work: Path, *, profile: str, query: str = "person, animal",
) -> tuple[list[Shot], list[str]]:
    """Detect shots and subjects; returns (shots, performer ids) with performers matched."""
    info = await asyncio.to_thread(ingest.probe, clip)
    duration = float(info["frame_count"]) / float(info["fps"]) if info.get("fps") else float(info["duration"])
    cuts = await asyncio.to_thread(ingest._detect_scene_cuts, clip)
    spans = split_shots(cuts, duration)
    shots: list[Shot] = []
    work.mkdir(parents=True, exist_ok=True)
    for i, (a, b) in enumerate(spans):
        frame_path = work / f"shot{i:02d}.png"
        t = min(a + 0.05, max(a, b - 0.05))
        (await asyncio.to_thread(ingest.extract_frame, clip, t)).save(frame_path)
        subjects = await detect_in_image(client, frame_path, query, work / f"shot{i:02d}_det", profile=profile)
        shots.append(Shot(i, a, b, subjects, str(frame_path)))
    if not any(s.subjects for s in shots):
        return shots, []
    main = main_shot(shots)
    with Image.open(main.frame_path) as f:
        ref = [(f"P{j + 1}", subject_head_hist(f, s)) for j, s in enumerate(main.subjects)]
    performer_ids = [pid for pid, _ in ref]
    for shot in shots:
        if not shot.subjects:
            continue
        with Image.open(shot.frame_path) as f:
            cand = [(s.id, subject_head_hist(f, s)) for s in shot.subjects]
        shot.performers = (
            {pid: s.id for pid, s in zip(performer_ids, main.subjects)} if shot is main
            else match_performers(ref, cand)
        )
    return shots, performer_ids
