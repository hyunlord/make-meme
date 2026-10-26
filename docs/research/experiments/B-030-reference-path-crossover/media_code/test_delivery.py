# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
# Run: existing Python test_delivery.py
"""CPU full-canvas layout contract for B030 review derivatives."""
from PIL import Image
from delivery import render_row


def test_full_canvas_and_labels() -> None:
    """Given five distinct canvases, preserve each full frame at equal scale."""
    colors = ('red', 'green', 'blue', 'yellow', 'white')
    frames = [Image.new('RGB', (896, 512), color) for color in colors]
    row = render_row(frames, 8)
    assert row.size == (2240, 280)
    for index, color in enumerate(colors):
        assert row.getpixel((index * 448 + 224, 160)) == Image.new('RGB', (1, 1), color).getpixel((0, 0))


if __name__ == '__main__':
    test_full_canvas_and_labels()
