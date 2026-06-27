import traceback
from typing import Tuple, Literal, Union, Optional
from PIL import Image as PILImage, ImageFilter
from PIL import ImageDraw, ImageFont

Point = Tuple[int, int]

def _load_font(font_family: str, font_sz: float) -> ImageFont.FreeTypeFont:
    """
    Try to load a TrueType/OpenType font. If loading fails (e.g., WOFF2),
    fall back to PIL's default bitmap font to avoid crashing.
    """
    try:
        # Pillow prefers .ttf/.otf. WOFF/WOFF2 generally not supported.
        return ImageFont.truetype(font_family, int(font_sz))
    except Exception:
        print("ERROR", font_family)
        error_trace = traceback.format_exc()
        print(error_trace)


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> Tuple[int, int]:
    """
    Measure text width/height similarly to Wand's metrics.text_width/height.
    Uses textbbox for precise glyph metrics.
    """
    # textbbox returns (left, top, right, bottom)
    bbox = draw.textbbox((0, 0), text, font=font)
    return (bbox[2] - bbox[0], bbox[3] - bbox[1])

def _text_length(font: ImageFont.FreeTypeFont, draw: ImageDraw.ImageDraw, text: str) -> float:
    """
    Preferred width advance using font.getlength (Pillow >= 8.0); fallback to draw.textlength.
    """
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
    stroke_w:float = 0.0
) -> None:
    """
    Emulates Wand's draw.text_kerning by adding *extra* tracking (letter spacing) in pixels.
    Pillow applies built-in font kerning automatically; this adds additional spacing.
    """
    x, y = position
    if not tracking:
        draw.text((x, y), text, font=font, fill=fill,
                  stroke_width=stroke_w, stroke_fill=fill)
        return
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill,
                  stroke_width=stroke_w, stroke_fill=fill)
        adv = _text_length(font, draw, ch)
        x += int(round(adv + tracking))


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> Tuple[int, int]:
    """
    Measure text width/height similarly to Wand's metrics.text_width/height.
    Uses textbbox for precise glyph metrics (ink box).
    """
    bbox = draw.textbbox((0, 0), text, font=font)
    return (bbox[2] - bbox[0], bbox[3] - bbox[1])  # (width, height)


def _normalize_opacity(opacity: Optional[Union[int, float]]) -> int:
    if opacity is None:
        return 255
    if isinstance(opacity, float):
        # accept 0.0–1.0 floats
        return int(round(max(0.0, min(1.0, opacity)) * 255))
    # accept 0–255 ints
    return int(max(0, min(255, opacity)))

def _to_rgba(c, fallback_alpha=255):
    if c is None:
        return None
    if len(c) == 3:
        r, g, b = c
        return (int(r), int(g), int(b), int(fallback_alpha))
    elif len(c) == 4:
        r, g, b, a = c
        if isinstance(a, float):
            a = int(round(max(0.0, min(1.0, a)) * 255))
        return (int(r), int(g), int(b), int(max(0, min(255, a))))
    raise ValueError("Color tuples must be (R,G,B) or (R,G,B,A)")


def execute(
    base_image: PILImage.Image,
    font_sz: float,
    text: str,
    position: Point,
    alignment: Literal['left', 'right'] = 'left',
    font_family: str = None,
    text_color: Union[Tuple[int,int,int], Tuple[int,int,int,int]] = (55, 55, 55),
    kerning: float = 1.0,
    y_limit: Optional[int] = None,
    vertical_bound: Optional[Literal['above','below']] = None,
    opacity: Optional[int] = 254,
    rotate: float = 0.0,  # <-- NEW PARAMETER
    blur_radius: float = 0.0,   # <-- NEW: Gaussian blur radius for drawn text
    stroke_w: float = 0.0,
) -> PILImage.Image:
    """
    Draw text onto `base_image` and return a new Image with the rendering applied.
    `rotate` applies a rotation (deg) to the text overlay.
    `blur_radius` applies a Gaussian blur to the drawn text (overlay only).
    """
    result = base_image.copy()

    # No-op early exit
    if position[0] == 0 and position[1] == 0:
        return result

    # Optional vertical bound
    if y_limit is not None and vertical_bound in ('above', 'below'):
        if vertical_bound == 'above' and position[1] < y_limit:
            return result
        elif vertical_bound == 'below' and position[1] > y_limit:
            return result

    font = _load_font(font_family, font_sz)

    # Normalize color/opacity
    alpha_from_param = _normalize_opacity(opacity)
    fill = _to_rgba(text_color, fallback_alpha=alpha_from_param)

    base_rgba = result.convert("RGBA")
    overlay = PILImage.new("RGBA", base_rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Positioning
    req_x, req_y = int(position[0]), int(position[1])

    native_adv = _text_length(font, draw, text)
    extra_tracking = max(0, len(text) - 1) * float(kerning or 0.0)
    text_w = int(round(native_adv + extra_tracking))

    if alignment.lower() == 'right':
        x_pos = req_x - text_w
    elif alignment.lower() == 'center':
        x_pos = req_x - (text_w // 2)
    else:
        x_pos = req_x
    # ascent, descent = font.getmetrics()
    y_pos = int(req_y)

    _draw_text_with_tracking(draw, (x_pos, y_pos), text, font, fill, float(kerning or 0.0), stroke_w)

    if rotate:
        rotated = overlay.rotate(rotate, resample=PILImage.BICUBIC, expand=True)
        # center it back onto a canvas of original size
        canvas = PILImage.new("RGBA", base_rgba.size, (0, 0, 0, 0))
        off = ((base_rgba.size[0] - rotated.size[0]) // 2,
               (base_rgba.size[1] - rotated.size[1]) // 2)
        canvas.paste(rotated, off, rotated)
        overlay = canvas

    # Apply blur to the text overlay only
    if blur_radius and blur_radius > 0:
        overlay = overlay.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    # Composite text overlay onto base
    result = result.convert("RGBA")
    result.alpha_composite(overlay)

    return result