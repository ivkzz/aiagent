"""Загрузчики документов для RAG pipeline.

Поддерживаемые форматы: .txt .md .pdf .docx .html .csv
Каждый загрузчик возвращает list[Document] с метаданными source и page.

Основные принципы:
- load_document(path) — универсальная точка входа
- Метаданные source содержат имя файла (не полный путь — конфиденциальность)
- При ошибке парсинга выбрасывает DocumentLoadError с понятным сообщением
"""

from pathlib import Path

from langchain_community.document_loaders import (
    CSVLoader,
    Docx2txtLoader,
    PyPDFLoader,
    TextLoader,
    UnstructuredHTMLLoader,
)
from langchain_core.documents import Document

from app.core.exceptions import DocumentLoadError
from app.core.logger import get_logger

log = get_logger(__name__)

# Реестр загрузчиков по расширению файла
_LOADER_MAP = {
    ".txt": lambda p: TextLoader(str(p), encoding="utf-8"),
    ".md": lambda p: TextLoader(str(p), encoding="utf-8"),
    ".pdf": lambda p: PyPDFLoader(str(p)),
    ".docx": lambda p: Docx2txtLoader(str(p)),
    ".html": lambda p: UnstructuredHTMLLoader(str(p)),
    ".csv": lambda p: CSVLoader(str(p), encoding="utf-8"),
}


def load_document(path: Path) -> list[Document]:
    """Загружает документ из файла и возвращает список Document.

    Автоматически определяет загрузчик по расширению файла.
    Добавляет метаданные: source (имя файла), file_type (расширение).

    Args:
        path: Путь к файлу.

    Returns:
        Список Document с содержимым и метаданными.

    Raises:
        DocumentLoadError: Если формат не поддерживается или возникла ошибка парсинга.
    """
    extension = path.suffix.lower()
    loader_factory = _LOADER_MAP.get(extension)

    if not loader_factory:
        raise DocumentLoadError(
            f"Формат '{extension}' не поддерживается. "
            f"Поддерживаемые: {', '.join(_LOADER_MAP.keys())}"
        )

    log.info(f"Загрузка документа: {path.name} (тип: {extension})")

    try:
        loader = loader_factory(path)  # type: ignore[no-untyped-call]
        docs = loader.load()
    except Exception as exc:
        raise DocumentLoadError(
            f"Ошибка при разборе файла '{path.name}': {exc}"
        ) from exc

    # Нормализуем метаданные — убираем полный путь, оставляем только имя файла
    for doc in docs:
        doc.metadata["source"] = path.name
        doc.metadata["file_type"] = extension

    log.info(f"Загружено страниц/секций: {len(docs)} из {path.name}")
    return docs


def load_directory(directory: Path, recursive: bool = True) -> list[Document]:
    """Загружает все поддерживаемые документы из директории.

    Args:
        directory: Путь к директории.
        recursive: Если True — рекурсивно обходит поддиректории.

    Returns:
        Объединённый список Document из всех файлов директории.
    """
    pattern = "**/*" if recursive else "*"
    all_docs: list[Document] = []
    errors: list[str] = []

    for file_path in directory.glob(pattern):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in _LOADER_MAP:
            continue

        try:
            docs = load_document(file_path)
            all_docs.extend(docs)
        except DocumentLoadError as exc:
            log.warning(f"Пропускаем {file_path.name}: {exc}")
            errors.append(f"{file_path.name}: {exc}")

    log.info(
        f"Директория {directory.name}: загружено {len(all_docs)} документов, "
        f"ошибок: {len(errors)}"
    )
    return all_docs
