from typing import Tuple, Union, Optional, Literal
from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont

Point = Tuple[int, int]


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



def execute_centered_between(
    base_image: PILImage.Image,
    font_sz: float,
    text: str,
    x1: int,
    x2: int,
    y: int,  # baseline Y
    font_family: str = None,
    text_color: Union[Tuple[int,int,int], Tuple[int,int,int,int]] = (55, 55, 55),
    kerning: float = 1.0,  # extra tracking in px
    y_limit: Optional[int] = None,
    vertical_bound: Optional[Literal['above','below']] = None,
    opacity: Union[int, float] = 254  # 0–255 or 0.0–1.0
) -> PILImage.Image:
    """
    Draw `text` centered horizontally between x1 and x2, on baseline y.
    Uses an RGBA overlay so opacity always applies (even with RGB text_color).
    Returns a new PIL Image.
    """
    if x2 <= x1:
        raise ValueError("x2 must be greater than x1")

    result = base_image.copy()

    # Optional vertical bound early exit
    if y_limit is not None and vertical_bound in ('above', 'below'):
        if vertical_bound == 'above' and y < y_limit:
            return result
        elif vertical_bound == 'below' and y > y_limit:
            return result

    # ----- Always draw on an RGBA overlay so alpha is respected -----
    base_rgba = result.convert("RGBA")
    overlay = PILImage.new("RGBA", base_rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font = _load_font(font_family, font_sz)

    # ---- Normalize opacity to 0..255 ----
    if isinstance(opacity, float):
        # allow 0.0..1.0
        opacity = int(round(max(0.0, min(1.0, opacity)) * 255))
    else:
        opacity = int(max(0, min(255, opacity)))

    # ---- Normalize color to RGBA with opacity applied ----
    if len(text_color) == 3:
        r, g, b = text_color
        a = opacity
    elif len(text_color) == 4:
        r, g, b, a = text_color
        if isinstance(a, float) and 0.0 <= a <= 1.0:
            a = int(round(a * 255))
        a = int(max(0, min(255, a)))
        # multiply per-pixel alpha by global opacity
        a = int(round(a * (opacity / 255.0)))
    else:
        raise ValueError("text_color must be (R,G,B) or (R,G,B,A)")

    fill = (int(r), int(g), int(b), int(a))

    # ---- compute total advance including extra tracking ----
    base_advance = _glyph_advance(font, draw, text)
    extra_tracking = max(0.0, float(kerning or 0.0)) * max(0, len(text) - 1)
    total_advance = base_advance + extra_tracking

    span_width = x2 - x1
    start_x = int(round(x1 + (span_width - total_advance) / 2.0))
    if total_advance > span_width:
        start_x = x1

    ascent, _descent = font.getmetrics()
    top_y = int(y - ascent)

    _draw_text_with_tracking(draw, (start_x, top_y), text, font, fill, tracking=float(kerning or 0.0))

    # Composite overlay with correct alpha
    result = base_rgba.copy()
    result.alpha_composite(overlay)
    return result
