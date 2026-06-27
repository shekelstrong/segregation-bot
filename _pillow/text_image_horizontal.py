from typing import Dict, List, Literal, Optional, Sequence, Tuple
from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont

ParamType = Literal["text", "image"]
RGB = Tuple[int, int, int]  # 0–255 each
Point = Tuple[int, int]
Box2D = Tuple[Point, Point]

# -------- helpers (Pillow equivalents for Wand behavior) --------

def _load_font(font_family: str, font_size: float) -> ImageFont.FreeTypeFont:
    """
    Try to load a TTF/OTF font. If the provided path is not supported (e.g., WOFF/WOFF2),
    fall back to Pillow's default bitmap font to avoid crashing.
    """
    try:
        return ImageFont.truetype(font_family, int(round(font_size)))
    except Exception:
        return ImageFont.load_default()

def _measure_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> Tuple[float, float]:
    """
    Measure text width/height similarly to Wand's font metrics.
    Uses textbbox for precise glyph bounds (includes kerning built into the font).
    """
    # textbbox returns (left, top, right, bottom)
    bbox = draw.textbbox((0, 0), text, font=font)
    w = float(bbox[2] - bbox[0])
    h = float(bbox[3] - bbox[1])
    return w, h

def _glyph_advance(draw: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont, ch: str) -> float:
    """
    Best-effort glyph advance width. Prefer font.getlength (Pillow >= 8.0).
    Fallback to draw.textlength.
    """
    if hasattr(font, "getlength"):
        return float(font.getlength(ch))
    return float(draw.textlength(ch, font=font))

def _ensure_rgba(img: PILImage.Image) -> PILImage.Image:
    return img if img.mode == "RGBA" else img.convert("RGBA")

def _apply_image_opacity(img: PILImage.Image, opacity: float) -> PILImage.Image:
    """
    Multiply existing alpha by opacity (0.0–1.0).
    """
    if opacity >= 1.0:
        return img
    img = _ensure_rgba(img)
    r, g, b, a = img.split()
    # Multiply alpha channel
    a = a.point(lambda v: int(v * opacity))
    img.putalpha(a)
    return img

