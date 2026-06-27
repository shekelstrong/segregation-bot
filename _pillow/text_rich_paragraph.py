"""
Rich Text Paragraph Drawing Utility
Утиліта для малювання абзаців з підтримкою bold тексту та гнучкими відступами
"""
from typing import Tuple, Literal, List
from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont
import re


from _pillow.wrap_utils import _PUNCTUATION

Point = Tuple[int, int]


class TextSegment:
    """Represents a segment of text with styling"""
    def __init__(self, text: str, is_bold: bool = False):
        self.text = text
        self.is_bold = is_bold


def _load_font(font_family: str, font_sz: float) -> ImageFont.FreeTypeFont:
    """Load TrueType/OpenType font with fallback to default"""
    try:
        return ImageFont.truetype(font_family, int(font_sz))
    except Exception:
        return ImageFont.load_default()


def _parse_text_with_bold(text: str) -> List[TextSegment]:
    """
    Parse text and identify bold segments marked with **text** or <b>text</b>

    Args:
        text: Text with bold markers (e.g., "Normal **bold text** normal" or "Normal <b>bold text</b> normal")

    Returns:
        List of TextSegment objects
    """
    segments = []
    # Split by bold markers (both ** and <b>) but keep the delimiters
    # Match either **text** or <b>text</b>
    parts = re.split(r'(\*\*.*?\*\*|<b>.*?</b>)', text)

    for part in parts:
        if not part:
            continue
        if part.startswith('**') and part.endswith('**'):
            # Remove ** markers and mark as bold
            segments.append(TextSegment(part[2:-2], is_bold=True))
        elif part.startswith('<b>') and part.endswith('</b>'):
            # Remove <b> tags and mark as bold
            segments.append(TextSegment(part[3:-4], is_bold=True))
        else:
            segments.append(TextSegment(part, is_bold=False))

    return segments


def _measure_segment_width(
    segment: TextSegment,
    font_regular: ImageFont.FreeTypeFont,
    font_bold: ImageFont.FreeTypeFont,
    draw: ImageDraw.ImageDraw,
    kerning: float = 0.0,
    space_extra: float = 0.0,
) -> float:
    """Measure the width of a text segment with kerning"""
    # Always use regular font for spaces to maintain consistent spacing
    if segment.text == ' ':
        font = font_regular
    else:
        font = font_bold if segment.is_bold else font_regular

    if hasattr(font, "getlength"):
        base_width = font.getlength(segment.text)
    else:
        bbox = draw.textbbox((0, 0), segment.text, font=font)
        base_width = bbox[2] - bbox[0]

    if segment.text == ' ':
        base_width += space_extra

    # Add kerning
    if len(segment.text) > 1:
        base_width += (len(segment.text) - 1) * kerning

    return base_width


def _wrap_segments_to_lines(
    segments: List[TextSegment],
    font_regular: ImageFont.FreeTypeFont,
    font_bold: ImageFont.FreeTypeFont,
    max_width: int,
    draw: ImageDraw.ImageDraw,
    kerning: float = 0.0,
    space_extra: float = 0.0,
) -> List[List[TextSegment]]:
    """
    Wrap text segments into lines that fit within max_width

    Args:
        segments: List of TextSegment objects
        font_regular: Regular font
        font_bold: Bold font
        max_width: Maximum width in pixels
        draw: ImageDraw object for measuring
        kerning: Extra spacing between characters

    Returns:
        List of lines, where each line is a list of TextSegments
    """
    lines = []
    current_line = []
    current_width = 0

    for segment in segments:
        # Split segment by spaces, but keep track of them
        parts = segment.text.split(' ')

        for i, word in enumerate(parts):
            # Create word segment (even if empty)
            word_seg = TextSegment(word, segment.is_bold) if word else None

            # Add space segment between words (but not before first word)
            # This preserves the original spacing from the text
            if i > 0:
                space_seg = TextSegment(' ', segment.is_bold)
                space_width = _measure_segment_width(
                    space_seg, font_regular, font_bold, draw, kerning, space_extra
                )

                # Check if space fits on current line
                if current_width + space_width <= max_width or not current_line:
                    current_line.append(space_seg)
                    current_width += space_width
                # If space doesn't fit, it will be at the start of next line
                # which we'll skip by not adding it

            # Add word segment if it's not empty
            if word_seg and word_seg.text:
                word_width = _measure_segment_width(
                    word_seg, font_regular, font_bold, draw, kerning, space_extra
                )
                total_width = current_width + word_width

                if total_width <= max_width or not current_line:
                    # Add to current line
                    current_line.append(word_seg)
                    current_width += word_width
                else:
                    # Start new line
                    lines.append(current_line)
                    current_line = [word_seg]
                    current_width = word_width

    # Add last line
    if current_line:
        lines.append(current_line)

    return _fix_punctuation_segments(lines)


