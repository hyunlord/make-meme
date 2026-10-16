"""Locate where a short clip's audio comes from inside a longer reference track.

Used to answer "which part of the song do people actually use in memes/shorts?":
each short's soundtrack is aligned against the original MV's audio.

Method: log-energy in 32 log-spaced frequency bands per 32 ms frame (robust to
volume/EQ changes and moderate voice-over), z-normalized per band, then FFT
cross-correlation of overlapping windows of the short against the whole reference.
Sped-up/slowed versions (very common on TikTok/Shorts) are handled by resampling
the short's feature timeline for a few speed factors.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

SR = 8000
N_FFT = 1024
HOP = 256  # 32 ms
FRAME_SEC = HOP / SR
N_BANDS = 32
SPEEDS = (1.0, 1.1, 1.2, 1.25, 1.3, 0.9, 0.8)
OFF_SPEED_MIN_Z = 7.0


@dataclass
class Match:
    ref_start: float  # seconds in the reference where this window's audio starts
    clip_start: float  # seconds in the short
    length: float  # seconds of reference audio covered
    score: float  # peak z-score (higher = more certain)
    speed: float  # playback speed of the short relative to the original


@dataclass
class Alignment:
    ref_start: float
    ref_end: float
    speed: float
    confidence: float  # 0..1
    matches: list[Match]

    @property
    def length(self) -> float:
        return self.ref_end - self.ref_start


def load_audio(path: Path, sr: int = SR) -> np.ndarray:
    """Mono float32 PCM via ffmpeg (any container yt-dlp gives us)."""
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
        capture_output=True, check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"could not decode audio from {path.name}: {proc.stderr.decode(errors='replace')[-300:]}")
    return np.frombuffer(proc.stdout, dtype=np.float32).copy()


def _band_matrix(n_fft: int, sr: int, n_bands: int) -> np.ndarray:
    freqs = np.fft.rfftfreq(n_fft, 1 / sr)
    edges = np.geomspace(80, sr / 2, n_bands + 1)
    m = np.zeros((n_bands, freqs.size), dtype=np.float32)
    for b in range(n_bands):
        sel = (freqs >= edges[b]) & (freqs < edges[b + 1])
        if not sel.any():  # very narrow low bands: take the nearest bin
            sel = np.abs(freqs - (edges[b] + edges[b + 1]) / 2) == np.abs(freqs - (edges[b] + edges[b + 1]) / 2).min()
        m[b, sel] = 1.0 / sel.sum()
    return m


_BANDS = _band_matrix(N_FFT, SR, N_BANDS)


def features(audio: np.ndarray) -> np.ndarray:
    """[frames, bands] log band energies, onset-emphasized and z-normalized per band."""
    if audio.size < N_FFT:
        audio = np.pad(audio, (0, N_FFT - audio.size))
    n_frames = 1 + (audio.size - N_FFT) // HOP
    idx = np.arange(N_FFT)[None, :] + HOP * np.arange(n_frames)[:, None]
    frames = audio[idx] * np.hanning(N_FFT).astype(np.float32)
    power = np.abs(np.fft.rfft(frames, axis=1)) ** 2
    bands = np.log1p(power @ _BANDS.T * 1e4)
    # first difference emphasizes rhythm/onsets, which survive re-encoding and voice-over best
    diff = np.diff(bands, axis=0, prepend=bands[:1])
    feat = np.concatenate([bands, diff], axis=1)
    feat -= feat.mean(axis=0, keepdims=True)
    feat /= feat.std(axis=0, keepdims=True) + 1e-6
    return feat.astype(np.float32)


def _xcorr(ref: np.ndarray, query: np.ndarray) -> np.ndarray:
    """Normalized cross-correlation over lags 0..len(ref)-len(query), summed across feature dims."""
    n = ref.shape[0] + query.shape[0]
    size = 1 << (n - 1).bit_length()
    fr = np.fft.rfft(ref, size, axis=0)
    fq = np.fft.rfft(query[::-1], size, axis=0)
    corr = np.fft.irfft(fr * fq, size, axis=0).sum(axis=1)
    valid = corr[query.shape[0] - 1 : ref.shape[0]]
    return valid / (query.shape[0] * query.shape[1])


def _resample_time(feat: np.ndarray, speed: float) -> np.ndarray:
    """A short sped up by `speed` covers speed× more reference time per frame."""
    if speed == 1.0:
        return feat
    n_out = max(2, round(feat.shape[0] * speed))
    src = np.linspace(0, feat.shape[0] - 1, n_out)
    lo = np.floor(src).astype(int)
    hi = np.minimum(lo + 1, feat.shape[0] - 1)
    w = (src - lo)[:, None]
    return (feat[lo] * (1 - w) + feat[hi] * w).astype(np.float32)


_OCT_PER_BAND = float(np.log2((SR / 2) / 80) / N_BANDS)


def _shift_pitch(feat: np.ndarray, speed: float) -> np.ndarray:
    """Undo the pitch rise of a 'sped up'/nightcore edit (speed changes pitch too):
    move band energies down by log2(speed) octaves."""
    k = round(np.log2(speed) / _OCT_PER_BAND)
    if k == 0:
        return feat
    out = np.zeros_like(feat)
    for part in (slice(0, N_BANDS), slice(N_BANDS, 2 * N_BANDS)):
        block = feat[:, part]
        if k > 0:
            out[:, part][:, : N_BANDS - k] = block[:, k:]
        else:
            out[:, part][:, -k:] = block[:, : N_BANDS + k]
    return out


def _matches_for(ref_feat, q_all, speed, win, hop, min_score):
    w = min(win, q_all.shape[0])
    starts = range(0, max(1, q_all.shape[0] - w + 1), max(1, round(hop * speed)))
    matches: list[Match] = []
    for start in starts:
        corr = _xcorr(ref_feat, q_all[start : start + w])
        peak = int(np.argmax(corr))
        z = float((corr[peak] - corr.mean()) / (corr.std() + 1e-9))
        if z >= min_score:
            matches.append(Match(peak * FRAME_SEC, start * FRAME_SEC / speed, w * FRAME_SEC, z, speed))
    return _consistent(matches), len(starts)


def align(
    ref_feat: np.ndarray,
    clip_feat: np.ndarray,
    *,
    window_sec: float = 5.0,
    hop_sec: float = 2.5,
    min_score: float = 4.5,
    speeds: tuple[float, ...] = SPEEDS,
) -> Alignment | None:
    """Find the reference range a clip uses. Returns None if nothing aligns confidently.

    Original speed is tried first and accepted when at least half of the clip's windows
    agree on one position (most dance-challenge shorts use the official audio as is).
    Otherwise every speed (with and without the pitch shift of a 'sped up' edit) is tried
    and the variant whose windows agree most consistently wins. Raw correlation peaks
    are not compared across speeds: time-stretching smooths features and inflates them."""
    win = round(window_sec / FRAME_SEC)
    hop = round(hop_sec / FRAME_SEC)
    if clip_feat.shape[0] < win // 2 or clip_feat.shape[0] >= ref_feat.shape[0]:
        return None

    clip_sec = clip_feat.shape[0] * FRAME_SEC

    def result(ms: list[Match]) -> Alignment:
        speed = ms[0].speed
        offset = float(np.median([m.ref_start - m.clip_start * speed for m in ms]))
        ref_start = min(m.ref_start for m in ms)
        # the excerpt is contiguous: extend to the clip's end, but not past one hop beyond the
        # last confident window (shorts often end with non-song audio)
        last = max(m.ref_start + m.length for m in ms)
        ref_end = min(offset + clip_sec * speed, last + hop_sec * speed)
        mean_z = sum(m.score for m in ms) / len(ms)
        return Alignment(ref_start, ref_end, ms[0].speed, float(min(1.0, (mean_z - min_score) / 6.0 + 0.3)), ms)

    base, n_base = _matches_for(ref_feat, clip_feat, 1.0, win, hop, min_score)
    if base and len(base) * 2 >= n_base:
        return result(base)

    best: tuple[tuple[float, float], list[Match]] | None = None
    variants = [(sp, False) for sp in speeds] + [(sp, True) for sp in speeds if sp != 1.0]
    for speed, pitched in variants:
        q_all = _resample_time(clip_feat, speed)  # now in reference time units
        if pitched:
            q_all = _shift_pitch(q_all, speed)
        if q_all.shape[0] < win // 2 or q_all.shape[0] >= ref_feat.shape[0]:
            continue
        consistent, n = _matches_for(ref_feat, q_all, speed, win, hop, min_score)
        # off-speed matches are far easier to get by chance (unrelated songs with a similar
        # beat line up at some speed), so demand more and stronger agreeing windows
        if len(consistent) < min(3, n) or sum(m.score for m in consistent) / len(consistent) < OFF_SPEED_MIN_Z:
            continue
        key = (len(consistent) / n, sum(m.score for m in consistent) / len(consistent))
        if best is None or key > best[0]:
            best = (key, consistent)
    return result(best[1]) if best else None


def _consistent(matches: list[Match], tol: float = 0.3) -> list[Match]:
    """Keep the largest group of windows that agree on where the clip sits in the reference
    (ref_start - clip_start*speed is constant for a contiguous excerpt)."""
    if not matches:
        return []
    keys = [m.ref_start - m.clip_start * m.speed for m in matches]
    best: list[Match] = []
    for k in keys:
        group = [m for m, kk in zip(matches, keys) if abs(kk - k) <= tol]
        if len(group) > len(best) or (len(group) == len(best) and sum(g.score for g in group) > sum(b.score for b in best)):
            best = group
    return best


@dataclass
class Hotspot:
    start: float
    end: float
    count: int  # how many clips use (most of) this range
    clips: list[int]


def hotspots(alignments: list[tuple[int, Alignment]], duration: float, top: int = 3) -> list[Hotspot]:
    """Most-reused ranges of the reference: coverage histogram (0.5 s bins) → peaks."""
    if not alignments:
        return []
    bins = np.zeros(int(duration / 0.5) + 2)
    who: list[set[int]] = [set() for _ in range(bins.size)]
    for idx, a in alignments:
        lo, hi = int(a.ref_start / 0.5), int(a.ref_end / 0.5)
        bins[lo : hi + 1] += a.confidence
        for b in range(lo, min(hi + 1, bins.size)):
            who[b].add(idx)
    found: list[Hotspot] = []
    used = np.zeros_like(bins, dtype=bool)
    for _ in range(top):
        masked = np.where(used, 0, bins)
        peak = int(np.argmax(masked))
        if masked[peak] <= 0:
            break
        thresh = masked[peak] * 0.5
        lo = peak
        while lo > 0 and masked[lo - 1] >= thresh:
            lo -= 1
        hi = peak
        while hi < bins.size - 1 and masked[hi + 1] >= thresh:
            hi += 1
        clips = sorted(set().union(*who[lo : hi + 1]))
        found.append(Hotspot(lo * 0.5, (hi + 1) * 0.5, len(clips), clips))
        used[max(0, lo - 4) : hi + 5] = True
    return found


@dataclass
class Hook:
    start: float
    end: float
    repeats: list[float]  # other start times where the same section recurs
    score: float


def find_hook(ref_feat: np.ndarray, *, window_sec: float = 8.0, hop_sec: float = 1.0,
              min_score: float = 5.0) -> Hook | None:
    """The most-repeated section of a song (usually the chorus/hook, which is what memes
    tend to use): each window is correlated against the rest of the track."""
    win = round(window_sec / FRAME_SEC)
    hop = round(hop_sec / FRAME_SEC)
    if ref_feat.shape[0] < 3 * win:
        return None
    best: Hook | None = None
    for start in range(0, ref_feat.shape[0] - win, hop):
        corr = _xcorr(ref_feat, ref_feat[start : start + win])
        mean, std = corr.mean(), corr.std() + 1e-9
        corr = corr.copy()
        corr[max(0, start - win) : start + win] = mean  # ignore self-match
        repeats: list[float] = []
        total = 0.0
        for _ in range(3):  # up to 3 recurrences
            peak = int(np.argmax(corr))
            z = (corr[peak] - mean) / std
            if z < min_score:
                break
            repeats.append(round(peak * FRAME_SEC, 2))
            total += z
            corr[max(0, peak - win // 2) : peak + win // 2] = mean
        if repeats and (best is None or total > best.score):
            best = Hook(start * FRAME_SEC, (start + win) * FRAME_SEC, sorted(repeats), float(total))
    return best
