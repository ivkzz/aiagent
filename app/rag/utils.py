"""Вспомогательные функции для RAG: дедупликация, агрегация, форматирование."""

import hashlib
from typing import Callable

from langchain_core.documents import Document

from app.core.logger import get_logger
from app.rag.config import RAGConfig, get_rag_config

log = get_logger(__name__)


def compute_doc_hash(doc: Document, max_length: int = 200) -> str:
    """Вычисляет хэш документа для быстрой дедупликации.

    Args:
        doc: Document объект
        max_length: максимальная длина текста для хэширования

    Returns:
        SHA256 хэш строки
    """
    content = doc.page_content[:max_length]
    return hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()[:16]


def _get_doc_score(doc: Document) -> float | None:
    """Извлекает score документа из metadata."""
    return doc.metadata.get("score")


def are_docs_duplicate(doc1: Document, doc2: Document, config: RAGConfig) -> bool:
    """Проверяет, являются ли два документа дубликатами.

    Стратегия:
    1. Точное совпадение хэша первых N символов (быстрая проверка)
    2. Если хэши разные, но source одинаковый — считаем дублем (оставляем лучший по score)

    Args:
        doc1, doc2: Документы для сравнения
        config: Конфигурация с порогом dedup_similarity_threshold

    Returns:
        True если документы — дубликаты
    """
    # Быстрая проверка по хэшу
    if compute_doc_hash(doc1, config.dedup_max_length) == compute_doc_hash(
        doc2, config.dedup_max_length
    ):
        return True

    # Если документы из одного источника — считаем дубликатами (лучший оставим в deduplicate_documents)
    source1 = doc1.metadata.get(config.FIELD_SOURCE)
    source2 = doc2.metadata.get(config.FIELD_SOURCE)
    if source1 and source2 and source1 == source2:
        return True

    # Дополнительная проверка по Jaccard (опционально, если настроен высокий порог)
    if config.dedup_similarity_threshold > 0.8:
        words1 = set(doc1.page_content.lower().split())
        words2 = set(doc2.page_content.lower().split())

        if not words1 or not words2:
            return False

        intersection = len(words1 & words2)
        union = len(words1 | words2)
        jaccard = intersection / union if union > 0 else 0

        if jaccard >= config.dedup_similarity_threshold:
            return True

    return False


def deduplicate_documents(
    docs: list[Document],
    config: RAGConfig | None = None,
    keep_best_per_source: bool = True,
) -> list[Document]:
    """Удаляет дубликаты из списка документов.

    Стратегия:
    - Группируем по источнику (source) если keep_best_per_source=True
    - Удаляем точные дубликаты по хэшу
    - Сохраняем порядок и максимальное количество

    Args:
        docs: Исходный список документов
        config: Конфигурация
        keep_best_per_source: Если True, возвращаем лучший документ для каждого источника
                            (на основе score из metadata, если доступен)

    Returns:
        Список уникальных документов в исходном порядке (или отсортированных по score)
    """
    if config is None:
        config = get_rag_config()

    if not docs:
        return []

    seen_hashes: set[str] = set()
    unique_docs: list[Document] = []

    # Группируем по источнику для выборки лучшего
    source_best: dict[str, Document] = {}

    for doc in docs:
        doc_hash = compute_doc_hash(doc, config.dedup_max_length)

        if doc_hash in seen_hashes:
            continue  # пропускаем дубликат

        seen_hashes.add(doc_hash)

        if keep_best_per_source:
            source = doc.metadata.get(config.FIELD_SOURCE, "unknown")

            existing = source_best.get(source)
            if existing is None:
                source_best[source] = doc
            else:
                # Сравниваем scores из metadata
                current_score = doc.metadata.get("score")
                existing_score = existing.metadata.get("score")

                # Выбираем документ с бОльшим score (если оба есть, или любой если один None)
                if current_score is not None and existing_score is not None:
                    if current_score > existing_score:
                        source_best[source] = doc
                elif current_score is not None:
                    source_best[source] = doc
                # Если current_score None, оставляем existing (или если оба None — первый)
        else:
            unique_docs.append(doc)

    # Формируем результат
    if keep_best_per_source:
        # Сортируем по score (если есть, по убыванию), затем по source
        result = list(source_best.values())
        result.sort(
            key=lambda d: (
                -1 * (d.metadata.get("score") or 0),
                d.metadata.get(config.FIELD_SOURCE, ""),
            )
        )
    else:
        result = unique_docs

    log.debug(
        f"Дедупликация: {len(docs)} → {len(result)} документов "
        f"(удалено {len(docs) - len(result)})"
    )

    return result


def aggregate_documents_content(
    docs: list[Document],
    max_length: int | None = None,
    separator: str = "\n\n---\n\n",
) -> str:
    """Агрегирует содержимое документов в одну строку.

    Args:
        docs: Список документов
        max_length: Максимальная общая длина (обрезает последний если превышено)
        separator: Разделитель между документами

    Returns:
        Объединённый текст
    """
    if max_length is None:
        max_length = get_rag_config().max_aggregated_length

    parts = []
    total_len = 0

    for doc in docs:
        content = doc.page_content.strip()
        content_len = len(content)

        if max_length and total_len + content_len > max_length:
            # Добавляем столько помещается
            remaining = max_length - total_len
            if remaining > 100:  # минимум 100 символов для осмысленного текста
                parts.append(content[:remaining])
                total_len = max_length
            break
        else:
            parts.append(content)
            total_len += content_len

    return separator.join(parts)


def format_search_results(
    docs: list[Document],
    config: RAGConfig | None = None,
    include_scores: bool = True,
    include_sources: bool = True,
    max_docs: int | None = None,
) -> str:
    """Форматирует список документов в читаемый строковый результат.

    Args:
        docs: Найденные документы (с score в metadata)
        config: Конфигурация (использует глобальную если None)
        include_scores: Включать ли релевантность в вывод
        include_sources: Включать ли источник в вывод
        max_docs: Максимальное количество документов для вывода

    Returns:
        Отформатированная строка с результатами
    """
    if config is None:
        config = get_rag_config()

    if not docs:
        return "Ничего релевантного не найдено."

    if max_docs:
        docs = docs[:max_docs]

    parts: list[str] = []

    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get(config.FIELD_SOURCE, "неизвестный источник")
        score = doc.metadata.get("score")  # Читаем из metadata

        score_str = f"(релевантность: {round(score, 3)})" if include_scores and score is not None else ""
        source_str = f"Источник: {source}" if include_sources else ""

        header = " ".join(filter(None, [f"[{i}]", source_str, score_str])).strip()
        content = doc.page_content.strip()

        parts.append(f"{header}\n{content}")

    result = "\n\n---\n\n".join(parts)

    summary = f"Найдено {len(docs)} фрагментов.\n\n"
    return summary + result
