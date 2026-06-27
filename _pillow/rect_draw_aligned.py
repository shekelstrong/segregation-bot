from __future__ import annotations

from typing import Literal

from PIL import Image as PILImage
from PIL import ImageDraw

HorizontalAlign = Literal["left", "center", "right"]


def _resolve_rect(
    *,
    container_box: tuple[int, int, int, int],
    rect_width: int | float,
    min_width: int = 1,
    align: HorizontalAlign = "center",
) -> tuple[int, int, int, int]:
    left, top, right, bottom = container_box
    container_width = max(1, right - left)

    width = int(round(rect_width))
    width = max(int(min_width), min(width, container_width))

    if align == "left":
        rect_left = left
    elif align == "right":
        rect_left = right - width
    elif align == "center":
        rect_left = int(round(left + ((container_width - width) / 2.0)))
    else:
        raise ValueError("align must be one of: left, center, right")

    rect_right = rect_left + width
    if rect_left < left:
        rect_left = left
        rect_right = rect_left + width
    if rect_right > right:
        rect_right = right
        rect_left = rect_right - width

    return rect_left, top, rect_right, bottom


def execute(
    *,
    base_image: PILImage.Image,
    container_box: tuple[int, int, int, int],
    rect_width: int | float,
    fill: tuple[int, int, int] | tuple[int, int, int, int],
    radius: int = 0,
    align: HorizontalAlign = "center",
    min_width: int = 1,
    clear_fill: tuple[int, int, int] | tuple[int, int, int, int] | None = None,
) -> tuple[PILImage.Image, tuple[int, int, int, int]]:
    """
    Draw one rectangle horizontally aligned inside `container_box`.
    Returns the composited image and resulting rectangle coords.
    """
    result = base_image.convert("RGBA").copy()
    draw = ImageDraw.Draw(result)

    if clear_fill is not None:
        draw.rectangle(container_box, fill=clear_fill)

    rect = _resolve_rect(
        container_box=container_box,
        rect_width=rect_width,
        min_width=min_width,
        align=align,
    )

    if radius > 0:
        draw.rounded_rectangle(rect, radius=radius, fill=fill)
    else:
        draw.rectangle(rect, fill=fill)

    return result, rect

