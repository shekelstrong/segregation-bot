"""
router.py — Telegram-handler для режима segregation_video.

Точка входа: ``setup_router()`` возвращает готовый ``aiogram.Router`` с обработчиками:

  • ``/start``            — приветствие и показ клавиатуры
  • Кнопка «▶ Сегрегация видео» (callback ``segregation``) — запуск FSM-сценария
  • Текст в состоянии ``waiting_for_data`` — разбор двух строк + рендер
  • Кнопка «❌ Отмена» (callback ``segregation_cancel``) — отмена
  • ``/cancel``           — отмена текущего сценария

Рендер выполняется в отдельном потоке через ``asyncio.to_thread()``,
чтобы не блокировать event loop. При любой ошибке временный файл удаляется,
FFmpeg-процесс завершается, FSM-состояние очищается.
"""

from __future__ import annotations

import asyncio
import logging
import traceback
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from .handler import BUTTON_KEY
from .messages import (
    INPUT_INSTRUCTION,
    MSG_ALREADY_RUNNING,
    MSG_CANCELLED,
    MSG_NOTHING_TO_CANCEL,
    MSG_RENDERING,
    MSG_START_HELLO,
    MSG_TECHNICAL_ERROR,
    build_success_caption,
)
from .parse_input import UserInputError, format_number_for_display, parse_user_message
from .service import render_to_tempfile, safe_delete

logger = logging.getLogger(__name__)


class SegregationStates(StatesGroup):
    """FSM-состояния сценария segregation_video."""

    waiting_for_data = State()


def build_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с одной кнопкой запуска режима."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="▶ Сегрегация видео",
                    callback_data=BUTTON_KEY,
                )
            ]
        ]
    )


def build_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой отмены (пока пользователь вводит данные)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="segregation_cancel",
                )
            ]
        ]
    )


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


async def cmd_start(message: Message, state: FSMContext) -> None:
    """/start — приветствие и показ клавиатуры."""
    await state.clear()
    await message.answer(MSG_START_HELLO, reply_markup=build_keyboard())


async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """/cancel — отмена текущего FSM-сценария."""
    current = await state.get_state()
    if current is None:
        await message.answer(MSG_NOTHING_TO_CANCEL, reply_markup=build_keyboard())
        return
    await state.clear()
    await message.answer(MSG_CANCELLED, reply_markup=build_keyboard())


async def on_button_press(callback: CallbackQuery, state: FSMContext) -> None:
    """Нажатие кнопки запуска режима."""
    if callback.data != BUTTON_KEY:
        return
    current = await state.get_state()
    if current == SegregationStates.waiting_for_data.state:
        await callback.message.edit_text(  # type: ignore[union-attr]
            MSG_ALREADY_RUNNING, reply_markup=build_cancel_keyboard()
        )
        await callback.answer()
        return

    await state.set_state(SegregationStates.waiting_for_data)
    if callback.message:
        await callback.message.edit_text(  # type: ignore[union-attr]
            INPUT_INSTRUCTION, reply_markup=build_cancel_keyboard()
        )
    await callback.answer()


async def on_cancel_button(callback: CallbackQuery, state: FSMContext) -> None:
    """Нажатие кнопки «Отмена» во время сценария."""
    if callback.data != "segregation_cancel":
        return
    await state.clear()
    if callback.message:
        await callback.message.edit_text(  # type: ignore[union-attr]
            MSG_CANCELLED, reply_markup=build_keyboard()
        )
    await callback.answer()


async def on_text_message(message: Message, state: FSMContext) -> None:
    """Обработка текстового сообщения в состоянии waiting_for_data."""
    current = await state.get_state()
    if current != SegregationStates.waiting_for_data.state:
        # Не в сценарии — игнорируем
        return

    if not message.text:
        await message.answer(
            "⚠️ Пришли, пожалуйста, текстовое сообщение из двух непустых строк.",
            reply_markup=build_cancel_keyboard(),
        )
        return

    # Разбор и валидация
    try:
        user_data = parse_user_message(message.text)
    except UserInputError as exc:
        logger.info("User input rejected: %s", exc)
        await message.answer(
            f"⚠️ {exc}\n\nПопробуй ещё раз:",
            reply_markup=build_cancel_keyboard(),
        )
        return

    # Сообщаем о начале обработки и сразу очищаем FSM, чтобы при ошибке
    # состояние уже было чистое.
    await message.answer(MSG_RENDERING)
    await state.clear()

    # Рендер в отдельном потоке — не блокируем event loop.
    out_path: Path | None = None
    try:
        out_path = await asyncio.to_thread(render_to_tempfile, user_data)
        await message.answer_video(
            video=FSInputFile(str(out_path), filename="segregation.mp4"),
            caption=build_success_caption(
                user_data.name,
                format_number_for_display(user_data.number),
            ),
            reply_markup=build_keyboard(),
        )
    except Exception as exc:
        logger.error(
            "Render/send failed: %s\n%s", exc, traceback.format_exc()
        )
        await message.answer(
            MSG_TECHNICAL_ERROR, reply_markup=build_keyboard()
        )
    finally:
        safe_delete(out_path)


def setup_router() -> Router:
    """Собрать Router со всеми обработчиками."""
    router = Router()

    router.message.register(cmd_start, Command(commands=["start"]))
    router.message.register(cmd_cancel, Command(commands=["cancel"]))

    # Нажатие кнопки запуска режима
    router.callback_query.register(on_button_press, F.data == BUTTON_KEY)
    # Нажатие кнопки отмены
    router.callback_query.register(on_cancel_button, F.data == "segregation_cancel")

    # Текстовое сообщение в состоянии waiting_for_data
    router.message.register(on_text_message, SegregationStates.waiting_for_data)

    return router


__all__ = [
    "SegregationStates",
    "build_keyboard",
    "build_cancel_keyboard",
    "setup_router",
    "cmd_start",
    "cmd_cancel",
    "on_button_press",
    "on_cancel_button",
    "on_text_message",
]