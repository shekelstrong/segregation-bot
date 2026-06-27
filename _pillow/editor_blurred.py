"""
Draw text with outline and blur effect on PIL Image
Based on editor_blurred.py Wand implementation
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter


def execute(
    base_image,
    font_sz,
    text,
    position,
    alignment='left',
    font_family=None,
    text_color=(55, 55, 55),
    kerning=1.0,
    blur_strength=0.0,
    outline_color=(100, 100, 100),
    outline_width=20
):
    """
    Draw text with outline and blur effect on PIL Image

    Parameters:
    -----------
    base_image : PIL.Image
        Input image object
    font_sz : int
        Font size in pixels
    text : str
        Text to draw
    position : tuple
        (x, y) coordinates for text position
    alignment : str
        Text alignment: 'left', 'center', or 'right' (default: 'left')
    font_family : str
        Path to TTF font file
    text_color : tuple
        RGB color for text fill (default: (55, 55, 55))
    kerning : float
        Letter spacing (kept for compatibility, not implemented in PIL)
    blur_strength : float
        Gaussian blur radius (0 = no blur)
    outline_color : tuple
        RGB color for text outline (default: (100, 100, 100))
    outline_width : int
        Outline/stroke width in pixels (default: 20)

    Returns:
    --------
    PIL.Image
        Image with text overlay
    """
    # Skip if position is (0, 0)
    if position[0] == 0 and position[1] == 0:
        return base_image

    # Load font
    try:
        font = ImageFont.truetype(font_family, font_sz)
    except Exception:
        font = ImageFont.load_default()

    # Create transparent overlay for text
    overlay = Image.new('RGBA', base_image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Calculate text position based on alignment
    x, y = position
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]

    if alignment.lower() == 'right':
        x = position[0] - text_width
    elif alignment.lower() == 'center':
        x = position[0] - (text_width // 2)

    # Draw text with outline and fill
    # In Wand: outline first (stroke), then fill on top
    # In PIL: both drawn together with stroke_width parameter
    draw.text(
        (x, y),
        text,
        font=font,
        fill=text_color + (255,),  # Add alpha channel
        stroke_width=outline_width,
        stroke_fill=outline_color + (255,)  # Add alpha channel
    )

    # Apply blur to text overlay if needed
    if blur_strength > 0:
        overlay = overlay.filter(ImageFilter.GaussianBlur(radius=blur_strength))

    # Convert base image to RGBA if needed
    if base_image.mode != 'RGBA':
        base_image = base_image.convert('RGBA')

    # Composite text overlay onto base image
    result = Image.alpha_composite(base_image, overlay)

    # Convert back to RGB if original was RGB
    if base_image.mode == 'RGB':
        result = result.convert('RGB')

    return result
