"""Централизованная конфигурация приложения через pydantic-settings.

Все параметры читаются из .env файла.
Используется единственный экземпляр через get_settings().
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения.

    Значения загружаются из .env файла или переменных окружения.
    Переменные окружения имеют приоритет над .env.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- LLM (OpenRouter) ---
    openrouter_api_key: str = Field(..., description="OpenRouter API ключ")
    openrouter_base_url: str = Field(
        "https://openrouter.ai/api/v1",
        description="OpenRouter base URL",
    )
    llm_model: str = Field(
        "openai/gpt-4o-mini",
        description="Модель для генерации ответов",
    )
    embedding_model: str = Field(
        "openai/text-embedding-3-small",
        description="Модель для создания embeddings",
    )

    # --- RAG / Chroma ---
    chroma_persist_dir: str = Field(
        "./data/chroma",
        description="Директория для хранения Chroma DB",
    )
    chunk_size: int = Field(
        1000,
        ge=100,
        le=8000,
        description="Размер chunk при разбивке документов",
    )
    chunk_overlap: int = Field(
        200,
        ge=0,
        le=1000,
        description="Перекрытие между chunks",
    )

    # --- Memory (LangGraph Checkpointer) ---
    sqlite_path: str = Field(
        "./data/sqlite/checkpoints.db",
        description="Путь к SQLite файлу для хранения истории диалогов",
    )

    # --- Google Sheets ---
    google_service_account_file: str = Field(
        "./credentials/service_account.json",
        description="Путь к JSON файлу Service Account",
    )
    google_spreadsheet_id: str = Field(
        ...,
        description="ID Google Spreadsheet для записи логов",
    )

    # --- FastAPI ---
    api_key: str = Field(..., description="Секретный ключ для X-API-Key аутентификации")
    api_host: str = Field("0.0.0.0", description="Хост FastAPI сервера")
    api_port: int = Field(8000, ge=1, le=65535, description="Порт FastAPI сервера")

    # --- Логирование ---
    log_level: str = Field("INFO", description="Уровень логирования: DEBUG/INFO/WARNING/ERROR")
    log_json: bool = Field(False, description="Вывод логов в JSON формате")


@lru_cache
def get_settings() -> Settings:
    """Возвращает кешированный экземпляр настроек.

    Используется как зависимость FastAPI или напрямую.
    """
    return Settings()
