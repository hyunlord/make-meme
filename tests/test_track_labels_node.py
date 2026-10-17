"""MakeMemeTrackLabels (companion ComfyUI node) without ComfyUI: the tracker's bit-packing
helper is stubbed with the same algorithm."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "make_meme" / "comfy_nodes"))


def _pack(masks):
    binary = masks > 0
    shifts = torch.arange(8)
    return (binary.view(*masks.shape[:-1], -1, 8) * (1 << shifts)).sum(-1).byte()


def _unpack(packed):
    bits = torch.tensor([1, 2, 4, 8, 16, 32, 64, 128], dtype=torch.uint8)
    return (packed.unsqueeze(-1) & bits).bool().view(*packed.shape[:-1], -1)


@pytest.fixture
def node(monkeypatch):
    tracker = types.ModuleType("comfy.ldm.sam3.tracker")
    tracker.unpack_masks = _unpack
    for name in ("comfy", "comfy.ldm", "comfy.ldm.sam3"):
        monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    monkeypatch.setitem(sys.modules, "comfy.ldm.sam3.tracker", tracker)
    from make_meme_nodes.track_labels import MakeMemeTrackLabels

    return MakeMemeTrackLabels()


def test_labels_keep_object_identities(node):
    masks = torch.zeros(2, 3, 16, 16)  # 2 frames, 3 objects
    masks[0, 0, 2:6, 2:6] = 1
    masks[0, 2, 10:14, 10:14] = 1
    masks[1, 0, 3:7, 3:7] = 1
    masks[1, 1, 3:5, 3:5] = 1  # overlaps object 0: the earlier object wins
    data = {"packed_masks": _pack(masks), "orig_size": (32, 32), "n_frames": 2}
    (out,) = node.labels(data)
    assert out.shape == (2, 32, 32, 3)
    lab = (out[..., 0] * 255).round().int()
    assert lab[0, 8, 8] == 1 and lab[0, 24, 24] == 3 and lab[0, 0, 0] == 0
    assert lab[1, 7, 7] == 1 and set(lab[1].unique().tolist()) == {0, 1}


def test_no_objects_gives_empty_labels(node):
    (out,) = node.labels({"packed_masks": None, "orig_size": (8, 8), "n_frames": 3})
    assert out.shape == (3, 8, 8, 3) and float(out.max()) == 0.0
