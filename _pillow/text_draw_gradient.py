from typing import Tuple, Literal, Union, Optional, Sequence
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

def _normalize_opacity(opacity: Optional[Union[int, float]]) -> int:
    if opacity is None:
        return 255
    if isinstance(opacity, float):
        return int(round(max(0.0, min(1.0, opacity)) * 255))
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

# ---------- NEW: gradient helpers ----------

def _interpolate(a: int, b: int, t: float) -> int:
    return int(round(a + (b - a) * t))

def _lerp_color(c1: Tuple[int,int,int,int], c2: Tuple[int,int,int,int], t: float) -> Tuple[int,int,int,int]:
    return (
        _interpolate(c1[0], c2[0], t),
        _interpolate(c1[1], c2[1], t),
        _interpolate(c1[2], c2[2], t),
        _interpolate(c1[3], c2[3], t),
    )

def _normalize_stops(stops: Optional[Sequence[float]], n: int) -> Sequence[float]:
    if not stops or len(stops) != n:
        # even spacing
        return [i/(n-1) if n > 1 else 0.0 for i in range(n)]
    # clamp & sort by position along with colors upstream (we'll assume sanity here)
    return [max(0.0, min(1.0, float(s))) for s in stops]

def _make_linear_gradient(size: Tuple[int,int],
                          colors: Sequence[Tuple[int,int,int,int]],
                          stops: Optional[Sequence[float]] = None,
                          direction: Literal["horizontal","vertical"]="horizontal"
                          ) -> PILImage.Image:
    """
    Create an RGBA linear gradient image of `size`.
    `colors`: list of RGBA color stops (>=2).
    `stops`: positions in [0,1] for each color (same length as colors). If None -> even.
    """
    w, h = size
    assert w > 0 and h > 0
    assert len(colors) >= 2
    pos = _normalize_stops(stops, len(colors))
    # ensure tuples & clamp
    cols = [ _to_rgba(c) for c in colors ]

    # 1px-thick strip, then resize for speed
    if direction == "horizontal":
        strip = PILImage.new("RGBA", (w, 1))
        px = strip.load()
        for x in range(w):
            t = x/(w-1) if w > 1 else 0.0
            # find segment
            for i in range(len(cols)-1):
                if t <= pos[i+1] or i == len(cols)-2:
                    # local t in this segment
                    denom = (pos[i+1]-pos[i]) or 1e-9
                    lt = max(0.0, min(1.0, (t - pos[i]) / denom))
                    px[x,0] = _lerp_color(cols[i], cols[i+1], lt)
                    break
        return strip.resize((w, h), resample=PILImage.BILINEAR)
    else:
        strip = PILImage.new("RGBA", (1, h))
        px = strip.load()
        for y in range(h):
            t = y/(h-1) if h > 1 else 0.0
            for i in range(len(cols)-1):
                if t <= pos[i+1] or i == len(cols)-2:
                    denom = (pos[i+1]-pos[i]) or 1e-9
                    lt = max(0.0, min(1.0, (t - pos[i]) / denom))
                    px[0,y] = _lerp_color(cols[i], cols[i+1], lt)
                    break
        return strip.resize((w, h), resample=PILImage.BILINEAR)

# -------------------------------------------

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
    # -------- NEW gradient parameters --------
    gradient_colors: Optional[Sequence[Tuple[int,int,int] | Tuple[int,int,int,int]]] = None,
    gradient_stops: Optional[Sequence[float]] = None,
    gradient_direction: Literal["horizontal","vertical"] = "horizontal",
) -> PILImage.Image:
    """
    Draw `text` onto `base_image` and return a new Image with the rendering applied.
    `position[1]` is treated as the text baseline (ink box bottom alignment).

    If `gradient_colors` is provided (>=2 colors), the text is filled with a linear
    gradient; otherwise `text_color` is used as a solid fill.
    """
    result = base_image.copy()

    if position[0] == 0 and position[1] == 0:
        return result

    if y_limit is not None and vertical_bound in ('above', 'below'):
        if vertical_bound == 'above' and position[1] < y_limit:
            return result
        elif vertical_bound == 'below' and position[1] > y_limit:
            return result

    font = _load_font(font_family, font_sz)

    # --- Normalize color & alpha ---
    alpha_from_param = _normalize_opacity(opacity)
    fill = _to_rgba(text_color, fallback_alpha=alpha_from_param)

    base_rgba = result.convert("RGBA")
    overlay = PILImage.new("RGBA", base_rgba.size, (0, 0, 0, 0))

    draw_overlay = ImageDraw.Draw(overlay)

    req_x, req_y = int(position[0]), int(position[1])

    # Measure advance width (for kerning/tracking) & box height
    native_adv = _text_length(font, draw_overlay, text)
    extra_tracking = max(0, len(text) - 1) * float(kerning or 0.0)
    text_w = int(round(native_adv + extra_tracking))
    ascent, descent = font.getmetrics()
    text_h = ascent + descent  # consistent with baseline math

    # X alignment
    if alignment.lower() == 'right':
        x_pos = req_x - text_w
    else:
        x_pos = req_x

    # Baseline alignment (baseline at req_y)
    y_pos = int(req_y - ascent)  # top-left of text box

    # ---------- gradient or solid ----------
    if gradient_colors and len(gradient_colors) >= 2:
        # 1) Build a text mask (L) exactly sized to the text box
        mask = PILImage.new("L", (max(1, text_w), max(1, text_h)), 0)
        mask_draw = ImageDraw.Draw(mask)
        # draw at (0,0); baseline occurs at y=ascent
        _draw_text_with_tracking(mask_draw, (0, 0), text, font, 255, tracking=float(kerning or 0.0))

        # 2) Build the gradient tile matching the text box
        #    Use the same alpha as `opacity`
        grad_rgba_colors = [ _to_rgba(c, fallback_alpha=alpha_from_param) for c in gradient_colors ]
        gradient = _make_linear_gradient((mask.width, mask.height),
                                         grad_rgba_colors,
                                         stops=gradient_stops,
                                         direction=gradient_direction)

        # 3) Paste the gradient into overlay using the text mask
        overlay.paste(gradient, (x_pos, y_pos), mask)

    else:
        # Solid fill path (original behavior, respects opacity)
        _draw_text_with_tracking(draw_overlay, (x_pos, y_pos), text, font, fill, tracking=float(kerning or 0.0))

    # Composite overlay onto base
    out = base_rgba.copy()
    out.alpha_composite(overlay)
    # Return in original mode if it wasn't RGBA
    return out.convert(base_image.mode) if base_image.mode != "RGBA" else out