"""CPU-only frame-order and RGB contract for the Bernini ARM reader."""

from io import BytesIO
from pathlib import Path
from fractions import Fraction
import subprocess
import sys
import hashlib
import json
from tempfile import TemporaryDirectory

import av
import numpy as np

from decord_compat import VideoReader, cpu


def clip(tmp_path: Path) -> tuple[Path, np.ndarray]:
    frames = np.zeros((7, 32, 48, 3), dtype=np.uint8)
    for index in range(7):
        frames[index, :, :, 0] = index * 30
        frames[index, :, 8:24, 1] = 200
        frames[index, 5:20, :, 2] = 80
    path = tmp_path / "fixture.mkv"
    with av.open(str(path), "w") as output:
        stream = output.add_stream("ffv1", rate=Fraction(24, 1))
        stream.width, stream.height, stream.pix_fmt = 48, 32, "bgr0"
        for pixels in frames:
            for packet in stream.encode(av.VideoFrame.from_ndarray(pixels, format="rgb24")):
                output.mux(packet)
        for packet in stream.encode():
            output.mux(packet)
    return path, frames


def test_path_and_bytes_preserve_frames(clip: tuple[Path, np.ndarray]) -> None:
    path, frames = clip
    for source in (str(path), BytesIO(path.read_bytes())):
        reader = VideoReader(source, num_threads=1, ctx=cpu(0), fault_tol=1)
        reader.seek(0)
        assert len(reader) == 7
        assert reader.get_avg_fps() == 24.0
        np.testing.assert_array_equal(reader.get_batch([6, 0, 3, 3]).asnumpy(), frames[[6, 0, 3, 3]])
        try:
            reader.get_batch([7])
        except IndexError:
            rejected = True
        else:
            rejected = False
        assert rejected


def test_ffmpeg_rgb_equivalence(clip: tuple[Path, np.ndarray]) -> None:
    path, _ = clip
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        check=True, capture_output=True,
    ).stdout
    expected = np.frombuffer(raw, dtype=np.uint8).reshape(7, 32, 48, 3)
    np.testing.assert_array_equal(VideoReader(str(path)).get_batch(range(7)).asnumpy(), expected)


def test_reject_gpu() -> None:
    try:
        cpu(1)
    except ValueError:
        rejected = True
    else:
        rejected = False
    assert rejected


def verify_real_clip(path: str) -> None:
    reader = VideoReader(path)
    pixels = reader.get_batch(range(len(reader))).asnumpy()
    raw = subprocess.run(
        ["/usr/bin/ffmpeg", "-v", "error", "-i", path,
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        check=True, capture_output=True,
    ).stdout
    assert pixels.tobytes() == raw
    print(json.dumps({
        "frames": len(reader), "fps": reader.get_avg_fps(),
        "shape": list(pixels.shape), "rgb_sha256": hashlib.sha256(raw).hexdigest(),
        "ffmpeg_exact": True, "decord_equivalence": "UNVERIFIED",
    }))


if __name__ == "__main__":
    with TemporaryDirectory() as directory:
        fixture = clip(Path(directory))
        test_path_and_bytes_preserve_frames(fixture)
        test_ffmpeg_rgb_equivalence(fixture)
        test_reject_gpu()
    print("PASS: path/BytesIO order duplicates fps RGB ffmpeg equivalence and rejection")
    if len(sys.argv) > 1:
        verify_real_clip(sys.argv[1])
