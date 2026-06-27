from typing import Tuple, Union, Optional, Literal
from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont

from _pillow.wrap_utils import fix_punctuation_wrap

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
    tracking: float,
    stroke_width: float = 0.0
) -> None:
    """Draw per-glyph, adding extra tracking (letter spacing) in pixels."""
    x, y = position
    stroke_w = int(stroke_width)
    if not tracking:
        draw.text((x, y), text, font=font, fill=fill,
                  stroke_width=stroke_w, stroke_fill=fill)
        return

    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill,
                  stroke_width=stroke_w, stroke_fill=fill)
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
    text_color: Union[Tuple[int, int, int],
                      Tuple[int, int, int, int]] = (55, 55, 55),
    kerning: float = 1.0,  # extra tracking in px
    y_limit: Optional[int] = None,
    vertical_bound: Optional[Literal['above', 'below']] = None,
    opacity: Union[int, float] = 254,  # 0–255 or 0.0–1.0
    slant: float = 0.0  # slant angle in degrees (positive = right lean)
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

    _draw_text_with_tracking(draw, (start_x, top_y), text, font, fill, tracking=float(
        kerning or 0.0), stroke_width=0.0)

    # Apply slant transformation if requested (simple version)
    if slant and slant != 0.0:
        import math
        # Convert degrees to radians and calculate shear factor
        slant_radians = math.radians(slant)
        shear_factor = math.tan(slant_radians)

        # Simple affine transform - no cropping, just shear in place
        # Matrix: [1, shear, 0, 0, 1, 0] = horizontal shear only
        width, height = overlay.size

        transform_matrix = (
            1, shear_factor, 0,
            0, 1, 0
        )

        # Apply transformation with same dimensions (text will stay centered)
        overlay = overlay.transform(
            overlay.size,
            PILImage.AFFINE,
            transform_matrix,
            resample=PILImage.BICUBIC,
            fillcolor=(0, 0, 0, 0)
        )

    # Composite overlay with correct alpha
    result = base_rgba.copy()
    result.alpha_composite(overlay)
    return result


def execute_centered_paragraph(
    base_image: PILImage.Image,
    text: str,
    center_x: int,
    top_y: int,
    font_size: int,
    font_family: str,
    text_color: Union[Tuple[int, int, int],
                      Tuple[int, int, int, int]] = (255, 255, 255),
    line_spacing: float = 1.3,
    kerning: float = 0.0,
    opacity: Union[int, float] = 255,
    stroke_width: float = 0.0,
    max_width: Optional[int] = None,
) -> PILImage.Image:
    """
    Draw a centered multi-line paragraph.

    Parameters:
    -----------
    base_image : PILImage.Image
        Base image to draw on
    text : str
        Text to draw (can contain \\n for explicit line breaks)
    center_x : int
        X coordinate of center line
    top_y : int
        Y coordinate of first line
    font_size : int
        Font size in pixels
    font_family : str
        Path to font file
    text_color : tuple
        RGB or RGBA color (default: white)
    line_spacing : float
        Line height multiplier (default: 1.3)
    kerning : float
        Letter spacing in pixels (default: 0.0)
    opacity : int or float
        Opacity 0-255 or 0.0-1.0 (default: 255)
    stroke_width : float
        Stroke width to make text bolder (default: 0.0)
    max_width : int, optional
        Maximum width for automatic word wrapping (default: None - no wrapping)

    Returns:
    --------
    PILImage.Image
        New image with centered paragraph drawn
    """
    result = base_image.copy().convert("RGBA")
    overlay = PILImage.new("RGBA", result.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font = _load_font(font_family, font_size)

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

    # Word wrap function
    def wrap_text(text: str, max_width: Optional[int]) -> list:
        # If no max_width, just split by \n without word wrapping
        if max_width is None:
            return text.split('\n')

        lines = []
        paragraphs = text.split('\n')

        for paragraph in paragraphs:
            words = paragraph.split()
            current_line = []

            for word in words:
                test_line = ' '.join(current_line + [word])
                base_advance = _glyph_advance(font, draw, test_line)
                extra_tracking = max(0.0, float(kerning)) * \
                    max(0, len(test_line) - 1)
                width = base_advance + extra_tracking

                if width <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]

            if current_line:
                lines.append(' '.join(current_line))

        return lines

    # Wrap text into lines
    lines = fix_punctuation_wrap(wrap_text(text, max_width))

    # Calculate line height
    ascent, descent = font.getmetrics()
    line_height = int((ascent + descent) * line_spacing)

    # Draw each line centered
    y = top_y
    for line in lines:
        # Calculate total width with kerning
        base_advance = _glyph_advance(font, draw, line)
        extra_tracking = max(0.0, float(kerning)) * max(0, len(line) - 1)
        total_width = base_advance + extra_tracking

        # Calculate centered x position
        start_x = int(center_x - total_width / 2.0)

        # Draw with tracking using existing helper
        _draw_text_with_tracking(draw, (start_x, y), line, font, fill, tracking=float(
            kerning), stroke_width=stroke_width)

        y += line_height

    # Composite overlay onto base
    result.alpha_composite(overlay)
    return result
