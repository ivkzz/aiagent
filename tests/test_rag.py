"""Тесты RAG pipeline: chunker и loader.

Тесты chunker используют monkeypatch для настроек,
чтобы не требовать .env файл.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from langchain_core.documents import Document

from app.core.exceptions import DocumentLoadError
from app.rag.chunker import _get_splitter, split_documents
from app.rag.loader import load_directory, load_document

# --- Тесты loader ---


def test_load_txt_document(tmp_path: Path) -> None:
    """Загружает .txt файл и проверяет содержимое."""
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("Привет мир!\nЭто тестовый документ.", encoding="utf-8")

    docs = load_document(txt_file)

    assert len(docs) >= 1
    assert "Привет мир" in docs[0].page_content
    assert docs[0].metadata["source"] == "test.txt"
    assert docs[0].metadata["file_type"] == ".txt"


def test_load_md_document(tmp_path: Path) -> None:
    """Загружает .md файл."""
    md_file = tmp_path / "readme.md"
    md_file.write_text("# Заголовок\n\nТекст параграфа.", encoding="utf-8")

    docs = load_document(md_file)

    assert len(docs) >= 1
    assert docs[0].metadata["source"] == "readme.md"


def test_load_unsupported_format_raises(tmp_path: Path) -> None:
    """Неподдерживаемый формат вызывает DocumentLoadError."""
    bad_file = tmp_path / "data.xyz"
    bad_file.write_text("content")

    with pytest.raises(DocumentLoadError, match="не поддерживается"):
        load_document(bad_file)


def test_load_directory(tmp_path: Path) -> None:
    """загружает все поддерживаемые файлы из директории."""
    (tmp_path / "a.txt").write_text("Документ А", encoding="utf-8")
    (tmp_path / "b.md").write_text("Документ Б", encoding="utf-8")
    (tmp_path / "skip.xyz").write_text("пропустить")

    docs = load_directory(tmp_path, recursive=False)

    assert len(docs) >= 2
    sources = [d.metadata["source"] for d in docs]
    assert "a.txt" in sources
    assert "b.md" in sources


# --- Тесты chunker ---


def test_split_documents_creates_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    """split_documents разбивает длинный документ на chunks."""
    # Подменяем get_settings чтобы не требовать .env
    mock_settings = MagicMock(chunk_size=500, chunk_overlap=50)
    monkeypatch.setattr("app.rag.chunker.get_settings", lambda: mock_settings)
    _get_splitter.cache_clear()
    # Создаём документ больше chunk_size (500 символов)
    long_text = "Это предложение. " * 100  # ~1700 символов
    docs = [Document(page_content=long_text, metadata={"source": "test.txt"})]

    chunks = split_documents(docs)

    assert len(chunks) > 1
    for idx, chunk in enumerate(chunks):
        assert chunk.metadata["chunk_index"] == idx
        assert chunk.metadata["source"] == "test.txt"

    _get_splitter.cache_clear()  # сбрасываем кеш после теста


def test_split_short_document_stays_one_chunk(monkeypatch: pytest.MonkeyPatch) -> None:
    """Короткий документ остаётся одним chunk."""
    mock_settings = MagicMock(chunk_size=500, chunk_overlap=50)
    monkeypatch.setattr("app.rag.chunker.get_settings", lambda: mock_settings)
    _get_splitter.cache_clear()

    short_text = "Короткий текст."
    docs = [Document(page_content=short_text, metadata={"source": "short.txt"})]

    chunks = split_documents(docs)

    assert len(chunks) == 1
    assert short_text in chunks[0].page_content
    _get_splitter.cache_clear()


def test_split_empty_documents_returns_empty() -> None:
    """Пустой список документов возвращает пустой результат."""
    chunks = split_documents([])
    assert chunks == []
