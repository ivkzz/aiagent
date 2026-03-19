# AI Agent

Эталонный шаблон Python AI-агента с **RAG**, **LangGraph** и **Google Sheets** интеграцией.

## Стек

| Компонент | Технология |
|-----------|------------|
| API | FastAPI + SSE streaming |
| LLM | OpenRouter (GPT-4o-mini, Claude и др.) |
| Embeddings | OpenRouter `text-embedding-3-small` |
| Vector Store | Chroma (persistent) |
| Память агента | LangGraph + SQLite Checkpointer |
| Логирование диалогов | Google Sheets API |
| Упаковка | Docker + docker-compose |

## Быстрый старт

```bash
# 1. Заполнить конфиг
cp .env.example .env
# Отредактировать .env — добавить OPENROUTER_API_KEY, GOOGLE_SPREADSHEET_ID и т.д.

# 2. Запустить
docker compose up --build

# 3. Проверить
curl http://localhost:8000/health
```

## API

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/health` | Проверка работоспособности |
| POST | `/chat` | Диалог с агентом (SSE streaming) |
| POST | `/documents/ingest` | Загрузка файлов в RAG |

Документация: http://localhost:8000/docs

## Google Sheets интеграция

Агент автоматически записывает каждый диалог в Google Sheets через Service Account.

### 1. Создать проект и включить API

1. Открыть [Google Cloud Console](https://console.cloud.google.com/)
2. Создать новый проект (или выбрать существующий)
3. Перейти в **APIs & Services → Library**
4. Найти и включить **Google Sheets API**
5. Найти и включить **Google Drive API**

### 2. Создать Service Account

1. Перейти в **APIs & Services → Credentials**
2. Нажать **Create Credentials → Service Account**
3. Заполнить имя (например, `aiagent-sheets`) → **Create and Continue** → **Done**
4. Открыть созданный Service Account → вкладка **Keys**
5. **Add Key → Create new key → JSON** → скачать файл
6. Переименовать скачанный файл в `service_account.json` и положить в папку `credentials/`:

```
aiagent/
└── credentials/
    └── service_account.json   ← сюда
```

> Папка `credentials/` добавлена в `.gitignore` — ключ не попадёт в репозиторий.

### 3. Создать таблицу и выдать доступ

1. Создать новую [Google Таблицу](https://sheets.new)
2. Скопировать **ID таблицы** из URL:
   ```
   https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
                                          ^^^^^^^^^^^^^^^
   ```
3. Нажать **Поделиться** → вставить email Service Account (вида `name@project.iam.gserviceaccount.com`) → роль **Редактор** → **Отправить**
4. Переименовать первый лист в `DialogLog`

### 4. Заполнить .env

```env
GOOGLE_SERVICE_ACCOUNT_FILE=./credentials/service_account.json
GOOGLE_SPREADSHEET_ID=your-spreadsheet-id-here
```

### Структура листа DialogLog

Агент автоматически создаёт заголовки при первой записи:

| timestamp | thread_id | user_message | agent_response | sources |
|-----------|-----------|--------------|----------------|---------|
| 2025-01-01T12:00:00Z | user-123 | Что такое RAG? | RAG — это... | doc.pdf |

## Разработка

```bash
pip install -e ".[dev]"
pytest
```
