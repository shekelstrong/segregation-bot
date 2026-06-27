"""
screens.py — сборка четырёх визуальных состояний видео.

Каждое состояние возвращает готовый кадр размера (FRAME_WIDTH, FRAME_HEIGHT).
Состояния:

  1. ``build_state_1_blue()``     — фон CARDS_MENU + синяя карта Mastercard.
  2. ``build_state_2_pink()``     — фон CARDS_MENU + розовая карта Visa.
  3. ``build_state_3_transaction(name, number)`` — экран COMMISSION_SCREEN
       с именем получателя, номером и фиксированной комиссией.
  4. ``build_state_4_details(name, number)`` — экран COMMISSION_DETAILS,
       наложенный на транзакцию; внутри — имя и номер получателя плюс
       фиксированные данные отправителя (Luis Diaz / ID / 5951143288544598).

Шрифты:
  - SF Pro недоступен на Ubuntu, используем ``FONT_FALLBACKS_*``
    (DejaVu Sans / Liberation Sans).
  - _pillow.text_draw.execute() используется для одиночных строк
    с уже знакомым API (см. _pillow/text_draw.py).

Все тексты, размеры и операции фиксированы в ``constants.py`` и
соответствуют эталону ``resulting.mp4``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

from .constants import (
    BASE_DIR,
    BLUE_BALANCE,
    BLUE_TX,
    BLUE_TX_DATE,
    CARD_EXPIRY,
    CARDHOLDER_UPPER,
    COMMISSION_AMOUNT,
    DETAILS_SENDER_ID,
    DETAILS_TX_NUMBER,
    FONT_FALLBACKS_BOLD,
    FONT_FALLBACKS_REGULAR,
    FRAME_HEIGHT,
    FRAME_WIDTH,
    PINK_BALANCE,
    PINK_TX,
    PINK_TX_DATE,
    STATUS_BAR_TIME,
    TEMPLATES_DIR,
    TX_LIST_DATE,
)
from .parse_input import ParsedUserData, format_number_for_display

# Пути к PNG-шаблонам
_CARDS_MENU = TEMPLATES_DIR / "COP" / "CARDS_MENU.png"
_BLUE_CARD = TEMPLATES_DIR / "COP" / "MASTERCARD_BLUE_card_half.png"
_BLUE_DATA = TEMPLATES_DIR / "COP" / "MASTERCARD_BLUE_data_half.png"
_PINK_CARD = TEMPLATES_DIR / "COP" / "VISA_PINK_card_half.png"
_PINK_DATA = TEMPLATES_DIR / "COP" / "VISA_PINK_data_half.png"
_TX_SCREEN = TEMPLATES_DIR / "COP" / "COMMISSION_SCREEN.png"
_TX_DETAILS = TEMPLATES_DIR / "COP" / "COMMISSION_DETAILS.png"
_HF_1 = TEMPLATES_DIR / "COP" / "SEGREGATION_HEADER_FOOTER_1.png"  # карточные
_HF_2 = TEMPLATES_DIR / "COP" / "SEGREGATION_HEADER_FOOTER_2.png"  # транзакция + детали

# ---------------------------------------------------------------------------
# Утилиты для шрифтов и композинга
# ---------------------------------------------------------------------------


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Загрузить первый доступный fallback-шрифт заданного размера."""
    candidates = FONT_FALLBACKS_BOLD if bold else FONT_FALLBACKS_REGULAR
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _open_rgb(path: Path) -> Image.Image:
    return Image.open(path).convert("RGB")


