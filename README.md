# segregation-bot

Telegram-бот на `aiogram 3.x`, который по двум строкам (имя получателя + номер
клиента) собирает MP4-видео с экранами банковского приложения и отправляет его
пользователю. Реализация тестового задания `tech_task`.

## Что внутри

- **aiogram 3.17.0** — Telegram-фреймворк (polling)
- **Pillow 11.1.0** — генерация кадров
- **ffmpeg + libx264** — кодирование MP4
- **Docker** — контейнеризация и деплой
- **GitHub Actions** — CI (тесты) + CD (деплой на сервер по SSH)

## Структура проекта

```
tech_task/
├── main.py                          # точка входа бота
├── requirements.txt                 # зависимости
├── Dockerfile                       # python:3.11-slim + ffmpeg
├── docker-compose.yml               # сервис segregation-bot
├── .github/workflows/deploy.yml     # CI/CD: тесты → deploy
├── segregation_video/               # пакет режима
│   ├── __init__.py                  # публичный API
│   ├── constants.py                 # метрики и фиксированные значения
│   ├── parse_input.py               # разбор двух строк + валидация
│   ├── messages.py                  # тексты
│   ├── handler.py                   # BUTTON_KEY = "segregation"
│   ├── animations.py                # предоставленный, 2 анимации
│   ├── screens.py                   # 4 визуальных состояния
│   ├── swipe.py                     # свайп синяя → розовая
│   ├── timeline.py                  # 605 кадров
│   ├── service.py                   # рендер в уникальный временный файл
│   ├── router.py                    # aiogram 3.x FSM + handlers
│   └── templates/COP/*.png          # 9 PNG-шаблонов
├── _pillow/                         # предоставленные Pillow-утилиты
├── _util/video/                     # предоставленный кодировщик
└── tests/                           # тесты (35/35 проходят)
```

## Пользовательский сценарий

1. Пользователь отправляет боту `/start`.
2. Бот отвечает приветствием с **inline-кнопкой** «▶ Сегрегация видео».
3. Пользователь нажимает кнопку → бот просит прислать **2 строки**:
   ```
   Carlos Vinicio Barrios Quiroa
   170120010184
   ```
4. Бот валидирует ввод (имя непустое, ≤ 80 символов; номер цифровой, 6-30
   символов), при ошибке — сообщение и кнопка «❌ Отмена».
5. Бот рендерит MP4 (605 кадров, 1180×2556, 60fps, H.264 yuv420p, ~10с).
6. Бот отправляет видео пользователю с подписью и возвращает главное меню.

## Запуск локально

```bash
# 1. Установить ffmpeg
sudo apt-get install ffmpeg    # Debian/Ubuntu
brew install ffmpeg            # macOS

# 2. Python 3.10+
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Токен
export TELEGRAM_BOT_TOKEN=***...***

# 4. Запустить
python -B main.py
```

## Запуск в Docker

```bash
# Создать .env с токеном
cat > .env <<EOF
TELEGRAM_BOT_TOKEN=***
LOG_LEVEL=INFO
EOF

# Запустить
docker compose up -d --build

# Логи
docker logs -f segregation-bot

# Остановить
docker compose down
```

## CI/CD

`push` в ветку `main` → GitHub Actions:

1. **Job `test`** — устанавливает Python 3.11 + ffmpeg, прогоняет 35 тестов.
2. **Job `deploy`** (нужен `test` OK) — копирует репозиторий на сервер по SSH,
   записывает `.env` с токеном, запускает `docker compose up -d --build`,
   ждёт `healthy` статус контейнера до 60с.

### Требуемые GitHub Secrets

В `Settings → Secrets and variables → Actions`:

| Имя | Описание |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Токен от @BotFather |
| `SERVER_HOST` | IP/хост сервера (например `108.165.164.85`) |
| `SERVER_USER` | SSH-пользователь (например `root`) |
| `SERVER_SSH_KEY` | Приватный SSH-ключ с доступом к серверу |
| `SERVER_DEPLOY_DIR` | Директория на сервере (например `/root/deploy`) |

## Тесты

```bash
python -B -m unittest discover -s tests -v
# Ran 35 tests in ~10s — OK
```

## Измеренные метрики (полный рендер)

- **CPU:** Linux x86_64, Python 3.11.15
- **Real:** ~30с (с учётом overhead кодирования через ffmpeg pipe)
- **User:** ~67с (multiprocessing внутри Pillow + ffmpeg)
- **MP4:** ~1.3 MB, 605 кадров, 10.083с
- **RAM:** пиковое потребление ~700 MB (605 кадров × ~1 MB в очереди ffmpeg)
