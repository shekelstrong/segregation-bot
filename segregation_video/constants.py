from pathlib import Path

# ---------------------------------------------------------------------------
# Frame / video
# ---------------------------------------------------------------------------
FRAME_WIDTH = 1180
FRAME_HEIGHT = 2556
FRAMERATE = 60
CRF = 12
PRESET = "fast"
BRIGHTNESS = 100

# Provided animation phases
TRANSACTION_SLIDE_FRAMES = 15
DETAILS_SLIDE_FRAMES = 20
DETAILS_SCALED_HEIGHT = 1982

# ---------------------------------------------------------------------------
# Static-frame counts (см. README раздел 8 + эталон resulting.mp4)
#
# Распределение по 605 кадрам @ 60fps ≈ 10.08 с:
#   • синяя Mastercard статика     ~150 кадров (~2.50 с)
#   • свайп к розовой              ~12  кадров (~0.20 с)
#   • розовая Visa статика        ~157 кадров (~2.62 с)
#   • транзакция slide-in           15  кадров (0.25 с)  ← из constants
#   • транзакция статика          ~111 кадров (~1.85 с)
#   • детали slide-up               20  кадров (~0.33 с) ← из constants
#   • детали статика               ~140 кадров (~2.33 с)
# Итого ≈ 605.
# ---------------------------------------------------------------------------
BLUE_STATIC_FRAMES = 156
SWIPE_FRAMES = 12
PINK_STATIC_FRAMES = 151
TRANSACTION_STATIC_FRAMES = 111
DETAILS_STATIC_FRAMES = 140

# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
FONT_DIR = BASE_DIR / "fonts"

# ---------------------------------------------------------------------------
# Fonts
#
# SF Pro недоступен на Ubuntu. README 6.4 явно запрещает на него
# рассчитывать. Используем системные fallback'ы (DejaVu Sans /
# Liberation Sans) — визуально близки к SF Pro Text.
# ---------------------------------------------------------------------------
SF_PRO_DISPLAY_REGULAR = str(FONT_DIR / "sf-pro-display-regular.otf")
SF_PRO_DISPLAY_BOLD = str(FONT_DIR / "sf-pro-display-bold.otf")
SF_PRO_TEXT_SEMIBOLD = str(FONT_DIR / "sf-pro-text-semibold.ttf")

# Порядок поиска fallback-шрифтов. Сначала пробуем bold (для крупных
# надписей), потом regular.
FONT_FALLBACKS_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]
FONT_FALLBACKS_REGULAR = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]

# ---------------------------------------------------------------------------
# Фиксированные значения из README раздел 6.
# Эти данные НЕ запрашиваются у пользователя и не меняются между запросами.
# ---------------------------------------------------------------------------
STATUS_BAR_TIME = "7:06"
CARDHOLDER = "Luis Diaz"            # обычный регистр для деталей
CARDHOLDER_UPPER = "LUIS DIAZ"      # ЗАГЛАВНЫЕ для карты
CARD_EXPIRY = "03/31"
TX_LIST_DATE = "21 marzo"

# Синяя карта Mastercard
BLUE_BALANCE = "₡5,320.00"
BLUE_TX = [
    ("Transferencia saliente", "-₡312.91", "out"),
    ("Transferencia entrante", "₡7,237.30", "in"),
]
BLUE_TX_DATE = [
    ("Transferencia entrante", "-₡145.00", "out"),
    ("Transferencia saliente", "₡310.00", "in"),
]

# Розовая карта Visa
PINK_BALANCE = "₡1,840.00"
PINK_TX = [
    ("Transferencia saliente", "-₡3,079,744", "out"),
    ("Transferencia entrante", "₡3,079,744", "in"),
]
PINK_TX_DATE = [
    ("Transferencia entrante", "₡145.00", "in"),
    ("Transferencia saliente", "₡310.00", "out"),
]

# Экран транзакции
COMMISSION_AMOUNT = "₡81,500"   # без ".00" — как в эталоне

# Экран деталей
DETAILS_TX_NUMBER = "5951143288544598"
# Маскированный ID отправителя — 14 звёздочек, как в эталоне
DETAILS_SENDER_ID = "*" * 14

__all__ = [
    # Frame / video
    "FRAME_WIDTH", "FRAME_HEIGHT", "FRAMERATE", "CRF", "PRESET", "BRIGHTNESS",
    # Animation phases
    "TRANSACTION_SLIDE_FRAMES", "DETAILS_SLIDE_FRAMES", "DETAILS_SCALED_HEIGHT",
    # Static frame counts
    "BLUE_STATIC_FRAMES", "SWIPE_FRAMES", "PINK_STATIC_FRAMES",
    "TRANSACTION_STATIC_FRAMES", "DETAILS_STATIC_FRAMES",
    # Paths
    "BASE_DIR", "TEMPLATES_DIR", "FONT_DIR",
    "SF_PRO_DISPLAY_REGULAR", "SF_PRO_DISPLAY_BOLD", "SF_PRO_TEXT_SEMIBOLD",
    "FONT_FALLBACKS_BOLD", "FONT_FALLBACKS_REGULAR",
    # Fixed values
    "STATUS_BAR_TIME", "CARDHOLDER", "CARDHOLDER_UPPER", "CARD_EXPIRY",
    "TX_LIST_DATE",
    "BLUE_BALANCE", "BLUE_TX", "BLUE_TX_DATE",
    "PINK_BALANCE", "PINK_TX", "PINK_TX_DATE",
    "COMMISSION_AMOUNT",
    "DETAILS_TX_NUMBER", "DETAILS_SENDER_ID",
]