from collections.abc import Iterator

from PIL import Image

from .constants import (
    DETAILS_SCALED_HEIGHT,
    DETAILS_SLIDE_FRAMES,
    TRANSACTION_SLIDE_FRAMES,
)


def interpolate_positions(
    start: int,
    end: int,
    *,
    frame_count: int,
) -> list[int]:
    """Return linear integer positions including both requested endpoints."""
    if frame_count <= 0:
        raise ValueError("frame_count must be greater than zero")
    if frame_count == 1:
        return [int(start)]

    distance = end - start
    positions = [
        int(round(start + distance * index / (frame_count - 1)))
        for index in range(frame_count)
    ]
    positions[0] = int(start)
    positions[-1] = int(end)
    return positions


def generate_transaction_slide_frames(
    current_screen: Image.Image,
    transaction_screen: Image.Image,
    *,
    frame_count: int = TRANSACTION_SLIDE_FRAMES,
) -> Iterator[Image.Image]:
    """Slide the transaction screen in from the right over the current screen."""
    if current_screen.size != transaction_screen.size:
        raise ValueError("current_screen and transaction_screen must have the same size")

    current_rgba = current_screen.convert("RGBA")
    transaction_rgba = transaction_screen.convert("RGBA")
    positions = interpolate_positions(
        current_rgba.width,
        0,
        frame_count=frame_count,
    )

    try:
        for x_position in positions:
            frame = current_rgba.copy()
            frame.alpha_composite(transaction_rgba, (x_position, 0))
            yield frame
    finally:
        current_rgba.close()
        transaction_rgba.close()


def generate_details_slide_frames(
    transaction_screen: Image.Image,
    details_screen: Image.Image,
    *,
    details_height: int = DETAILS_SCALED_HEIGHT,
    frame_count: int = DETAILS_SLIDE_FRAMES,
) -> Iterator[Image.Image]:
    """Slide a details sheet up from below the transaction screen."""
    if details_height <= 0 or details_height > transaction_screen.height:
        raise ValueError(
            "details_height must be between 1 and the transaction screen height"
        )

    transaction_rgba = transaction_screen.convert("RGBA")
    details_rgba = details_screen.convert("RGBA")
    scale = details_height / details_rgba.height
    scaled_size = (
        max(1, int(round(details_rgba.width * scale))),
        details_height,
    )
    scaled_details = details_rgba.resize(scaled_size, Image.Resampling.LANCZOS)
    final_y = transaction_rgba.height - details_height
    positions = interpolate_positions(
        transaction_rgba.height,
        final_y,
        frame_count=frame_count,
    )

    try:
        for y_position in positions:
            frame = transaction_rgba.copy()
            frame.alpha_composite(scaled_details, (0, y_position))
            yield frame
    finally:
        transaction_rgba.close()
        details_rgba.close()
        scaled_details.close()


__all__ = [
    "generate_details_slide_frames",
    "generate_transaction_slide_frames",
    "interpolate_positions",
]