def _open_rgba(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def _scale_to_frame(image: Image.Image) -> Image.Image:
    """Привести изображение к размеру ``(FRAME_WIDTH, FRAME_HEIGHT)``."""
    if image.size == (FRAME_WIDTH, FRAME_HEIGHT):
        return image.copy()
    return image.resize(
        (FRAME_WIDTH, FRAME_HEIGHT), Image.Resampling.LANCZOS
    )


def _scale_to_width_keep_ar(
    image: Image.Image, target_w: int
) -> Image.Image:
    """Масштабировать по ширине ``target_w`` с сохранением AR."""
    if image.width == target_w:
        return image.copy()
    ratio = target_w / image.width
    return image.resize(
        (target_w, max(1, int(round(image.height * ratio)))),
        Image.Resampling.LANCZOS,
    )


def _overlay(image: Image.Image, overlay_rgba: Image.Image) -> Image.Image:
    """Alpha-composite ``overlay_rgba`` поверх ``image`` (после конвертации)."""
    if overlay_rgba.size != image.size:
        overlay_rgba = overlay_rgba.resize(
            image.size, Image.Resampling.LANCZOS
        )
    out = image.convert("RGBA")
    out.alpha_composite(overlay_rgba)
    final = out.convert("RGB")
    out.close()
    return final


# ---------------------------------------------------------------------------
# Карточный экран (Tarjeta + Transacciones)
#
# В эталоне карты занимают ~35% ширины и располагаются в верхней части
# над белой панелью Transacciones. Под картой виден индикатор пагинации
# (2 точки), который встроен в шаблон ``CARDS_MENU.png``.
# ---------------------------------------------------------------------------


def _compose_card_screen(
    menu_template: Path,
    card_half: Path,
    data_half: Path,
    balance: str,
    transactions: Iterable[tuple[str, str, str]],
    transactions_date: Iterable[tuple[str, str, str]],
) -> Image.Image:
    """Собрать один экран «Tarjeta + Transacciones».

    ``transactions`` — список из кортежей ``(subtitle, amount, direction)``
    для блока «Hoy». ``transactions_date`` — то же для блока «21 marzo».

    Геометрия (по анализу PNG-шаблонов, см. PROJECT_STRUCTURE.md раздел 6):

      • CARDS_MENU.png — 1500×3248, полный фон (Tarjeta + Transacciones)
        уже содержит «Hoy», «21 marzo», «Filtros», иконки-стрелки и
        подписи «Transferencia saliente / entrante».
      • card_half.png  — 1500×3248, **только карта**, y=414..1149.

    ``data_half`` принимается в сигнатуре для совместимости, но НЕ
    используется, т.к. весь список операций уже отрисован в CARDS_MENU.
    Кандидат только добавляет **суммы** справа от каждой строки.
    """
    del data_half  # CARDS_MENU уже содержит весь список операций
    target_w = FRAME_WIDTH
    scale = target_w / 1500  # все шаблоны этой группы имеют 1500-px ширину

    # Меню растягиваем на весь frame (вертикальная склейка Tarjeta+Trans).
    menu = _open_rgba(menu_template).resize(
        (target_w, FRAME_HEIGHT), Image.Resampling.LANCZOS
    )

    # Карта: вырезаем ТОЛЬКО синюю область из card_half.png (Y_orig=414..1149),
    # чтобы не растягивать прозрачные пиксели сверху/снизу. Затем
    # масштабируем по ширине во frame, сохраняя пропорции.
    card_full = _open_rgba(card_half)
    try:
        # В оригинале 1500×3248 синяя карта занимает Y=414..1149.
        card_crop = card_full.crop((0, 414, 1500, 1149))
        # Масштабируем ТОЛЬКО обрезанную область в ширину frame.
        new_card_h = max(1, int(round(card_crop.height * scale)))
        card_scaled = card_crop.resize(
            (target_w, new_card_h), Image.Resampling.LANCZOS
        )

        # Координата y в frame: 414 * scale = 326
        card_y = int(round(414 * scale))

        canvas = menu.copy()
        # Только карта сверху; список операций — встроен в CARDS_MENU.
        canvas.alpha_composite(card_scaled, (0, card_y))
    finally:
        card_full.close()

    drawable = canvas.convert("RGB")
    draw = ImageDraw.Draw(drawable)

    # === Баланс карты (правый верхний угол карты) ===
    # В эталоне баланс ₡5,320.00 — крупный ТОНКИЙ (light) тёмный текст.
    font_balance = _load_font(64, bold=False)
    draw.text(
        (750, 470),
        balance,
        fill=(40, 43, 54),  # тёмно-серый (по пиксельному анализу эталона)
        font=font_balance,
    )

    # === VALID THRU / 03/31 ===
    # В шаблоне MASTERCARD_BLUE_card_half.png метка "VALID THRU" УЖЕ
    # нарисована (Y_orig≈800..900, в frame Y≈630..708).
    # Рисуем ТОЛЬКО дату "03/31" под ней.
    # В эталоне дата — СВЕТЛО-СЕРЫЙ, тонкий.
    font_valid_date = _load_font(40, bold=False)
    draw.text(
        (940, 660),
        CARD_EXPIRY,
        fill=(110, 115, 125),  # светло-серый
        font=font_valid_date,
    )

    # === Имя владельца (нижняя левая часть карты) ===
    # В эталоне "LUIS DIAZ" — СВЕТЛО-СЕРЫЙ, тонкий, в нижней левой части карты.
    font_cardholder = _load_font(28, bold=False)
    draw.text(
        (180, 820),
        CARDHOLDER_UPPER,
        fill=(110, 115, 125),  # светло-серый, едва заметный
        font=font_cardholder,
    )

    # === Суммы транзакций (рисуем поверх уже отрисованных строк CARDS_MENU) ===
    # Y-координаты в frame (по vision-анализу эталона, высота 2556):
    #   первая транзакция «Hoy»   — y≈1530
    #   вторая  транзакция «Hoy»   — y≈1755
    #   первая  транзакция «21 marzo» — y≈2110
    #   вторая  транзакция «21 marzo» — y≈2310
    font_tx_amount = _load_font(56, bold=True)
    tx_y_frame = [1530, 1755, 2110, 2310]
    all_tx = list(transactions) + list(transactions_date)
    for y_frame, (subtitle, amount, direction) in zip(tx_y_frame, all_tx):
        color = (40, 175, 80) if direction == "in" else (20, 20, 20)
        # Отрисовка текста с выравниванием по правому краю (≈ x=1130 в frame)
        bbox = draw.textbbox((0, 0), amount, font=font_tx_amount)
        text_w = bbox[2] - bbox[0]
        draw.text(
            (1100 - text_w, y_frame - 38),
            amount,
            fill=color,
            font=font_tx_amount,
        )

    # === Header / footer (статус-бар + таб-бар) ===
    final = _overlay(drawable, _open_rgba(_HF_1))
    drawable.close()
    return final


def build_state_1_blue() -> Image.Image:
    """Состояние 1: фон CARDS_MENU + синяя карта Mastercard + статичные тексты."""
    return _compose_card_screen(
        menu_template=_CARDS_MENU,
        card_half=_BLUE_CARD,
        data_half=_BLUE_DATA,
        balance=BLUE_BALANCE,
        transactions=BLUE_TX,
        transactions_date=BLUE_TX_DATE,
    )


def build_state_2_pink() -> Image.Image:
    """Состояние 2: фон CARDS_MENU + розовая карта Visa + статичные тексты."""
    return _compose_card_screen(
        menu_template=_CARDS_MENU,
        card_half=_PINK_CARD,
        data_half=_PINK_DATA,
        balance=PINK_BALANCE,
        transactions=PINK_TX,
        transactions_date=PINK_TX_DATE,
    )


# ---------------------------------------------------------------------------
# Экран транзакции (COMMISSION_SCREEN)
#
# Шаблон уже содержит:
#   - тёмно-фиолетовый фон
#   - кнопку «назад» (стрелка)
#   - заголовок "Transacción" / "Número de fondos transferidos"
#   - белую карточку "Enviar dinero a" с круглым + (FAB)
#   - нижнюю белую карточку "El destinatario debe pagar la comisión."
#
# Нужно добавить:
#   - имя получателя (внутри карточки Enviar dinero a, крупно)
#   - номер получателя (там же, мельче серым)
#   - "La comisión es de ₡81,500" (мелким шрифтом в нижней карточке)
# ---------------------------------------------------------------------------


def build_state_3_transaction(user: ParsedUserData) -> Image.Image:
    """Состояние 3: экран транзакции с именем/номером/комиссией."""
    screen = _open_rgb(_TX_SCREEN)
    if screen.size != (FRAME_WIDTH, FRAME_HEIGHT):
        screen = _scale_to_frame(screen)

    drawable = screen.convert("RGBA")
    draw = ImageDraw.Draw(drawable)

    # === Имя получателя (внутри карточки Enviar dinero a) ===
    font_name = _load_font(60, bold=True)
    # Позиция по эталону: под FAB, в верхней половине экрана.
    # x — после иконки +, центрируем имя.
    name_x = 250
    name_y = 920
    draw.text(
        (name_x, name_y),
        user.name,
        fill=(20, 20, 20),
        font=font_name,
    )

    # === Номер получателя (мелким серым под именем) ===
    font_number = _load_font(42, bold=False)
    draw.text(
        (name_x, name_y + 80),
        format_number_for_display(user.number),
        fill=(120, 120, 120),
        font=font_number,
    )

    # === Комиссия: "La comisión es de ₡81,500" ===
    # В нижней карточке, мелким серым под заголовком.
    font_commission = _load_font(40, bold=False)
    draw.text(
        (250, 1320),
        f"La comisión es de {COMMISSION_AMOUNT}",
        fill=(120, 120, 120),
        font=font_commission,
    )

    # === Header / footer (с таб-баром для транзакции) ===
    final = _overlay(drawable.convert("RGB"), _open_rgba(_HF_2))
    drawable.close()
    screen.close()
    return final


# ---------------------------------------------------------------------------
# Экран деталей (COMMISSION_DETAILS накладывается поверх transaction)
#
# В эталоне details_screen содержит белую нижнюю панель с полями:
#   - "El pago está en modo de espera"  (заголовок)
#   - "De:" (отправитель)              — Luis Diaz
#   - "ID: **************"             — маскированный
#   - "Número de transacción: 5951143288544598"
#   - "Cuenta en -"
#   - "Para:" (получатель)             — введённое имя
#   - введённый номер                   — под "Para:"
# ---------------------------------------------------------------------------


def build_state_4_details(user: ParsedUserData) -> Image.Image:
    """Состояние 4: экран деталей с фиксированным отправителем и введёнными данными получателя."""
    # Начинаем с собранного экрана транзакции (то же, что build_state_3_transaction)
    base = build_state_3_transaction(user)
    base_rgba = base.convert("RGBA")

    # Открываем шаблон деталей и масштабируем ТОЛЬКО белую нижнюю панель.
    # В оригинале 1500×2520 белая панель занимает Y=840..2296 (по pixel-анализу).
    # В frame панель должна накладываться начиная с Y=1200 (по анализу эталона:
    # в эталоне "El pago está en modo de espera" находится на Y=1422).
    details_full = _open_rgba(_TX_DETAILS)
    try:
        details_crop = details_full.crop((0, 840, 1500, 2296))
        scale_x = FRAME_WIDTH / 1500
        new_h = max(1, int(round(details_crop.height * scale_x)))
        details_rgba = details_crop.resize(
            (FRAME_WIDTH, new_h), Image.Resampling.LANCZOS
        )

        # В frame: y=1200 — начало панели (выходит на Y=2352)
        details_y = 1200
        canvas = base_rgba.copy()
        canvas.alpha_composite(details_rgba, (0, details_y))
    finally:
        details_full.close()

    drawable = canvas.convert("RGB")
    draw = ImageDraw.Draw(drawable)

    # Поля и значения для экрана деталей. Шаблон COMMISSION_DETAILS уже
    # содержит метки "De:", "Para:", "ID:" + 16 звёздочек, "Número de
    # transacción:", "Cuenta en -" — нам нужно только вписать значения
    # справа от меток, на их фактических Y-координатах в шаблоне.
    font_value = _load_font(56, bold=True)
    font_tx_number = _load_font(48, bold=True)  # чуть мельче — 16-значный номер
    pink = (228, 50, 130)   # magenta/fuchsia как в эталоне
    black = (35, 35, 35)

    # Шаблон COMMISSION_DETAILS.png 1500×2520.
    # Мы обрезали ТОЛЬКО белую панель Y=840..2296 (высота 1456 в оригинале).
    # Затем масштабировали по ширине во frame (scale_x = 1180/1500 = 0.787).
    # В frame панель накладывается с y=591.
    #
    # Все Y-координаты меток в ОБРЕЗАННОМ оригинале:
    #   «De:»                Y_crop = 1283-840 = 443
    #   «ID:»                Y_crop = 1465-840 = 625
    #   «Número de transacción:» Y_crop = 1578-840 = 738
    #   «Para:»              Y_crop = 1809-840 = 969
    #
    # X-координаты меток (как в оригинале, x ≈ 130..160).
    PANEL_Y_ORIG = 840
    PANEL_SCALE = FRAME_WIDTH / 1500
    PANEL_Y_FRAME = 1200

    def _x_after_label(label: str, label_x_orig: int, font_for_value) -> int:
        """Вычислить X в frame, чтобы значение начиналось сразу после метки."""
        label_w = draw.textlength(label, font=font_for_value)
        return int(round((label_x_orig * PANEL_SCALE) + label_w + 20 * PANEL_SCALE))

    def _y_orig_to_frame(y_orig: int) -> int:
        """Y в frame для метки на y_orig в ПОЛНОМ COMMISSION_DETAILS.png."""
        return int(PANEL_Y_FRAME + (y_orig - PANEL_Y_ORIG) * PANEL_SCALE)

    # === De: Luis Diaz (фиксированный отправитель, тёмно-серым жирным) ===
    de_x = _x_after_label("De:", 130, font_value)
    draw.text(
        (de_x, _y_orig_to_frame(1283) - 14),
        "Luis Diaz",
        fill=(35, 35, 35),
        font=font_value,
    )

    # === Número de transacción: 5951143288544598 (фикс. чёрным) ===
    nt_x = _x_after_label("Número de transacción:", 130, font_tx_number)
    draw.text(
        (nt_x, _y_orig_to_frame(1578) - 10),
        DETAILS_TX_NUMBER,
        fill=black,
        font=font_tx_number,
    )

    # «Cuenta en -» оставляем ПУСТЫМ (как в эталоне — это placeholder метка).

    # === Para: <введённое имя> (жирным тёмно-серым) ===
    para_x = _x_after_label("Para:", 130, font_value)
    draw.text(
        (para_x, _y_orig_to_frame(1809) - 14),
        user.name,
        fill=(35, 35, 35),
        font=font_value,
    )

    # === Cuenta: <введённый номер> (отдельной строкой под Para, чёрным) ===
    # Y-координата в оригинале ≈ 1950 (по vision-анализу эталона).
    cuenta_value_y = _y_orig_to_frame(1950) - 10
    draw.text(
        (130, cuenta_value_y),
        f"Cuenta: {user.number}",
        fill=(35, 35, 35),
        font=font_tx_number,
    )

    final = drawable.convert("RGB")
    base_rgba.close()
    details_rgba.close()
    drawable.close()
    canvas.close()
    base.close()
    return final


__all__ = [
    "build_state_1_blue",
    "build_state_2_pink",
    "build_state_3_transaction",
    "build_state_4_details",
]