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

# Healthcheck: проверяем, что python-процесс жив.
# python:3.11-slim не содержит pgrep/ps, поэтому используем /proc.
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import os, sys; pids=[p for p in os.listdir('/proc') if p.isdigit() and any('main.py' in open(f'/proc/{p}/cmdline').read().replace(chr(0),' ').split() for _ in [0])]; sys.exit(0 if pids else 1)" || exit 1

CMD ["python", "-B", "main.py"]
