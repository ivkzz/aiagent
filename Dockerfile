# Стадия сборки зависимостей
FROM python:3.12-slim AS builder

WORKDIR /build

# Устанавливаем uv — быстрый менеджер пакетов Python
RUN pip install uv --quiet

# Устанавливаем зависимости (только runtime, без dev) в системный Python
RUN uv pip install --system --no-cache \
    "fastapi>=0.115" \
    "uvicorn[standard]>=0.34" \
    "sse-starlette>=2.1" \
    "python-multipart>=0.0.20" \
    "langchain>=0.3" \
    "langchain-openai>=0.3" \
    "langgraph>=0.3" \
    "langgraph-checkpoint-sqlite>=2.0" \
    "langchain-chroma>=0.2" \
    "chromadb>=0.6" \
    "langchain-community>=0.3" \
    "pypdf>=5.0" \
    "python-docx>=1.1" \
    "docx2txt>=0.8" \
    "unstructured[html,csv]>=0.16" \
    "gspread>=6.1" \
    "google-auth>=2.35" \
    "pydantic>=2.10" \
    "pydantic-settings>=2.6" \
    "loguru>=0.7" \
    "httpx>=0.28"

# Финальный образ — минимальный
FROM python:3.12-slim AS runtime

WORKDIR /app

# Копируем установленные пакеты из builder
COPY --from=builder /usr/local/lib/python3.12/site-packages \
    /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Копируем конфигурационные файлы и исходный код
COPY pyproject.toml .
COPY app/ ./app/

# Создаём директории для данных и логов
RUN mkdir -p data/chroma data/sqlite data/documents logs credentials

# Запуск от непривилегированного пользователя
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
