"""Инструменты для работы с документами: список загруженных файлов."""

from langchain_core.tools import tool

from app.core.logger import get_logger
from app.rag.vectorstore import get_all_sources

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
        sources = await get_all_sources()
        if not sources:
            return "В базе знаний нет загруженных документов."
        return "Загруженные документы:\n" + "\n".join(f"- {s}" for s in sources)
    except Exception as exc:
        log.error(f"Ошибка получения списка документов: {exc}")
        return f"Ошибка получения списка документов: {exc}"
