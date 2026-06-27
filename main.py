#!/usr/bin/env python3
"""
main.py — точка входа Telegram-бота segregation_video.

Запуск:
    export TELEGRAM_BOT_TOKEN=...     # токен от @BotFather
    export BUILDO_BOT_TOKEN=...       # альтернативное имя
    python -B main.py

Или через Docker / systemd — см. README раздел 17.

Требования:
    Python 3.10+
    ffmpeg с libx264 в PATH
    requirements.txt: aiogram==3.17.0, pillow==11.1.0
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Позволяет запускать main.py и из корня, и из segregation_video/.
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Гарантируем, что _util тоже доступен (он в той же папке, что и main.py).
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from segregation_video.router import setup_router  # noqa: E402


def _setup_logging() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    # aiogram шумит — оставим WARNING
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)


async def main() -> None:
    _setup_logging()
    logger = logging.getLogger("main")

    token = (
        os.environ.get("BUILDO_BOT_TOKEN")
        or os.environ.get("TELEGRAM_BOT_TOKEN")
    )
    if not token:
        logger.error(
            "Не задан токен бота. Установите BUILDO_BOT_TOKEN или "
            "TELEGRAM_BOT_TOKEN в переменных окружения."
        )
        sys.exit(1)

    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(setup_router())

    logger.info("Starting segregation_video bot…")
    try:
        await dp.start_polling(
            bot, allowed_updates=["message", "callback_query"]
        )
    finally:
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped by user.")