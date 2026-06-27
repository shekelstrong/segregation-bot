from PIL import Image, ImageDraw, ImageFont
from typing import Tuple, Union

from _pillow.wrap_utils import fix_punctuation_wrap

def add_text_top_left(
    img: Image.Image,
    str_middle: str,
    box_coords: Tuple[int, int, int, int],
    font_size: int,
    text_color: Union[Tuple[int, int, int], Tuple[int, int, int, int]] = (2, 2, 2),
    line_height_factor: float = 1.2,
    line_spacing: float = 0,
    kerning: float = 0.0,  # extra pixels BETWEEN glyphs
    font_path: str = None,
    rotation: float = 0.0,
    align: str = "left",
) -> Image.Image:
    """
    Draw text aligned top-left within a box on a Pillow Image.
    Respects right bound even with positive kerning.
    Returns a new image (non-destructive).
    """
    img = img.convert("RGBA").copy()
    draw = ImageDraw.Draw(img)

    left, top, right, bottom = box_coords
    box_width = max(0, right - left)

    font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()

    # --- helpers --------------------------------------------------------------
    def text_width_with_kerning(s: str) -> float:
        if not s:
            return 0.0
        # FIX: Measure sum of individual characters to match drawing loop exactly
        return sum(draw.textlength(c, font=font) for c in s) + kerning * (len(s) - 1)

    def hard_wrap_word(word: str) -> list[str]:
        """Break a single long word so each chunk fits the box (accounts for kerning)."""
        chunks, cur = [], ""
        for ch in word:
            cand = cur + ch
            if text_width_with_kerning(cand) <= box_width or not cur:
                cur = cand
            else:
                chunks.append(cur)
                cur = ch
        if cur:
            chunks.append(cur)
        return chunks

    def wrap_text_paragraph(text: str) -> list[str]:
        """
        Word-wrap into lines that fit box_width using width that includes kerning.
        Falls back to hard wrapping inside overlong words.
        """
        lines, cur = [], ""
        for word in text.split():
            cand = (cur + " " + word).strip() if cur else word
            if text_width_with_kerning(cand) <= box_width:
                cur = cand
            else:
                if cur:
                    lines.append(cur)
                # word itself may still be too long -> hard wrap it
                long_chunks = hard_wrap_word(word)
                if long_chunks:
                    # first chunk becomes the new current line if room remains
                    cur = long_chunks.pop()
                    # all prior chunks finalize as full lines
                    lines.extend(long_chunks)
                else:
                    cur = ""
        if cur:
            lines.append(cur)
        return lines

    # --- wrap lines with kerning-aware width ----------------------------------
    lines = fix_punctuation_wrap(wrap_text_paragraph(str_middle))
    if not lines:
        return img

    # line height
    bbox = draw.textbbox((0, 0), lines[0], font=font)
    line_height_px = (bbox[3] - bbox[1])
    step_y = int(round(line_height_px * line_height_factor + line_spacing))

    # draw to overlay (so rotation & alpha work well)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    y_cursor = top
    align = align.lower()
    for line in lines:
        if y_cursor > bottom:
            break

        line_width = text_width_with_kerning(line)
        if align == "center":
            x_cursor = float(left + max(0, (box_width - line_width) / 2))
        elif align == "right":
            x_cursor = float(max(left, right - line_width))
        else:
            x_cursor = float(left)
        n = len(line)

        for i, ch in enumerate(line):
            ch_w = odraw.textlength(ch, font=font)

            # FIX: Removed the "if next_right > right: break" check.
            # We trust the wrapper function to have sized the line correctly.

            odraw.text((x_cursor, y_cursor), ch, font=font, fill=text_color)

            # Calculate next position
            extra_gap = kerning if i < n - 1 else 0.0
            x_cursor += ch_w + extra_gap

        y_cursor += step_y

    # rotate around box's top-left corner
    if rotation:
        overlay = overlay.rotate(rotation, resample=Image.BICUBIC, center=(left, top))

    img.alpha_composite(overlay)
    return img
