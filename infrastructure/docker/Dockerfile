FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    libxml2-dev libxslt-dev \
    libfreetype6-dev libjpeg-dev zlib1g-dev \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libasound2 libpango-1.0-0 libcairo2 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY backend ./backend
COPY shared ./shared

RUN pip install --upgrade pip && \
    pip install pandas scikit-learn numpy joblib && \
    pip install -e ".[dev]"

RUN playwright install chromium && playwright install-deps chromium || true

# Create non-root user
RUN useradd -m -u 1000 digizafe && \
    mkdir -p /app/secrets && \
    chown -R digizafe:digizafe /app

USER digizafe

WORKDIR /app/backend

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
