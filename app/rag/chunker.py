"""Разбивка документов на chunks для RAG.

Использует RecursiveCharacterTextSplitter — стандарт для большинства задач RAG.
Рекурсивно разбивает по '\n\n' → '\n' → ' ' → '' пока chunk не достигнет нужного размера.

Параметры из конфига:
- chunk_size: целевой размер chunk (по умолчанию 1000 символов)
- chunk_overlap: перекрытие между chunks (по умолчанию 200 символов)

Перекрытие нужно, чтобы контекст на границах chunks не терялся.
"""

from functools import lru_cache

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings
from app.core.logger import get_logger

log = get_logger(__name__)


@lru_cache(maxsize=1)
def _get_splitter() -> RecursiveCharacterTextSplitter:
    """Кешированный экземпляр сплиттера с параметрами из конфига."""
    settings = get_settings()
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        # Разделители по убыванию приоритета
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
        is_separator_regex=False,
    )


def split_documents(documents: list[Document]) -> list[Document]:
    """Разбивает список Document на chunks.

    Каждый chunk наследует метаданные исходного документа.
    Добавляет метаданные chunk_index для отладки.

    Args:
        documents: Список Document из загрузчика.

    Returns:
        Список chunk-Document готовых к индексации в vector store.
    """
    if not documents:
        log.warning("split_documents вызван с пустым списком")
        return []

    splitter = _get_splitter()
    chunks = splitter.split_documents(documents)

    # Добавляем индекс chunk для отладки (помогает найти источник в Chroma)
    for idx, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = idx

    log.info(
        f"Разбивка: {len(documents)} документ(ов) → {len(chunks)} chunks "
        f"(chunk_size={get_settings().chunk_size}, overlap={get_settings().chunk_overlap})"
    )
    return chunks
