"""Chroma vector store — основной компонент RAG поиска.

Persistent Chroma хранит embeddings между перезапусками приложения.
Синглтон через lru_cache гарантирует один открытый коннекшн.

Коллекция: "documents" — единое пространство для всех проиндексированных файлов.

Публичный интерфейс:
- get_vectorstore()       → Chroma (синглтон)
- add_documents(chunks)   → добавление/обновление chunks
- similarity_search(...)  → поиск по запросу
- get_all_sources()       → асинхронное получение списка источников
"""

import asyncio
from functools import lru_cache
from typing import Any

from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.config import get_settings
from app.core.exceptions import VectorStoreError
from app.core.logger import get_logger
from app.rag.embeddings import get_embeddings

log = get_logger(__name__)

_COLLECTION_NAME = "documents"


@lru_cache(maxsize=1)
def get_vectorstore() -> Chroma:
    """Возвращает кешированный Chroma vector store.

    Данные сохраняются на диск в директорию из конфига (CHROMA_PERSIST_DIR).
    При повторном запуске загружает существующие данные.

    Returns:
        Chroma экземпляр с persistent хранилищем.

    Raises:
        VectorStoreError: Если Chroma не удалось инициализировать.
    """
    settings = get_settings()

    log.info(
        f"Инициализация Chroma: dir={settings.chroma_persist_dir}, collection={_COLLECTION_NAME}"
    )

    try:
        return Chroma(
            collection_name=_COLLECTION_NAME,
            embedding_function=get_embeddings(),
            persist_directory=settings.chroma_persist_dir,
            # L2 distance (евклидово) по умолчанию
        )
    except Exception as exc:
        raise VectorStoreError(f"Ошибка инициализации Chroma: {exc}") from exc


def add_documents(chunks: list[Document]) -> int:
    """Добавляет chunks в vector store.

    Chroma автоматически дедуплицирует по ID (если ID совпадают).
    При повторной индексации того же файла старые chunks остаются.
    Для полного переиндексирования использовать delete_by_source() + add_documents().

    Args:
        chunks: Список chunks из split_documents().

    Returns:
        Количество добавленных chunks.

    Raises:
        VectorStoreError: Если добавление не удалось.
    """
    if not chunks:
        log.warning("add_documents вызван с пустым списком chunks")
        return 0

    vectorstore = get_vectorstore()

    try:
        vectorstore.add_documents(chunks)
        log.info(f"Добавлено chunks в Chroma: {len(chunks)}")
        return len(chunks)
    except Exception as exc:
        raise VectorStoreError(f"Ошибка добавления документов в Chroma: {exc}") from exc


def similarity_search(
    query: str,
    score_threshold: float | None = None,
    k: int = 4,
) -> list[Document]:
    """Семантический поиск по вектор-базе.

    Args:
        query: Текстовый запрос пользователя.
        k: Максимальное количество результатов.
        score_threshold: Минимальный score релевантности (0.0–1.0).

    Returns:
        Список Document с score в metadata['score'], отсортированных по убыванию релевантности.
    """
    vectorstore = get_vectorstore()

    log.debug(f"Поиск в Chroma: query='{query[:50]}...', k={k}, threshold={score_threshold}")

    try:
        results = vectorstore.similarity_search_with_relevance_scores(
            query,
            k=k,
            score_threshold=score_threshold,
        )

        docs_with_scores: list[Document] = []
        for doc, score in results:
            # Сохраняем score в metadata, так как Document не позволяет динамически добавлять атрибуты
            doc.metadata["score"] = float(score)
            docs_with_scores.append(doc)

        log.debug(f"Найдено документов: {len(docs_with_scores)}")
        return docs_with_scores

    except Exception as exc:
        log.warning(f"Ошибка при поиске в Chroma: {exc}")
        return []


def delete_by_source(source_name: str) -> None:
    """Удаляет все chunks конкретного файла из vector store.

    Используется при переиндексации обновлённого файла.

    Args:
        source_name: Имя файла (значение metadata.source).
    """
    vectorstore = get_vectorstore()

    try:
        vectorstore.delete(where={"source": source_name})
        log.info(f"Удалены chunks источника: {source_name}")
    except Exception as exc:
        log.warning(f"Не удалось удалить chunks для {source_name}: {exc}")


async def get_all_sources() -> list[str]:
    """Асинхронно возвращает список всех уникальных источников документов.

    Использует run_in_executor для выполнения синхронной операции Chroma
    без блокировки event loop.

    Returns:
        Отсортированный список имён источников (source).
    """
    vectorstore = get_vectorstore()

    def _fetch_sources() -> list[str]:
        """Внутренняя синхронная функция для получения источников."""
        result = vectorstore.get()
        metadatas = result.get("metadatas", [])
        sources: set[str] = set()
        for meta in metadatas:
            if meta and "source" in meta:
                sources.add(meta["source"])
        return sorted(sources)

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _fetch_sources)
