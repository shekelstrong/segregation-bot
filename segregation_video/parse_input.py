"""
parse_input.py — разбор и валидация пользовательского ввода.

Ожидаемый формат — ровно две непустые строки:
    <имя клиента>
    <номер клиента / счёта>

Допущения по длине и составу символов (выбраны как разумный компромисс):
    NAME_MIN_LEN      = 2     # не считаем валидным однобуквенные имена
    NAME_MAX_LEN      = 60    # самое длинное имя в эталоне + запас
    NUMBER_MIN_LEN    = 4     # слишком короткий номер — мусор
    NUMBER_MAX_LEN    = 20    # самый длинный номер в эталоне = 12 цифр + пробелы
    NAME_PATTERN      = r"^[A-Za-zÀ-ÿА-Яа-яЁё\s\.'\-]+$"
    NUMBER_PATTERN    = r"^[\d\s\-]+$"

Эти значения не пытаются покрыть все юникодные алфавиты — мы делаем
базовую защиту от мусорного ввода, а не нормализацию имён. Если строка
не проходит валидацию, выбрасывается UserInputError с человеко-читаемым
описанием — никаких молчаливых подстановок или обрезаний.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

NAME_MIN_LEN = 2
NAME_MAX_LEN = 60
NUMBER_MIN_LEN = 4
NUMBER_MAX_LEN = 20

# Имя: латиница/кириллица/испанские буквы, пробел, точка, апостроф, дефис
_NAME_RE = re.compile(r"^[A-Za-zÀ-ÿА-Яа-яЁё\s\.'\-]+$")
# Номер: только цифры, пробелы и дефисы (потом нормализуем)
_NUMBER_RE = re.compile(r"^[\d\s\-]+$")


class UserInputError(ValueError):
    """Пользовательский ввод не прошёл валидацию."""


@dataclass(frozen=True)
class ParsedUserData:
    """Результат успешного разбора двух строк."""

    name: str
    number: str

    def __str__(self) -> str:
        return f"{self.name!r} / {self.number!r}"


def _normalize_number(raw: str) -> str:
    """Удаляем пробелы и дефисы из номера; оставляем только цифры."""
    return re.sub(r"[\s\-]+", "", raw)


def parse_user_message(text: str | None) -> ParsedUserData:
    """Разобрать сообщение пользователя в ``ParsedUserData``.

    Поднимает :class:`UserInputError` с понятным описанием проблемы.
    Не пытается «исправить» ввод — отвергает любые сомнительные случаи.
    """
    if text is None:
        raise UserInputError("Пустое сообщение. Пришли, пожалуйста, две строки.")
    if not isinstance(text, str):
        raise UserInputError("Сообщение должно быть текстом.")

    # Разделяем по переводам строки. splitlines() корректно обрабатывает
    # и \n, и \r\n, и \r.
    lines = [ln.strip() for ln in text.splitlines()]

    # Убираем пустые строки по краям (это не «пустая строка посередине»,
    # просто пользователь мог случайно отправить лишний перенос).
    if len(lines) == 0 or all(ln == "" for ln in lines):
        raise UserInputError("Сообщение пустое. Пришли две непустые строки.")

    # Схлопываем серии пустых строк, оставляя структуру «ровно две строки».
    non_empty = [ln for ln in lines if ln != ""]

    if len(non_empty) < 2:
        raise UserInputError(
            "Нужно прислать две непустые строки: имя и номер. "
            f"Сейчас только {len(non_empty)}."
        )
    if len(non_empty) > 2:
        raise UserInputError(
            "Слишком много строк. Нужно ровно две: имя и номер."
        )

    name, number = non_empty

    # ---- Имя ----
    if len(name) < NAME_MIN_LEN:
        raise UserInputError(
            f"Имя слишком короткое ({len(name)} симв.). "
            f"Минимум {NAME_MIN_LEN}."
        )
    if len(name) > NAME_MAX_LEN:
        raise UserInputError(
            f"Имя слишком длинное ({len(name)} симв.). "
            f"Максимум {NAME_MAX_LEN}."
        )
    if not _NAME_RE.match(name):
        raise UserInputError(
            "Имя содержит недопустимые символы. "
            "Допускаются буквы, пробелы, точка, апостроф и дефис."
        )
    # Отклоняем имена, состоящие только из цифр или спецсимволов
    if not re.search(r"[A-Za-zÀ-ÿА-Яа-яЁё]", name):
        raise UserInputError(
            "Имя должно содержать хотя бы одну букву."
        )

    # ---- Номер ----
    # Сначала проверяем по «сырому» виду (с пробелами/дефисами),
    # чтобы отклонить буквы и прочую пунктуацию.
    if len(number) < NUMBER_MIN_LEN:
        raise UserInputError(
            f"Номер слишком короткий ({len(number)} симв.). "
            f"Минимум {NUMBER_MIN_LEN} цифр."
        )
    if len(number) > NUMBER_MAX_LEN:
        raise UserInputError(
            f"Номер слишком длинный ({len(number)} симв.). "
            f"Максимум {NUMBER_MAX_LEN}."
        )
    if not _NUMBER_RE.match(number):
        raise UserInputError(
            "Номер содержит недопустимые символы. "
            "Допускаются только цифры, пробелы и дефисы."
        )

    digits = _normalize_number(number)
    if len(digits) < NUMBER_MIN_LEN:
        raise UserInputError(
            f"В номере слишком мало цифр ({len(digits)}). "
            f"Минимум {NUMBER_MIN_LEN}."
        )

    return ParsedUserData(name=name, number=digits)


def format_number_for_display(raw_digits: str) -> str:
    """Группирует цифры по три справа для отображения: ``170120010184`` → ``170 120 010 184``.

    Если строка содержит не-цифры, они удаляются перед группировкой.
    """
    digits = re.sub(r"\D", "", raw_digits)
    if not digits:
        return ""
    # Группируем по 3 с конца
    groups: list[str] = []
    while len(digits) > 3:
        groups.insert(0, digits[-3:])
        digits = digits[:-3]
    groups.insert(0, digits)
    return " ".join(groups)


__all__ = [
    "ParsedUserData",
    "UserInputError",
    "NAME_MIN_LEN",
    "NAME_MAX_LEN",
    "NUMBER_MIN_LEN",
    "NUMBER_MAX_LEN",
    "parse_user_message",
    "format_number_for_display",
]