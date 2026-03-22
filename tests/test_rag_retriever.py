"""Тесты для RAGRetriever."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document

from app.rag.config import RAGConfig
from app.rag.retriever import RAGRetriever

# ---------------------------------------------------------------------------
# Тесты multi-query
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multi_query_enabled_with_llm() -> None:
    """Multi-query генерирует альтернативные запросы при наличии LLM."""
    # Mock LLM
    mock_llm = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = "запрос 1\nзапрос 2\nзапрос 3"
    mock_llm.ainvoke.return_value = mock_response

    config = RAGConfig(
        multi_query_enabled=True,
        multi_query_max_queries=3,
        multi_query_llm_temperature=0.3,
    )
    retriever = RAGRetriever(llm=mock_llm, config=config)

    queries = await retriever._generate_queries("исходный запрос")

    assert len(queries) >= 1
    assert "исходный запрос" in queries  # оригинальный запрос всегда первый
    # LLM был вызван
    mock_llm.ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_multi_query_disabled_without_llm() -> None:
    """Без LLM multi-query отключён, возвращается только оригинальный запрос."""
    retriever = RAGRetriever(llm=None)

    queries = await retriever._generate_queries("тестовый запрос")

    assert queries == ["тестовый запрос"]


@pytest.mark.asyncio
async def test_multi_query_llm_error_fallback() -> None:
    """При ошибке LLM возвращается оригинальный запрос."""
    async def failing_llm(*args, **kwargs):
        raise Exception("LLM недоступен")

    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(side_effect=failing_llm)

    retriever = RAGRetriever(llm=mock_llm)

    queries = await retriever._generate_queries("запрос")

    # При ошибке возвращается только оригинальный запрос
    assert queries == ["запрос"]
    mock_llm.ainvoke.assert_called_once()


# ---------------------------------------------------------------------------
# Тесты поиска
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_returns_string() -> None:
    """search() возвращает строку с результатами."""
    # Mock LLM
    mock_llm = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = "альтернативный запрос"
    mock_llm.ainvoke.return_value = mock_response

    # Mock similarity_search
    with patch("app.rag.retriever.similarity_search") as mock_search:
        # Возвращаем 2 документа с score
        docs = [
            Document(page_content="Документ 1", metadata={"source": "file1.txt", "score": 0.9}),
            Document(page_content="Документ 2", metadata={"source": "file2.txt", "score": 0.7}),
        ]
        mock_search.return_value = docs

        config = RAGConfig(
            multi_query_enabled=False,  # отключаем multi-query для простоты
            default_k=2,
            score_threshold=0.0,
        )
        retriever = RAGRetriever(llm=None, config=config)

        result = await retriever.search("запрос", k=2)

        assert isinstance(result, str)
        assert "Найдено" in result
        assert "Документ 1" in result
        assert "Документ 2" in result


@pytest.mark.asyncio
async def test_search_empty_results() -> None:
    """При пустом результате возвращается сообщение 'ничего не найдено'."""
    with patch("app.rag.retriever.similarity_search") as mock_search:
        mock_search.return_value = []

        retriever = RAGRetriever(llm=None)
        result = await retriever.search("несуществующий запрос")

        assert "Ничего релевантного не найдено" in result


@pytest.mark.asyncio
async def test_search_deduplication() -> None:
    """Дубликаты документов удаляются, остаётся лучший по score."""
    with patch("app.rag.retriever.similarity_search") as mock_search:
        # Два документа с одинаковым source
        docs = [
            Document(page_content="Версия 1", metadata={"source": "doc.txt", "score": 0.5}),
            Document(page_content="Версия 2", metadata={"source": "doc.txt", "score": 0.9}),
        ]
        mock_search.return_value = docs

        retriever = RAGRetriever(llm=None)

        result = await retriever.search("запрос", k=2)

        # Проверяем, что в результате только один источник (лучший по score)
        assert "doc.txt" in result
        # Версия 2 (score 0.9) должна быть в результатах
        assert "Версия 2" in result
        # Версия 1 не должна быть (у неё score меньше)
        assert "Версия 1" not in result


@pytest.mark.asyncio
async def test_search_parallel_queries() -> None:
    """Multi-query выполняет параллельные поиски по всем запросам."""
    mock_llm = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = "альтернативный запрос"
    mock_llm.ainvoke.return_value = mock_response

    with patch("app.rag.retriever.similarity_search") as mock_search:
        # Возвращаем разные документы для разных запросов
        docs1 = [Document(page_content="Док 1", metadata={"source": "f1.txt", "score": 0.9})]
        docs2 = [Document(page_content="Док 2", metadata={"source": "f2.txt", "score": 0.8})]
        mock_search.side_effect = [docs1, docs2]

        config = RAGConfig(multi_query_enabled=True, multi_query_max_queries=2)
        retriever = RAGRetriever(llm=mock_llm, config=config)

        result = await retriever.search("запрос", k=2)

        # Проверяем, что similarity_search вызывался дважды (оригинал + альтернативный)
        assert mock_search.call_count == 2
        # Оба документа должны быть в результате
        assert "Док 1" in result
        assert "Док 2" in result


# ---------------------------------------------------------------------------
# Тесты конфигурации
# ---------------------------------------------------------------------------


def test_rag_config_defaults() -> None:
    """RAGConfig имеет правильные значения по умолчанию."""
    config = RAGConfig()

    assert config.default_k == 4
    assert config.max_k == 8
    assert config.score_threshold == 0.1
    assert config.multi_query_enabled is True
    assert config.multi_query_max_queries == 3  # по умолчанию 3
