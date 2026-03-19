"""Фабрика embeddings для RAG pipeline.

Использует langchain-openai, совместимый с OpenRouter.
Embeddings кешируются в памяти через синглтон — дорогой объект создаётся один раз.
"""

from functools import lru_cache

from langchain_openai import OpenAIEmbeddings

from app.config import get_settings
from app.core.logger import get_logger

log = get_logger(__name__)


@lru_cache(maxsize=1)
def get_embeddings() -> OpenAIEmbeddings:
    """Возвращает кешированный экземпляр embeddings модели.

    Кеш гарантирует, что объект создаётся один раз за весь жизненный цикл приложения.

    Returns:
        Сконфигурированный OpenAIEmbeddings клиент через OpenRouter.
    """
    settings = get_settings()

    log.info(f"Инициализация embeddings: model={settings.embedding_model}")

    return OpenAIEmbeddings(
        model=settings.embedding_model,
        openai_api_key=settings.openrouter_api_key,
        openai_api_base=settings.openrouter_base_url,
        chunk_size=100,
    )
