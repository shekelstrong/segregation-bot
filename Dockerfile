FROM python:3.11-slim

# Системные зависимости
# - ffmpeg: кодирование MP4 через _util/video
# - libx264 / libx265 / libvpx: кодеки для ffmpeg
# - шрифты DejaVu (fallback в screens.py при отсутствии SF Pro)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        fonts-dejavu-core \
        fonts-liberation \
        fonts-noto-core \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Зависимости — кэшируются отдельно от кода
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Код проекта
COPY . .

# Не запускаем от root
RUN useradd --create-home --shell /bin/bash bot \
    && chown -R bot:bot /app
USER bot

# Healthcheck: если процесс умер — контейнер unhealthy
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD pgrep -f "python.*main.py" > /dev/null || exit 1

CMD ["python", "-B", "main.py"]
