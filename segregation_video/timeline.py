"""
timeline.py — общая сборка последовательности кадров итогового видео.

Последовательность (см. README раздел 8 + эталон resulting.mp4):

  1. Статичное состояние синей Mastercard.
  2. Самостоятельно реализованный свайп синей → розовой.
  3. Статичное состояние розовой Visa.
  4. Предоставленное появление экрана транзакции справа.
  5. Статичное состояние экрана транзакции.
  6. Предоставленный подъём блока деталей снизу.
  7. Статичное состояние экрана деталей.

Все кадры возвращаются как frame-like объекты с интерфейсом
``frame.size`` и ``frame.convert(mode).tobytes()`` — это позволяет
передавать их в ``iter_encode_visually_lossless_from_pil``, не загружая
сотни полноразмерных изображений в память одновременно.

Для статичных участков используется ``_StaticView`` — обёртка с общим
RGB-буфером (≈ 8.6 MiB), которая выдаёт «свежий» frame-like объект
для каждого повтора, не копируя пиксели.
"""

from __future__ import annotations

from typing import Iterator

from PIL import Image as PILImage

from . import screens
from .animations import (
    generate_details_slide_frames,
    generate_transaction_slide_frames,
)
from .constants import (
    BLUE_STATIC_FRAMES,
    DETAILS_SCALED_HEIGHT,
    DETAILS_SLIDE_FRAMES,
    DETAILS_STATIC_FRAMES,
    PINK_STATIC_FRAMES,
    SWIPE_FRAMES,
    TRANSACTION_SLIDE_FRAMES,
    TRANSACTION_STATIC_FRAMES,
)
from .parse_input import ParsedUserData
from .swipe import generate_card_swipe_frames


class _StaticView:
    """Memory-cheap stand-in для PIL.Image для повторяющихся статичных кадров.

    ``iter_encode_visually_lossless_from_pil`` нуждается только в:
      * ``frame.size``
      * ``frame.convert(mode).tobytes()``

    Храня RGB-байты один раз, экономим ~8.6 MiB × N повторов.
    """

    __slots__ = ("_size", "_raw_bytes")

    def __init__(self, image: PILImage.Image):
        rgb = image.convert("RGB")
        self._size = rgb.size
        self._raw_bytes = rgb.tobytes()
        rgb.close()

    @property
    def size(self) -> tuple[int, int]:
        return self._size

    def close(self) -> None:
        return None  # shared bytes buffer — nothing to release

    def convert(self, mode: str):
        if mode != "RGB":
            raise NotImplementedError(
                "_StaticView only supports .convert('RGB')"
            )

        class _RGBView:
            __slots__ = ("_buf", "size")

            def __init__(self, buf: bytes, size: tuple[int, int]):
                self._buf = buf
                self.size = size

            def tobytes(self) -> bytes:
                return self._buf

        return _RGBView(self._raw_bytes, self._size)


def _repeat_static(image: PILImage.Image, count: int) -> Iterator[PILImage.Image]:
    """Yield ``image.copy()`` ``count`` раз.

    Используем ``.copy()`` потому, что ``iter_encode_visually_lossless_from_pil``
    проверяет тип кадра через ``isinstance(frame, PILImage.Image)``.
    Пиковое потребление памяти: 2 кадра (исходник + копия) ≈ 17 MB —
    encoder сразу же читает байты и закрывает копию.
    """
    try:
        for _ in range(count):
            yield image.copy()
    finally:
        image.close()


def build_complete_timeline(user: ParsedUserData) -> Iterator:
    """Генератор всех кадров итогового видео.

    Возвращает frame-like объекты с интерфейсом ``.size``/``.convert()``.
    """
    # ---- 1. Статичная синяя Mastercard ----
    blue = screens.build_state_1_blue()
    yield from _repeat_static(blue, BLUE_STATIC_FRAMES)

    # ---- 2. Свайп к розовой ----
    blue_for_swipe = screens.build_state_1_blue()
    pink_for_swipe = screens.build_state_2_pink()
    try:
        yield from generate_card_swipe_frames(
            current_card_screen=blue_for_swipe,
            next_card_screen=pink_for_swipe,
            frame_count=SWIPE_FRAMES,
        )
    finally:
        blue_for_swipe.close()
        pink_for_swipe.close()

    # ---- 3. Статичная розовая Visa ----
    pink = screens.build_state_2_pink()
    yield from _repeat_static(pink, PINK_STATIC_FRAMES)

    # ---- 4. Предоставленное появление транзакции справа ----
    pink_for_slide = screens.build_state_2_pink()
    tx_screen = screens.build_state_3_transaction(user)
    try:
        yield from generate_transaction_slide_frames(
            current_screen=pink_for_slide,
            transaction_screen=tx_screen,
            frame_count=TRANSACTION_SLIDE_FRAMES,
        )
    finally:
        pink_for_slide.close()
        tx_screen.close()

    # ---- 5. Статичный экран транзакции ----
    tx_static = screens.build_state_3_transaction(user)
    yield from _repeat_static(tx_static, TRANSACTION_STATIC_FRAMES)

    # ---- 6. Предоставленный подъём блока деталей снизу ----
    tx_for_slide = screens.build_state_3_transaction(user)
    details_screen = screens.build_state_4_details(user)
    try:
        yield from generate_details_slide_frames(
            transaction_screen=tx_for_slide,
            details_screen=details_screen,
            details_height=DETAILS_SCALED_HEIGHT,
            frame_count=DETAILS_SLIDE_FRAMES,
        )
    finally:
        tx_for_slide.close()
        details_screen.close()

    # ---- 7. Статичный экран деталей ----
    details_static = screens.build_state_4_details(user)
    yield from _repeat_static(details_static, DETAILS_STATIC_FRAMES)


def total_frame_count() -> int:
    """Общее число кадров в итоговом видео."""
    return (
        BLUE_STATIC_FRAMES
        + SWIPE_FRAMES
        + PINK_STATIC_FRAMES
        + TRANSACTION_SLIDE_FRAMES
        + TRANSACTION_STATIC_FRAMES
        + DETAILS_SLIDE_FRAMES
        + DETAILS_STATIC_FRAMES
    )


def expected_duration_seconds(framerate: int = 60) -> float:
    return total_frame_count() / framerate


__all__ = [
    "build_complete_timeline",
    "total_frame_count",
    "expected_duration_seconds",
]