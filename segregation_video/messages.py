"""
messages.py — тексты сообщений, которые бот отправляет пользователю.

Заготовка содержит только ``INPUT_INSTRUCTION``. Добавляю сообщения
для неверного ввода, отмены, начала рендера, ошибки и успеха.
"""

INPUT_INSTRUCTION = (
    "Пришли 2 строки:\n"
    "1) Имя клиента\n"
    "2) Номер клиента"
)

# Сообщения, которые бот отправляет сам
MSG_RENDERING = "⏳ Принято! Начинаю рендер видео…"
MSG_CANCELLED = "❌ Сценарий отменён. Можешь начать заново."
MSG_NOTHING_TO_CANCEL = "Нечего отменять."
MSG_TECHNICAL_ERROR = (
    "❌ Произошла техническая ошибка при генерации видео. Попробуй ещё раз."
)
MSG_ALREADY_RUNNING = (
    "⚠️ Сценарий уже запущен. Пришли 2 строки или нажми «Отмена»."
)
MSG_START_HELLO = (
    "👋 Привет! Я умею генерировать короткое видео по двум строкам данных.\n"
    "Нажми кнопку ниже, чтобы запустить сценарий."
)

# Caption под готовым видео
def build_success_caption(name: str, number_display: str) -> str:
    """Caption под итоговым MP4."""
    return (
        "✅ Готово!\n"
        f"Получатель: {name}\n"
        f"Номер: {number_display}\n\n"
        "Можешь запустить новый сценарий."
    )


__all__ = [
    "INPUT_INSTRUCTION",
    "MSG_RENDERING",
    "MSG_CANCELLED",
    "MSG_NOTHING_TO_CANCEL",
    "MSG_TECHNICAL_ERROR",
    "MSG_ALREADY_RUNNING",
    "MSG_START_HELLO",
    "build_success_caption",
]