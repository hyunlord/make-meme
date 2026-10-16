"""Tests for make_meme.chunking: Wan 4n+1 chunk planning invariants."""

from __future__ import annotations

import itertools

import pytest

from make_meme.chunking import estimate_seconds, plan_chunks


def _length(chunk):
    return (chunk.end - chunk.start) + chunk.pad


@pytest.mark.parametrize("total_frames", [1, 5, 80, 81, 82, 161, 162, 200, 1000])
def test_all_chunk_lengths_satisfy_4n_plus_1(total_frames):
    chunks = plan_chunks(total_frames, chunk_len=81, overlap=1)
    for chunk in chunks:
        length = _length(chunk)
        assert (length - 1) % 4 == 0, f"chunk length {length} is not 4n+1"


@pytest.mark.parametrize("total_frames", [1, 5, 80, 81, 82, 161, 162, 200, 1000])
def test_full_coverage(total_frames):
    chunks = plan_chunks(total_frames, chunk_len=81, overlap=1)
    covered: set[int] = set()
    for chunk in chunks:
        covered.update(range(chunk.start, chunk.end))
    assert covered == set(range(total_frames))


def test_overlap_between_consecutive_chunks():
    chunks = plan_chunks(300, chunk_len=81, overlap=5)
    assert len(chunks) > 1
    for prev, nxt in itertools.pairwise(chunks):
        assert prev.end - nxt.start == 5


def test_zero_overlap_is_contiguous():
    chunks = plan_chunks(200, chunk_len=81, overlap=0)
    assert len(chunks) > 1
    for prev, nxt in itertools.pairwise(chunks):
        assert nxt.start == prev.end


def test_single_chunk_when_shorter_than_chunk_len():
    chunks = plan_chunks(10, chunk_len=81, overlap=1)
    assert len(chunks) == 1
    assert chunks[0].start == 0
    assert chunks[0].end == 10


def test_empty_input_yields_no_chunks():
    assert plan_chunks(0) == []
    assert plan_chunks(-5) == []


def test_invalid_chunk_len_rejected():
    with pytest.raises(ValueError):
        plan_chunks(100, chunk_len=80)  # not of the form 4n+1


def test_invalid_overlap_rejected():
    with pytest.raises(ValueError):
        plan_chunks(100, chunk_len=81, overlap=81)
    with pytest.raises(ValueError):
        plan_chunks(100, chunk_len=81, overlap=-1)


def test_estimate_seconds_scales_with_chunks_and_quality():
    draft = estimate_seconds(162, "draft", seconds_per_chunk=10.0)
    high = estimate_seconds(162, "high", seconds_per_chunk=10.0)
    assert draft > 0
    assert high > draft


def test_estimate_seconds_at_least_one_chunk_for_tiny_input():
    assert estimate_seconds(1, "draft", seconds_per_chunk=10.0) == pytest.approx(10.0)
