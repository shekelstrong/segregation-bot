from PIL import Image, ImageDraw, ImageFont

from _pillow.wrap_utils import fix_punctuation_wrap


def add_text_top_left(img, text, box_coords, font_size,
                      text_color, background_color, line_spacing,
                      kerning, font_path, orientation, padding,
                      bubble_alignment="left",  # <--- NEW PARAMETER
                      rotation=0, border_radius=0, vertical_offset=0, line_height_factor=1.2,
                      ):
    draw = ImageDraw.Draw(img)

    # --- 1. Parse Padding ---
    if isinstance(padding, int):
        pad_l = pad_t = pad_r = pad_b = padding
    elif isinstance(padding, (tuple, list)) and len(padding) == 4:
        pad_l, pad_t, pad_r, pad_b = padding
    elif isinstance(padding, (tuple, list)) and len(padding) == 2:
        pad_l = pad_r = padding[0]
        pad_t = pad_b = padding[1]
    else:
        pad_l = pad_t = pad_r = pad_b = 0

    # --- 2. Parse Coordinates ---
    # box_coords = (span_start_x, span_start_y, span_end_x)
    span_x1, span_y1, span_x2 = box_coords

    # Calculate maximum width available for text content inside the span
    max_span_width = span_x2 - span_x1
    max_text_width = max_span_width - (pad_l + pad_r)

    # --- 3. Load Font ---
    try:
        font = ImageFont.truetype(font_path, font_size)
    except (IOError, TypeError):
        font = ImageFont.load_default()

    # Helper: Get exact width of a string (including kerning)
    def get_line_width(s):
        if not s: return 0
        try:
            w = draw.textlength(s, font=font)
        except AttributeError:
            bbox = draw.textbbox((0, 0), s, font=font)
            w = bbox[2] - bbox[0]
        # Add manual kerning
        if len(s) > 1:
            w += (len(s) - 1) * kerning
        return w

    # --- 4. Text Wrapping & Metrics ---
    # We wrap text to ensure it fits within max_text_width
    raw_lines = text.split('\n') if text else []
    final_lines = []

    for raw_line in raw_lines:
        words = raw_line.split()
        if not words:
            final_lines.append("")
            continue

        current_line = []
        for word in words:
            # Check width of current_line + word
            test_line = current_line + [word]
            if get_line_width(" ".join(test_line)) <= max_text_width:
                current_line.append(word)
            else:
                if current_line:
                    final_lines.append(" ".join(current_line))
                    current_line = [word]
                else:
                    # Word is wider than the whole box, force split
                    final_lines.append(word)
        if current_line:
            final_lines.append(" ".join(current_line))

    final_lines = fix_punctuation_wrap(final_lines)

    if not final_lines and text:
        final_lines = [text]
    elif not final_lines:
        final_lines = [""]

    # --- 5. Calculate Bubble Geometry ---
    # Find the longest line to determine the actual bubble width
    widest_line_width = 0
    for line in final_lines:
        w = get_line_width(line)
        if w > widest_line_width:
            widest_line_width = w

    # Calculate Bubble Dimensions
    bubble_content_width = widest_line_width
    bubble_total_width = bubble_content_width + pad_l + pad_r

    ascent, descent = font.getmetrics()
    base_line_height = ascent + descent
    text_block_height = (len(final_lines) * base_line_height * line_height_factor) + \
                        (max(0, len(final_lines) - 1) * line_spacing)

    bubble_total_height = text_block_height + pad_t + pad_b

    # --- 6. Apply Bubble Alignment ---
    # Position the bubble within the (span_x1, span_x2) range

    if bubble_alignment == "center":
        # Center the bubble in the span
        bg_left = span_x1 + (max_span_width - bubble_total_width) / 2
    elif bubble_alignment == "right":
        # Align bubble to the right edge of span
        bg_left = span_x2 - bubble_total_width
    else:
        # Default "left": Align bubble to left edge of span
        bg_left = span_x1

    bg_top = span_y1 + vertical_offset
    bg_right = bg_left + bubble_total_width
    bg_bottom = bg_top + bubble_total_height

    # --- 7. Draw Background ---
    if background_color:
        draw.rounded_rectangle(
            (bg_left, bg_top, bg_right, bg_bottom),
            fill=background_color,
            radius=border_radius
        )

    # --- 8. Draw Text ---
    current_y = bg_top + pad_t

    for line in final_lines:
        line_w = get_line_width(line)

        # Handle TEXT alignment (inside the bubble)
        if orientation == "center":
            # Center text relative to the bubble content area
            line_start_x = bg_left + pad_l + (bubble_content_width - line_w) / 2
        elif orientation == "right":
            # Right align text relative to bubble content area
            line_start_x = bg_right - pad_r - line_w
        else:
            # Left align text
            line_start_x = bg_left + pad_l

        # Draw characters
        current_x = line_start_x
        for char in line:
            draw.text((current_x, current_y), char, font=font, fill=text_color)

            # Advance cursor (char width + kerning)
            try:
                cw = draw.textlength(char, font=font)
            except AttributeError:
                cb = draw.textbbox((0, 0), char, font=font)
                cw = cb[2] - cb[0]
            current_x += cw + kerning

        current_y += (base_line_height * line_height_factor) + line_spacing

    # --- Rotation ---
    if rotation != 0:
        img = img.rotate(rotation, resample=Image.BICUBIC, expand=1)

    return ((bg_left, bg_top), (bg_right, bg_top), (bg_right, bg_bottom), (bg_left, bg_bottom)), img