def _fix_punctuation_segments(lines: List[List[TextSegment]]) -> List[List[TextSegment]]:
    """Move leading punctuation segments from line start to previous line end."""
    if len(lines) <= 1:
        return lines

    result = [lines[0]]
    for line in lines[1:]:
        if not line or not result:
            result.append(line)
            continue

        # Check first non-space segment for leading punctuation
        first_idx = 0
        while first_idx < len(line) and line[first_idx].text.strip() == '':
            first_idx += 1

        if first_idx >= len(line):
            result.append(line)
            continue

        first_seg = line[first_idx]
        # Count leading punctuation chars in the first real segment
        i = 0
        while i < len(first_seg.text) and first_seg.text[i] in _PUNCTUATION:
            i += 1

        if i > 0:
            punct = first_seg.text[:i]
            rest_text = first_seg.text[i:].lstrip()
            # Append punctuation to last segment of previous line
            last_seg = result[-1][-1]
            last_seg.text = last_seg.text + punct
            # Rebuild remaining segments for current line
            remaining = []
            if rest_text:
                remaining.append(TextSegment(rest_text, first_seg.is_bold))
            remaining.extend(line[first_idx + 1:])
            if remaining:
                result.append(remaining)
        else:
            result.append(line)
    return result


def _draw_segment(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    segment: TextSegment,
    font: ImageFont.FreeTypeFont,
    color: Tuple[int, int, int],
    kerning: float = 0.0,
    space_extra: float = 0.0,
) -> float:
    """
    Draw a text segment and return its width

    Args:
        draw: ImageDraw object
        x: X position
        y: Y position (adjusted for ascent)
        segment: TextSegment to draw
        font: Font to use
        color: Text color
        kerning: Extra spacing between characters

    Returns:
        Width of drawn segment
    """
    if not kerning:
        draw.text((x, y), segment.text, font=font, fill=color)
        if hasattr(font, "getlength"):
            return font.getlength(segment.text)
        else:
            bbox = draw.textbbox((0, 0), segment.text, font=font)
            width = bbox[2] - bbox[0]
            if segment.text == ' ':
                width += space_extra
            return width

    # Draw with kerning
    current_x = x
    for char in segment.text:
        draw.text((current_x, y), char, font=font, fill=color)
        if hasattr(font, "getlength"):
            char_width = font.getlength(char)
        else:
            bbox = draw.textbbox((0, 0), char, font=font)
            char_width = bbox[2] - bbox[0]
        current_x += char_width + kerning

    width = current_x - x
    if segment.text == ' ':
        width += space_extra
    return width


