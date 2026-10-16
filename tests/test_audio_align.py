from __future__ import annotations

import numpy as np
import pytest

from make_meme.analysis.audio_align import SR, align, features, hotspots


def _song(seconds: float, seed: int = 0) -> np.ndarray:
    """Synthetic 'music': random notes on a beat grid with harmonics + light noise."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * SR)) / SR
    out = np.zeros_like(t, dtype=np.float64)
    beat = 0.25
    for k in range(int(seconds / beat)):
        f0 = 110 * 2 ** (rng.integers(0, 36) / 12)
        start, dur = k * beat, beat * rng.choice([1, 2])
        sel = (t >= start) & (t < start + dur)
        env = np.exp(-(t[sel] - start) * 6)
        for h in (1, 2, 3):
            out[sel] += env * np.sin(2 * np.pi * f0 * h * t[sel]) / h
    out += 0.02 * rng.standard_normal(out.size)
    return (out / np.abs(out).max()).astype(np.float32)


@pytest.fixture(scope="module")
def ref():
    audio = _song(90)
    return audio, features(audio)


def test_finds_excerpt_with_noise_and_gain(ref):
    audio, ref_feat = ref
    clip = audio[int(37.3 * SR) : int(47.3 * SR)] * 0.4
    clip = clip + 0.05 * np.random.default_rng(1).standard_normal(clip.size).astype(np.float32)
    a = align(ref_feat, features(clip))
    assert a is not None
    assert a.ref_start == pytest.approx(37.3, abs=0.1)
    assert a.ref_end == pytest.approx(47.3, abs=0.6)
    assert a.speed == 1.0 and a.confidence > 0.5


def test_finds_sped_up_excerpt(ref):
    audio, ref_feat = ref
    excerpt = audio[int(20 * SR) : int(32.5 * SR)]
    # naive resampling = faster *and* higher pitch, like a TikTok "sped up" edit
    idx = np.arange(0, excerpt.size, 1.25).astype(int)
    a = align(ref_feat, features(excerpt[idx]))
    assert a is not None
    assert a.speed == pytest.approx(1.25, abs=0.06)
    assert a.ref_start == pytest.approx(20.0, abs=0.5)


def test_unrelated_audio_does_not_align(ref):
    _, ref_feat = ref
    assert align(ref_feat, features(_song(10, seed=99))) is None


def test_hotspots_pick_most_reused_range(ref):
    audio, ref_feat = ref
    found = []
    for i, (s, e) in enumerate([(40, 48), (41, 49), (39.5, 47), (70, 76)]):
        a = align(ref_feat, features(audio[int(s * SR) : int(e * SR)]))
        assert a is not None
        found.append((i, a))
    top = hotspots(found, duration=90)
    assert top[0].count == 3 and 39 <= top[0].start <= 41.5 and 46 <= top[0].end <= 50


def test_find_hook_detects_repeated_chorus():
    verse1, chorus, verse2, bridge = _song(20, 1), _song(8, 2), _song(20, 3), _song(10, 4)
    track = np.concatenate([verse1, chorus, verse2, chorus, bridge, chorus])
    from make_meme.analysis.audio_align import find_hook

    hook = find_hook(features(track))
    assert hook is not None
    chorus_starts = [20.0, 48.0, 66.0]
    assert any(abs(hook.start - c) <= 1.5 for c in chorus_starts)
    assert len(hook.repeats) >= 1
