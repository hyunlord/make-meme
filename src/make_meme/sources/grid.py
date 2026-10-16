"""Render a numbered contact-sheet grid of search candidates for the user to pick from."""

from __future__ import annotations

import asyncio
import logging
from io import BytesIO

import httpx
from PIL import Image, ImageDraw, ImageFont

from .models import Candidate
from .utils import format_duration

logger = logging.getLogger(__name__)

COLS = 4
VIDEO_CELL = (320, 180)
IMAGE_CELL = (240, 240)
CAPTION_HEIGHT = 24
PADDING = 8
MAX_GRID_WIDTH = 1600
MAX_CONCURRENT_DOWNLOADS = 8
THUMBNAIL_TIMEOUT = 5.0
TITLE_MAX_CHARS = 28

# Fonts that support Korean, tried in order -- search thumbnails/titles are often Korean.
_FONT_CANDIDATES = [
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _load_font(size: int) -> ImageFont.ImageFont:
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _placeholder(size: tuple[int, int]) -> Image.Image:
    return Image.new("RGB", size, color=(80, 80, 80))


async def _fetch_thumbnail(client: httpx.AsyncClient, url: str | None) -> Image.Image | None:
    if not url:
        return None
    try:
        resp = await client.get(url, timeout=THUMBNAIL_TIMEOUT)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content)).convert("RGB")
    except Exception as e:  # noqa: BLE001 - any failure here degrades to a placeholder, never aborts the grid
        logger.debug("thumbnail fetch failed for %s: %s", url, e)
        return None


def _letterbox(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_w, target_h = size
    src_w, src_h = img.size
    scale = min(target_w / src_w, target_h / src_h) if src_w and src_h else 1.0
    new_w, new_h = max(1, round(src_w * scale)), max(1, round(src_h * scale))
    resized = img.resize((new_w, new_h))
    canvas = Image.new("RGB", size, color=(20, 20, 20))
    canvas.paste(resized, ((target_w - new_w) // 2, (target_h - new_h) // 2))
    return canvas


def _caption_for(c: Candidate) -> str:
    if c.kind == "video":
        base = format_duration(c.duration)
    else:
        base = f"{c.width}x{c.height}" if c.width and c.height else ""
    title = (c.title or "").strip()
    if title and len(title) > TITLE_MAX_CHARS:
        title = title[: TITLE_MAX_CHARS - 1] + "..."
    return f"{base} {title}".strip() if title else base


def _empty_grid() -> Image.Image:
    img = Image.new("RGB", (400, 100), color=(30, 30, 30))
    draw = ImageDraw.Draw(img)
    draw.text((10, 40), "No candidates", fill=(255, 255, 255), font=_load_font(16))
    return img


async def build_candidate_grid(candidates: list[Candidate]) -> Image.Image:
    """Render a numbered contact-sheet grid of ``candidates``.

    Thumbnails are fetched concurrently (capped at ``MAX_CONCURRENT_DOWNLOADS``,
    each with a ``THUMBNAIL_TIMEOUT``-second budget); any that fail are
    replaced with a gray placeholder so one bad URL never blocks the grid.
    Each cell gets a numeric badge (top-left, matching ``Candidate.index``)
    and a caption (duration for video, dimensions for image, plus a
    truncated title). The returned image is at most ``MAX_GRID_WIDTH`` wide.
    """

    if not candidates:
        return _empty_grid()

    sem = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)

    async def _get(c: Candidate) -> Image.Image:
        async with sem, httpx.AsyncClient() as client:
            img = await _fetch_thumbnail(client, c.thumbnail_url)
        size = VIDEO_CELL if c.kind == "video" else IMAGE_CELL
        return _letterbox(img, size) if img is not None else _placeholder(size)

    thumbnails = await asyncio.gather(*(_get(c) for c in candidates))

    cols = COLS
    rows = (len(candidates) + cols - 1) // cols
    cell_w = max(VIDEO_CELL[0], IMAGE_CELL[0])
    cell_h = max(VIDEO_CELL[1], IMAGE_CELL[1]) + CAPTION_HEIGHT
    grid_w = cols * cell_w + (cols + 1) * PADDING
    grid_h = rows * cell_h + (rows + 1) * PADDING

    canvas = Image.new("RGB", (grid_w, grid_h), color=(15, 15, 15))
    draw = ImageDraw.Draw(canvas)
    badge_font = _load_font(20)
    caption_font = _load_font(14)

    for idx, (c, thumb) in enumerate(zip(candidates, thumbnails)):
        row, col = divmod(idx, cols)
        x = PADDING + col * (cell_w + PADDING)
        y = PADDING + row * (cell_h + PADDING)
        thumb_x = x + (cell_w - thumb.width) // 2
        canvas.paste(thumb, (thumb_x, y))

        draw.rectangle([thumb_x, y, thumb_x + 28, y + 24], fill=(0, 0, 0))
        draw.text((thumb_x + 6, y + 2), str(c.index), fill=(255, 255, 255), font=badge_font)

        draw.text(
            (x + 4, y + thumb.height + 2), _caption_for(c), fill=(230, 230, 230), font=caption_font
        )

    if canvas.width > MAX_GRID_WIDTH:
        ratio = MAX_GRID_WIDTH / canvas.width
        canvas = canvas.resize((MAX_GRID_WIDTH, round(canvas.height * ratio)))

    return canvas
