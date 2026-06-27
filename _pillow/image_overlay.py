from PIL import Image, ImageEnhance

def overlay_image_pillow(
    base_img: Image.Image,
    overlay_img: Image.Image,
    anchor_coords: tuple,
    overlay_height: int = None,
    brightness: int = 100,        # 0–100 (100 = normal)
    opacity: int = 255,           # 0–255 (255 = fully opaque)
    align: str = 'right',         # horizontal: 'right' or 'left'
    vertical_align: str = 'bottom'  # NEW: 'bottom', 'top', or 'center'
) -> Image.Image:
    """
    Overlays overlay_img onto base_img. Both must be PIL Images.

    Args:
        base_img (PIL.Image.Image): The base image.
        overlay_img (PIL.Image.Image): The overlay image.
        anchor_coords (tuple): (x, y) anchor in base image.
            Horizontal meaning depends on `align`:
                - 'right' → x is the overlay's right edge.
                - 'left'  → x is the overlay's left edge.
            Vertical meaning depends on `vertical_align`:
                - 'bottom' → y is the overlay's bottom edge (default).
                - 'top'    → y is the overlay's top edge.
                - 'center' → y is the vertical center of the overlay.
        overlay_height (int | None): Desired overlay height in pixels (width keeps aspect).
                                     If None, uses the overlay's original height.
        brightness (int): 0–100, where 100 = no change.
        opacity (int): 0–255 alpha applied on top of overlay's existing alpha.
        align (str): 'right' or 'left' (horizontal alignment).
        vertical_align (str): 'bottom', 'top', or 'center' (vertical alignment).

    Returns:
        PIL.Image.Image: A new image with the overlay applied.
    """
    # Normalize modes
    base_mode = base_img.mode
    base = base_img.convert("RGBA").copy()
    ov = overlay_img.convert("RGBA").copy()

    # Use original height if overlay_height not given
    if overlay_height is None:
        overlay_height = ov.height

    # --- Resize proportionally by height ---
    aspect = ov.width / ov.height if ov.height else 1.0
    new_w = max(1, int(round(overlay_height * aspect)))
    new_h = max(1, int(overlay_height))
    ov = ov.resize((new_w, new_h), Image.LANCZOS)

    # --- Brightness ---
    factor = max(0.0, brightness / 100.0)
    r, g, b, a = ov.split()
    rgb = Image.merge("RGB", (r, g, b))
    rgb = ImageEnhance.Brightness(rgb).enhance(factor)
    ov = Image.merge("RGBA", (*rgb.split(), a))

    # --- Opacity ---
    if opacity < 255:
        alpha_mul = max(0.0, min(1.0, opacity / 255.0))
        a = ov.getchannel("A").point(lambda px: int(px * alpha_mul))
        ov.putalpha(a)

    # --- Positioning ---
    x, y = anchor_coords

    # Horizontal
    if align == 'right':
        top_left_x = int(x - new_w)
    elif align == 'left':
        top_left_x = int(x)
    else:
        raise ValueError("align must be 'right' or 'left'.")

    # Vertical
    vertical_align = vertical_align.lower()
    if vertical_align == 'bottom':
        top_left_y = int(y - new_h)
    elif vertical_align == 'top':
        top_left_y = int(y)
    elif vertical_align == 'center':
        top_left_y = int(y - new_h / 2)
    else:
        raise ValueError("vertical_align must be 'bottom', 'top', or 'center'.")

    # Paste overlay using alpha mask
    base.paste(ov, (top_left_x, top_left_y), ov)

    # Return in original mode
    return base.convert(base_mode) if base_mode != "RGBA" else base