"""Конфигурация RAG-системы.

Все параметры поиска, дедупликации и multi-query собраны в одном месте.
Значения можно переопределить через переменные окружения или settings.
"""

from dataclasses import dataclass
from typing import ClassVar


@dataclass
class RAGConfig:
    """Конфигурация RAG поиска."""

    # --- Поиск ---
    default_k: int = 4
    max_k: int = 8
    score_threshold: float = 0.1
    min_relevance_threshold: float = 0.0

    # --- Дедупликация ---
    dedup_similarity_threshold: float = 0.85  # порог для объединения документов
    dedup_max_length: int = 200  # длина для сравнения

    # --- Multi-query ---
    multi_query_enabled: bool = True
    multi_query_min_queries: int = 1
    multi_query_max_queries: int = 3  # можно увеличить, если LLM быстрая
    multi_query_llm_temperature: float = 0.3

    # --- Агрегация ---
    aggregate_similar_docs: bool = True
    max_aggregated_length: int = 6000  # максимальная длина агрегированного контента

    # --- Логирование ---
    log_search_details: bool = False

    # Статические preseasoned константы
    FIELD_SCORE: ClassVar[str] = "score"
    FIELD_SOURCE: ClassVar[str] = "source"
    FIELD_CONTENT: ClassVar[str] = "page_content"


# Глобальная конфигурация (может быть переопределена через DI)
_default_config: RAGConfig | None = None


def get_rag_config() -> RAGConfig:
    """Возвращает глобальную конфигурацию RAG."""
    global _default_config
    if _default_config is None:
        _default_config = RAGConfig()
    return _default_config


def set_rag_config(config: RAGConfig) -> None:
    """Устанавливает глобальную конфигурацию RAG."""
    global _default_config
    _default_config = config