def _draw_text_with_tracking(
    base_rgba: PILImage.Image,
    position: Tuple[float, float],   # (x, baseline_y)  <-- Y is EXACT LINE
    text: str,
    font: ImageFont.FreeTypeFont,
    fill_rgba: Tuple[int, int, int, int],
    tracking: float,
    opacity: float,
) -> None:
    """
    Draw text so that the provided Y is the EXACT BASELINE for all glyphs.
    """
    overlay = PILImage.new("RGBA", base_rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    x, baseline_y = position
    tracking = float(tracking or 0.0)

    # Convert baseline -> top-left drawing Y using font metrics
    ascent, descent = font.getmetrics()  # pixels above/below baseline
    y_top = baseline_y - ascent

    if tracking == 0.0:
        draw.text((int(round(x)), int(round(y_top))), text, font=font, fill=fill_rgba)
    else:
        for ch in text:
            draw.text((int(round(x)), int(round(y_top))), ch, font=font, fill=fill_rgba)
            adv = _glyph_advance(draw, font, ch)
            x += adv + tracking

    if opacity < 1.0:
        overlay = _apply_image_opacity(overlay, opacity)

    base_rgba.alpha_composite(overlay)

# --------------------- main function (Pillow) ---------------------

def execute(
    base_image: PILImage.Image,
    text_params: Sequence[Dict],
    position: Optional[Point] = None,
    alignment: Literal["left", "center", "right"] = "left",
    bounding_box: Optional[Box2D] = None,
    kerning: float = 1.0,
    return_drawn_width: bool = False,
) -> PILImage.Image | tuple[PILImage.Image, float] | None:
    """
    Render a horizontal row of mixed text and images onto a base image.

    The function lays out each element from `text_params` left-to-right, honoring
    per-item `x_offset` / `y_offset`, kerning for text, and (optionally) a
    bounding box to horizontally center the whole row between two x-coordinates.

    Parameters
    ----------
    base_image : PIL.Image.Image
        Base image to draw onto (will not be modified; a copy is returned).
    text_params : Sequence[dict]
        Ordered list of elements to render. Each element must have a `"type"`
        field with value `"text"` or `"image"`.

        Text element fields:
            - type: "text"
            - text: str (required)
            - color: tuple[int,int,int] RGB 0–255 (required)
            - font_size: float | int (required)
            - font_family: str (required; path or font name)
            - x_offset: float | int (optional; default 0)
            - y_offset: float | int (optional; default 0)  # applied to the bottom-aligned Y
            - opacity: int (optional; 0–255, default 255)

        Image element fields (object or path):
            - type: "image"
            - image: PIL.Image.Image (optional; used if provided)
            - image_path: str (optional; used if no `image` given)
            - width: int (optional; if provided with height, image is resized)
            - height: int (optional; if provided with width, image is resized)
            - x_offset: float | int (optional; default 0)
            - y_offset: float | int (optional; default 0)
            - opacity: int (optional; 0–255, default 255)

    position : tuple[int,int] | None, default None
        Absolute (x, y) pixel coordinates to start the row from. Ignored if
        `bounding_box` is provided. If None and no bounding box is supplied,
        defaults to (10, 50). The Y value is treated as the TEXT BOTTOM line.
    alignment : {"left","center","right"}, default "left"
        Horizontal alignment behavior when `position` is used without a
        `bounding_box`. For `"center"` or `"right"`, the function pre-measures
        the content width and shifts the starting x accordingly.
    bounding_box : ((x1,y_line),(x2,y_line)) | None, default None
        Two points defining a horizontal region to center the entire row into.
        The y-coordinate is used as the TEXT BOTTOM reference for the row.
    kerning : float, default 1.0
        Extra per-letter spacing (tracking) applied to all text elements.
    return_drawn_width : bool, default False
        If True, also returns the total rendered row width (icon + text + offsets).

    Returns
    -------
    PIL.Image.Image
        A new image with the rendered row composited on it.
    tuple[PIL.Image.Image, float]
        Returned when `return_drawn_width=True`: (image, rendered_row_width).

    Notes
    -----
    - Opacity is specified per-element as 0–255 (mapped internally to 0.0–1.0).
    - Text vertical positioning is BOTTOM-aligned to the given Y coordinate.
      Use per-element `y_offset` to nudge as needed.
    - If a text element is missing required fields (`text`, `color`,
      `font_size`, or `font_family`), a ValueError is raised.
    - For image elements, at least one of `image` or `image_path` must be provided.
    """
    def _require_image_param(p: Dict) -> None:
        if p.get("type") == "image" and ("image" not in p and "image_path" not in p):
            raise ValueError("Image param requires 'image' (PIL Image) or 'image_path'.")

    # Helper: measure total width of the row for alignment/centering
    def _measure_total_width(params: Sequence[Dict]) -> float:
        total = 0.0
        # Use a tiny dummy overlay to compute text metrics
        dummy = PILImage.new("RGBA", (2, 2), (0, 0, 0, 0))
        d = ImageDraw.Draw(dummy)
        for p in params:
            total += float(p.get("x_offset", 0) or 0)
            if p["type"] == "text":
                # Validate required fields for text
                if any(k not in p for k in ("text", "color", "font_size", "font_family")):
                    raise ValueError("Text param requires 'text', 'color', 'font_size', and 'font_family'.")
                font = _load_font(p["font_family"], float(p["font_size"]))
                w, _ = _measure_text(d, p["text"], font)
                # Add extra tracking between glyphs to emulate Wand's text_kerning
                n = max(0, len(p["text"]) - 1)
                w += float(kerning) * n
                total += float(w)
            elif p["type"] == "image":
                _require_image_param(p)
                w = p.get("width")
                h = p.get("height")
                if w and h:
                    total += float(w)
                else:
                    if "image" in p and p["image"] is not None:
                        total += float(p["image"].width)
                    else:
                        with PILImage.open(p["image_path"]) as im:
                            total += float(im.width)
            else:
                raise ValueError(f"Unknown param type: {p['type']}")
        return total

    # Work on a copy; switch to RGBA when we need transparency-safe ops
    base = base_image.copy()
    result = base if base.mode == "RGBA" else base.convert("RGBA")

    logged_x: List[float] = []

    content_w: float | None = None

    # Decide starting (x, y). Y is the text BOTTOM line for this row.
    if bounding_box:
        (x1, y_line), (x2, _) = bounding_box
        content_w = _measure_total_width(text_params)
        x_pos = x1 + ((x2 - x1 - content_w) / 2.0)
        y_pos = float(y_line)
    else:
        default_pos = (10, 50)
        start_x, start_y = position or default_pos
        if alignment in ("center", "right"):
            content_w = _measure_total_width(text_params)
            if alignment == "center":
                start_x = start_x - content_w / 2.0
            else:  # "right"
                start_x = start_x - content_w
        x_pos = float(start_x)
        y_pos = float(start_y)

    # Track maximum row height if needed (currently unused)
    max_height = 0.0

    # A lightweight draw for measuring text during loop
    measure_canvas = PILImage.new("RGBA", (2, 2), (0, 0, 0, 0))
    measurer = ImageDraw.Draw(measure_canvas)

    for p in text_params:
        x_pos += float(p.get("x_offset", 0) or 0)
        raw_opacity = p.get("opacity", 255)
        # Accept int 0–255 or float 0.0–1.0; normalize to 0.0–1.0
        if isinstance(raw_opacity, (int, float)):
            opacity = float(raw_opacity)
            if opacity > 1.0:
                opacity = opacity / 255.0
        else:
            opacity = 1.0
        opacity = max(0.0, min(1.0, opacity))

        if p["type"] == "text":
            # Validate required fields
            if any(k not in p for k in ("text", "color", "font_size", "font_family")):
                raise ValueError("Text param requires 'text', 'color', 'font_size', and 'font_family'.")

            font = _load_font(p["font_family"], float(p["font_size"]))
            r, g, b = p["color"]
            # Fill is RGBA (alpha 255 used for crisp glyph edge; we apply overall opacity via overlay)
            fill_rgba = (int(r), int(g), int(b), 255)

            # Metrics for width/height (plus tracking like in _measure_total_width)
            text_w, text_h = _measure_text(measurer, p["text"], font)
            n = max(0, len(p["text"]) - 1)
            text_w += float(kerning) * n
            max_height = max(max_height, float(text_h))

            adjusted_y = y_pos + float(p.get("y_offset", 0) or 0)  # bottom-aligned Y

            # Draw text onto result with tracking + opacity via overlay; bottom-aligned via anchor='lb'
            _draw_text_with_tracking(
                base_rgba=result,
                position=(x_pos, adjusted_y),
                text=p["text"],
                font=font,
                fill_rgba=fill_rgba,
                tracking=float(kerning or 0.0),
                opacity=opacity,
            )

            logged_x.append(x_pos)
            x_pos += float(text_w)

        elif p["type"] == "image":
            _require_image_param(p)

            # Obtain an overlay image safely (clone if provided)
            if "image" in p and p["image"] is not None:
                overlay = p["image"].copy()
            else:
                overlay = PILImage.open(p["image_path"])

            try:
                # Resize if specified
                if "width" in p and "height" in p and p["width"] and p["height"]:
                    overlay = overlay.resize((int(p["width"]), int(p["height"])), resample=PILImage.LANCZOS)

                # Ensure RGBA and apply per-image opacity
                overlay = _ensure_rgba(overlay)
                overlay = _apply_image_opacity(overlay, opacity)

                img_w, img_h = float(overlay.width), float(overlay.height)
                max_height = max(max_height, img_h)

                # Keep previous behavior for images: align around the reference line (now defined by text bottom)
                # Center the image vertically on that line unless y_offset changes it.
                adjusted_y = y_pos + float(p.get("y_offset", 0) or 0) - (img_h / 2.0)

                # Composite onto result (which is RGBA) at integer coords
                result.alpha_composite(overlay, (int(round(x_pos)), int(round(adjusted_y))))

                logged_x.append(x_pos)
                x_pos += img_w
            finally:
                try:
                    overlay.close()
                except Exception:
                    pass
        else:
            raise ValueError(f"Unknown param type: {p['type']}")

    # If original base was not RGBA and no transparency was introduced, you could convert back.
    # We keep RGBA to preserve any alpha produced by text/image opacity.
    if return_drawn_width:
        if content_w is None:
            content_w = _measure_total_width(text_params)
        return result, content_w
    return result