def execute(
    base_image: PILImage.Image,
    text: str,
    position: Point,
    max_width: int,
    font_sz: float = 18,
    font_regular: str = None,
    font_bold: str = None,
    text_color: Tuple[int, int, int] = (55, 55, 55),
    line_spacing: float = 1.2,
    line_spacing_extra: float = 0.0,
    paragraph_spacing: float = 0.0,
    first_line_indent: float = 0.0,
    kerning: float = 0.0,
    space_extra: float = 0.0,
    alignment: Literal['left', 'right', 'center'] = 'left',
) -> Tuple[PILImage.Image, int]:
    """
    Draw rich text paragraph with bold support and flexible spacing

    Args:
        base_image: Base PIL Image to draw on
        text: Text with bold markers (e.g., "Normal **bold text** normal")
              Use \\n for manual line breaks within the paragraph (no extra spacing)
        position: Starting position (x, y) for the paragraph
        max_width: Maximum width in pixels before wrapping
        font_sz: Font size
        font_regular: Path to regular font file
        font_bold: Path to bold font file
        text_color: Text color as RGB tuple
        line_spacing: Line height multiplier (default 1.2) applied before extra pixels
        line_spacing_extra: Extra pixels added to each line height after applying multiplier
        paragraph_spacing: Extra spacing AFTER the entire paragraph in pixels
                          This is NOT applied to \\n breaks within the paragraph
        first_line_indent: Indentation for the very first line only (in pixels)
        kerning: Extra spacing between characters in pixels
        space_extra: Extra spacing (pixels) applied after each space character
        alignment: Text alignment ('left', 'right', 'center')

    Returns:
        Tuple of (Modified PIL Image, next_y_position)
        - Modified PIL Image with paragraph text
        - next_y_position: Y coordinate where next paragraph should start
                          (includes paragraph_spacing)

    Important:
        - \\n creates a simple line break (uses line_spacing only)
        - paragraph_spacing is added ONCE at the end of the entire text
        - first_line_indent only applies to the very first line

    Example:
        >>> result, next_y = execute(
        ...     base_image=img,
        ...     text="La cuenta **3081007551** registrada a nombre de **Eduardo Pérez**",
        ...     position=(100, 200),
        ...     max_width=600,
        ...     font_sz=18,
        ...     first_line_indent=20,
        ... )
        >>> # Draw next paragraph starting from next_y
        >>> result, next_y = execute(
        ...     base_image=result,
        ...     text="Next paragraph text",
        ...     position=(100, next_y),
        ...     max_width=600,
        ... )
    """
    result = base_image.copy()

    # Load fonts
    font_reg = _load_font(font_regular, font_sz)
    font_bld = _load_font(font_bold, font_sz)

    # Convert to RGBA
    base_rgba = result.convert("RGBA")
    overlay = PILImage.new("RGBA", base_rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Get font metrics (use regular font for line height)
    ascent, descent = font_reg.getmetrics()
    line_height = int((ascent + descent) * line_spacing + line_spacing_extra)

    # Split text by manual line breaks (\n) - these are simple line breaks, not paragraph breaks
    manual_lines = text.split('\n')

    # Starting position
    x_pos, y_pos = position

    # Track if this is the first line of the entire text (for first_line_indent)
    is_first_line_overall = True

    # Process each manual line
    for manual_line in manual_lines:
        if not manual_line.strip():
            # Empty line - just add line height (not paragraph spacing)
            y_pos += line_height
            continue

        # Parse bold segments
        segments = _parse_text_with_bold(manual_line.strip())

        # Wrap segments into lines
        wrapped_lines = _wrap_segments_to_lines(
            segments, font_reg, font_bld, max_width, draw, kerning, space_extra
        )

        # Draw each wrapped line
        for line_idx, line_segments in enumerate(wrapped_lines):
            # Calculate line width for alignment
            line_width = sum(
                _measure_segment_width(
                    seg, font_reg, font_bld, draw, kerning, space_extra
                )
                for seg in line_segments
            )

            # Calculate starting x position
            # Only apply first_line_indent to the very first line of the entire text
            if is_first_line_overall and line_idx == 0 and first_line_indent:
                line_x = x_pos + first_line_indent
                available_width = max_width - first_line_indent
            else:
                line_x = x_pos
                available_width = max_width

            # Apply alignment
            if alignment == 'center':
                line_x += (available_width - line_width) // 2
            elif alignment == 'right':
                line_x += available_width - line_width

            # Adjust y position by ascent
            adjusted_y = int(y_pos - ascent)

            # Draw each segment in the line
            current_x = line_x
            for segment in line_segments:
                # Always use regular font for spaces to maintain consistent spacing
                if segment.text == ' ':
                    font = font_reg
                else:
                    font = font_bld if segment.is_bold else font_reg
                segment_width = _draw_segment(
                    draw, current_x, adjusted_y, segment, font, text_color, kerning, space_extra
                )
                current_x += segment_width

            # Move to next line
            y_pos += line_height

            # After first line, set flag to false
            if is_first_line_overall:
                is_first_line_overall = False

    # Composite overlay onto base
    result = result.convert("RGBA")
    result.alpha_composite(overlay)

    # Return the image and the next Y position (including paragraph spacing)
    next_y = int(y_pos + paragraph_spacing)
    return result, next_y


if __name__ == "__main__":
    # Test the rich paragraph utility
    test_img = PILImage.new("RGB", (800, 800), (255, 255, 255))

    test_text = """Test paragraph with **bold text** and regular text.
La Superintendencia ha identificado que la cuenta **3081007551**, registrada a nombre de **Eduardo Isaías Coronado Pérez**, ha recibido fondos por un monto total de **Q32,306.00**.

Second paragraph with more **bold elements** throughout the text."""

    result, next_y = execute(
        base_image=test_img,
        text=test_text,
        position=(50, 50),
        max_width=600,
        font_sz=18,
        font_regular='font/Inter_18pt-Regular.ttf',
        font_bold='font/Inter_18pt-Bold.ttf',
        text_color=(55, 55, 55),
        line_spacing=1.2,
        paragraph_spacing=10,
        first_line_indent=20,
        kerning=0.5,
        alignment='left',
    )

    output_path = "test_rich_paragraph.png"
    result.save(output_path)
    print(f"Test saved to {output_path}")
    print(f"Next Y position: {next_y}")
