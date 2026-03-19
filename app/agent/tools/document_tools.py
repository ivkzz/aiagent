"""Инструменты для работы с документами: список загруженных файлов."""

from langchain_core.tools import tool

from app.core.logger import get_logger
from app.rag.vectorstore import get_vectorstore

log = get_logger(__name__)


@tool
async def list_documents() -> str:
    """Возвращает список всех загруженных документов в базе знаний.

    Используй этот инструмент, чтобы узнать, какие файлы доступны для поиска.
    Это поможет сформулировать точные поисковые запросы.

    Returns:
        Список названий файлов (source) или сообщение, если документов нет.
    """
    try:
        vectorstore = get_vectorstore()
        # Получаем все записи (ids, documents, metadatas)
        result = vectorstore.get()
        metadatas = result.get("metadatas", [])
        sources = set()
        for meta in metadatas:
            if meta and "source" in meta:
                sources.add(meta["source"])
        if not sources:
            return "В базе знаний нет загруженных документов."
        # Сортируем для стабильности
        sorted_sources = sorted(sources)
        return "Загруженные документы:\n" + "\n".join(f"- {s}" for s in sorted_sources)
    except Exception as exc:
        log.error(f"Ошибка получения списка документов: {exc}")
        return f"Ошибка получения списка документов: {exc}"
