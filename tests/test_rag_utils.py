"""Тесты для utils.py и retriever.py."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

from app.rag.config import RAGConfig
from app.rag.utils import (
    compute_doc_hash,
    deduplicate_documents,
    format_search_results,
)
from app.rag.vectorstore import similarity_search

# ---------------------------------------------------------------------------
# Тесты utils.py
# ---------------------------------------------------------------------------


def test_compute_doc_hash_consistent() -> None:
    """Хэш одинакового内容 будет одинаковым."""
    doc = Document(page_content="Привет мир!", metadata={"source": "test.txt"})
    h1 = compute_doc_hash(doc)
    h2 = compute_doc_hash(doc)
    assert h1 == h2


def test_compute_doc_hash_different_content() -> None:
    """Хэш разного内容 будет разным."""
    doc1 = Document(page_content="Текст 1", metadata={"source": "a.txt"})
    doc2 = Document(page_content="Текст 2", metadata={"source": "a.txt"})
    assert compute_doc_hash(doc1) != compute_doc_hash(doc2)


def test_deduplicate_documents_removes_exact_duplicates() -> None:
    """Дедупликация удаляет точные дубликаты по хэшу."""
    docs = [
        Document(page_content="Содержание", metadata={"source": "doc1.txt"}),
        Document(page_content="Содержание", metadata={"source": "doc1.txt"}),  # дубль
        Document(page_content="Другое", metadata={"source": "doc2.txt"}),
    ]
    result = deduplicate_documents(docs, keep_best_per_source=False)
    assert len(result) == 2


def test_deduplicate_documents_keeps_best_by_score_per_source() -> None:
    """С keep_best_per_source=True оставляет лучший документ для каждого источника."""
    docs = [
        Document(page_content="Версия 1", metadata={"source": "doc1.txt", "score": 0.5}),
        Document(page_content="Версия 2", metadata={"source": "doc1.txt", "score": 0.9}),  # лучший
        Document(page_content="Документ 2", metadata={"source": "doc2.txt", "score": 0.7}),
    ]
    result = deduplicate_documents(docs, keep_best_per_source=True)
    assert len(result) == 2
    # Проверяем, что для doc1.txt оставлен версия с score 0.9
    for doc in result:
        if doc.metadata["source"] == "doc1.txt":
            assert doc.metadata["score"] == 0.9


def test_deduplicate_documents_sorts_by_score() -> None:
    """Результат отсортирован по score (убывание)."""
    docs = [
        Document(page_content="A", metadata={"source": "a.txt", "score": 0.3}),
        Document(page_content="B", metadata={"source": "b.txt", "score": 0.9}),
        Document(page_content="C", metadata={"source": "c.txt", "score": 0.6}),
    ]
    result = deduplicate_documents(docs, keep_best_per_source=True)
    scores = [doc.metadata.get("score", 0) for doc in result]
    assert scores == sorted(scores, reverse=True)


def test_format_search_results_includes_metadata() -> None:
    """Форматирование включает источник и score."""
    docs = [
        Document(
            page_content="Содержимое документа",
            metadata={"source": "test.pdf", "score": 0.95}
        ),
    ]
    result = format_search_results(docs, include_scores=True, include_sources=True)
    assert "Источник: test.pdf" in result
    assert "(релевантность: 0.95)" in result
    assert "Содержимое документа" in result


def test_format_search_results_empty() -> None:
    """Пустой список документов возвращает сообщение."""
    result = format_search_results([])
    assert "Ничего релевантного не найдено" in result


# ---------------------------------------------------------------------------
# Тесты vectorstore.py
# ---------------------------------------------------------------------------


def test_similarity_search_score_in_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    """similarity_search добавляет score в metadata."""
    from app.rag.vectorstore import get_vectorstore

    # Mock vectorstore
    mock_vs = MagicMock()
    mock_doc = Document(page_content="Test", metadata={"source": "file.txt"})
    mock_vs.similarity_search_with_relevance_scores.return_value = [(mock_doc, 0.85)]

    monkeypatch.setattr("app.rag.vectorstore.get_vectorstore", lambda: mock_vs)

    results = similarity_search("query", k=1, score_threshold=0.0)

    assert len(results) == 1
    assert results[0].metadata.get("score") == 0.85
