from typing import Tuple, Literal, Union, Optional
from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont

Point = Tuple[int, int]

def _load_font(font_family: str, font_sz: float) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(font_family, int(font_sz))
    except Exception:
        return ImageFont.load_default()

def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> Tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return (bbox[2] - bbox[0], bbox[3] - bbox[1])

def _text_length(font: ImageFont.FreeTypeFont, draw: ImageDraw.ImageDraw, text: str) -> float:
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
    x, y = position
    if not tracking:
        draw.text((x, y), text, font=font, fill=fill)
        return
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        adv = _text_length(font, draw, ch)
        x += int(round(adv + tracking))

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
    *,
    background_color: Optional[Union[Tuple[int,int,int], Tuple[int,int,int,int]]] = None,
    background_padding: Union[int, Tuple[int,int,int,int]] = 0,
    background_radius: int = 0,  # 🔹 NEW PARAMETER
    min_background_width: Optional[int] = None,   # 🔹 NEW
) -> PILImage.Image:
    """
    Draw `text` onto `base_image` with optional background (color, padding, rounded corners).
    The Y in `position` is the baseline.
    """
    result = base_image.copy()

    if position == (0, 0):
        return result

    # Handle vertical boundaries
    if y_limit is not None and vertical_bound in ('above', 'below'):
        if vertical_bound == 'above' and position[1] < y_limit:
            return result
        elif vertical_bound == 'below' and position[1] > y_limit:
            return result

    def _to_rgba(c):
        if c is None:
            return None
        if len(c) == 3:
            r, g, b = c
            return (r, g, b, 255)
        elif len(c) == 4:
            r, g, b, a = c
            if isinstance(a, float):
                a = int(round(a * 255))
            return (int(r), int(g), int(b), int(a))
        else:
            raise ValueError("Color tuples must be (R,G,B) or (R,G,B,A)")

    fill = _to_rgba(text_color)
    bg_fill = _to_rgba(background_color)

    needs_alpha = (fill and fill[3] < 255) or (bg_fill and bg_fill[3] < 255)

    if needs_alpha or bg_fill:
        base_rgba = result.convert("RGBA")
        overlay = PILImage.new("RGBA", base_rgba.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
    else:
        draw = ImageDraw.Draw(result)

    font = _load_font(font_family, font_sz)
    req_x, req_y = position
    ascent, descent = font.getmetrics()
    y_top = int(req_y - ascent)

    native_adv = _text_length(font, draw, text)
    extra_tracking = max(0.0, float(kerning or 0.0)) * max(0, len(text) - 1)
    total_adv = int(round(native_adv + extra_tracking))
    text_height = int(ascent + descent)

    x_pos = req_x - total_adv if alignment.lower() == 'right' else req_x

    # Padding parsing
    if isinstance(background_padding, int):
        pad_left = pad_top = pad_right = pad_bottom = int(background_padding)
    else:
        pad_left, pad_top, pad_right, pad_bottom = map(int, background_padding)

    # --- Background rectangle (optional rounded) ---
    if bg_fill:
        rect_left = x_pos - pad_left
        rect_top = y_top - pad_top
        rect_right = x_pos + total_adv + pad_right
        rect_bottom = y_top + text_height + pad_bottom

        # 🔹 Enforce minimum background width (including padding)
        if min_background_width is not None:
            current_w = rect_right - rect_left
            if current_w < min_background_width:
                deficit = min_background_width - current_w
                if alignment.lower() == 'left':
                    # grow to the right
                    rect_right += deficit
                else:  # alignment == 'right'
                    # grow to the left
                    rect_left -= deficit

        if background_radius > 0:
            draw.rounded_rectangle(
                [rect_left, rect_top, rect_right, rect_bottom],
                radius=int(background_radius),
                fill=bg_fill
            )
        else:
            draw.rectangle([rect_left, rect_top, rect_right, rect_bottom], fill=bg_fill)

    # Draw text
    _draw_text_with_tracking(draw, (x_pos, y_top), text, font, fill, tracking=float(kerning or 0.0))

    if needs_alpha or bg_fill:
        result = result.convert("RGBA")
        result.alpha_composite(overlay)

    return result