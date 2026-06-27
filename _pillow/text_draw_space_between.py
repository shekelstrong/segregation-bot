from typing import List, Sequence, Tuple, Union
from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont


def _load_font(font_family: str, font_sz: float) -> ImageFont.FreeTypeFont:
    """Try to load TTF/OTF; fall back to PIL default if not supported."""
    try:
        return ImageFont.truetype(font_family, int(font_sz))
    except Exception:
        return ImageFont.load_default()

def _glyph_advance(font: ImageFont.FreeTypeFont, draw: ImageDraw.ImageDraw, text: str) -> float:
    """Preferred x-advance using font.getlength when available; fallback to draw.textlength."""
    if hasattr(font, "getlength"):
        return font.getlength(text)
    return draw.textlength(text, font=font)

def _draw_text_with_tracking(
    draw: ImageDraw.ImageDraw,
    position: Tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: Tuple[int, int, int, int],
    tracking: float
) -> None:
    """Draw per-glyph, adding extra tracking (letter spacing) in pixels."""
    x, y = position
    if not tracking:
        draw.text((x, y), text, font=font, fill=fill)
        return

    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        adv = _glyph_advance(font, draw, ch)
        x += int(round(adv + tracking))


def execute_space_between(
    base_image: PILImage.Image,
    font_sz: float,
    texts: Sequence[str],
    x1: int,
    x2: int,
    y: int,  # baseline Y for all items
    font_family: str = None,
    text_color: Union[Tuple[int,int,int], Tuple[int,int,int,int]] = (55, 55, 55),
    kerning: float = 1.0,   # extra tracking (px) between glyphs
    opacity: Union[int, float] = 254,  # 0–255 or 0.0–1.0
    min_gap: int = 0,       # when overflow, minimum gap enforced between items
    return_positions: bool = False     # optionally return [x_start] positions
) -> Union[PILImage.Image, Tuple[PILImage.Image, List[int]]]:
    """
    Draw `texts` horizontally between x1..x2 with CSS-like SPACE_BETWEEN distribution.
      - If only one item: it is horizontally centered between x1..x2 (same as execute_centered_between).
      - If the sum of text widths exceeds the span, items are drawn left-to-right starting at x1 with
        equal gaps clamped to `min_gap` (no overlap).
      - All items share the same baseline `y`.

    Returns the composited image (and optionally the x-start positions).
    """
    if x2 <= x1:
        raise ValueError("x2 must be greater than x1")
    if not texts:
        return base_image.copy()

    result = base_image.copy()
    base_rgba = result.convert("RGBA")
    overlay = PILImage.new("RGBA", base_rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font = _load_font(font_family, font_sz)

    # Normalize opacity
    if isinstance(opacity, float):
        opacity = int(round(max(0.0, min(1.0, opacity)) * 255))
    else:
        opacity = int(max(0, min(255, opacity)))

    # Normalize color to RGBA
    if len(text_color) == 3:
        r, g, b = text_color
        a = opacity
    elif len(text_color) == 4:
        r, g, b, a = text_color
        if isinstance(a, float) and 0.0 <= a <= 1.0:
            a = int(round(a * 255))
        a = int(max(0, min(255, a)))
        a = int(round(a * (opacity / 255.0)))
    else:
        raise ValueError("text_color must be (R,G,B) or (R,G,B,A)")
    fill = (int(r), int(g), int(b), int(a))

    # Measure each string (advance + tracking)
    advances: List[float] = []
    for t in texts:
        base_adv = _glyph_advance(font, draw, t)
        extra = max(0.0, float(kerning or 0.0)) * max(0, len(t) - 1)
        advances.append(base_adv + extra)

    span = x2 - x1
    total_width = sum(advances)

    n = len(texts)
    x_starts: List[int] = []

    if n == 1:
        # Center single item
        start_x = int(round(x1 + (span - advances[0]) / 2.0))
        x_starts = [max(x1, min(x2, start_x))]
    else:
        if total_width <= span:
            # Perfect SPACE_BETWEEN: equal gaps so first sits at x1, last ends at x2.
            gap = (span - total_width) / (n - 1)
            cur_x = float(x1)
            for adv in advances:
                x_starts.append(int(round(cur_x)))
                cur_x += adv + gap
        else:
            # Overflow: pack left-to-right starting at x1 with clamped equal gaps.
            # Choose the largest non-negative gap we can maintain.
            # If even min_gap causes overflow, we still enforce min_gap and allow text to extend beyond x2.
            gap = float(min_gap)
            cur_x = float(x1)
            for adv in advances:
                x_starts.append(int(round(cur_x)))
                cur_x += adv + gap

    # Vertical placement (baseline -> top)
    ascent, _descent = font.getmetrics()
    top_y = int(y - ascent)

    # Draw all strings
    for t, x_start in zip(texts, x_starts):
        _draw_text_with_tracking(draw, (x_start, top_y), t, font, fill, tracking=float(kerning or 0.0))

    # Composite
    result = base_rgba.copy()
    result.alpha_composite(overlay)

    if return_positions:
        return result, x_starts
    return result
