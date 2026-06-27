"""
service.py — рендер итогового видео в уникальный временный файл.

Использует ``_util.video.render_video_from_frames.iter_encode_visually_lossless_from_pil``
для потокового кодирования через ffmpeg stdin pipe — без промежуточных
PNG-файлов на диске.

Каждый запрос получает свой путь (UUID), чтобы параллельные пользователи
не перезаписывали один и тот же файл. При ошибке временный файл удаляется,
процесс ffmpeg принудительно завершается.
"""

from __future__ import annotations

import logging
import tempfile
import uuid
from pathlib import Path

from _util.video.render_video_from_frames import (
    iter_encode_visually_lossless_from_pil,
)

from .constants import CRF, FRAMERATE, PRESET
from .parse_input import ParsedUserData
from .timeline import build_complete_timeline

logger = logging.getLogger(__name__)


def render_to_tempfile(user: ParsedUserData) -> Path:
    """Отрисовать итоговое видео в уникальный временный файл.

    Возвращает путь к готовому MP4. При ошибке временный файл удаляется,
    ffmpeg завершается, исключение пробрасывается дальше.
    """
    work_dir = Path(tempfile.gettempdir()) / "segregation_video"
    work_dir.mkdir(parents=True, exist_ok=True)
    out_path = work_dir / f"result_{uuid.uuid4().hex}.mp4"

    logger.info(
        "Rendering segregation video for user=%r to %s", user, out_path
    )

    try:
        iter_encode_visually_lossless_from_pil(
            frames=build_complete_timeline(user),
            output_file=str(out_path),
            framerate=FRAMERATE,
            crf=CRF,
            preset=PRESET,
        )
    except Exception:
        logger.exception("Render failed")
        if out_path.exists():
            try:
                out_path.unlink()
            except OSError:
                logger.warning("Failed to remove temp file %s", out_path)
        raise

    if not out_path.exists():
        raise RuntimeError(
            f"Render finished but output file is missing: {out_path}"
        )

    size_kb = out_path.stat().st_size / 1024
    logger.info("Render finished: %s (%.1f KB)", out_path, size_kb)
    return out_path


def safe_delete(path: Path | str | None) -> None:
    """Удалить файл, проглотив любые ошибки."""
    if path is None:
        return
    try:
        p = Path(path)
        if p.exists():
            p.unlink()
            logger.debug("Deleted temp file %s", p)
    except OSError:
        logger.warning("Failed to delete temp file %s", path, exc_info=True)


__all__ = ["render_to_tempfile", "safe_delete"]