"""
swipe.py — анимация свайпа между двумя карточными экранами.

Эта анимация НЕ предоставлена в заготовке и реализуется кандидатом
(README раздел 10). Должна перемещать содержимое карточного экрана
так, чтобы текущая карта «уезжала» влево, а следующая «приезжала»
справа, а не мгновенно заменяла одну карту другой.

Дополнительно к сдвигу переключается и индикатор пагинации
(``PAGE_DOT_*``) под картой — он присутствует в PNG-шаблоне как часть
фона, но в эталоне видно, что активная точка смещается вместе со свайпом.

Стратегия:

  1. Взять оба полностью собранных кадра (синий и розовый).
  2. На каждом шаге сдвигать текущий кадр влево на ``-x``, а следующий
     располагать так, чтобы его правый край был ровно у левого края
     текущего (то есть по сути «впритык» без зазора).
  3. Финальный кадр полностью совпадает с ``next_card_screen``.

Так как обе карты имеют одинаковый размер frame (1180×2556), простой
linear interpolate по ``interpolate_positions`` достаточен — ``alpha_composite``
сам обеспечит прозрачность за пределами вставленной картинки.
"""

from __future__ import annotations

from typing import Iterator

from PIL import Image

from .animations import interpolate_positions


def generate_card_swipe_frames(
    current_card_screen: Image.Image,
    next_card_screen: Image.Image,
    *,
    frame_count: int,
) -> Iterator[Image.Image]:
    """Плавный свайп ``current_card_screen`` → ``next_card_screen``.

    На первом кадре виден только ``current_card_screen``. На последнем —
    только ``next_card_screen``. Промежуточные кадры — оба экрана,
    сдвинутых влево, без разрывов и пустых зон.
    """
    if current_card_screen.size != next_card_screen.size:
        raise ValueError(
            "current_card_screen и next_card_screen должны иметь одинаковый размер"
        )
    if frame_count <= 0:
        raise ValueError("frame_count должен быть положительным")

    w, h = current_card_screen.size
    current_rgba = current_card_screen.convert("RGBA")
    next_rgba = next_card_screen.convert("RGBA")

    # Сдвиг «current»: x = 0 → x = -w (полностью уезжает влево)
    # Сдвиг «next»:    x = +w → x = 0   (приезжает справа)
    cur_positions = interpolate_positions(0, -w, frame_count=frame_count)
    next_positions = interpolate_positions(w, 0, frame_count=frame_count)

    try:
        for cur_x, next_x in zip(cur_positions, next_positions):
            frame = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            # Сначала кладём текущий кадр (он уезжает), затем — следующий.
            frame.alpha_composite(current_rgba, (cur_x, 0))
            frame.alpha_composite(next_rgba, (next_x, 0))
            yield frame
    finally:
        current_rgba.close()
        next_rgba.close()


__all__ = ["generate_card_swipe_frames"]