"""Тесты Фазы 2: LangGraph агент, инструменты, chat endpoint.

Тесты используют monkeypatch для изоляции от:
- .env файла (нет OPENROUTER_API_KEY)
- реального LLM
- реальной Chroma DB
- реального Google Sheets
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from app.agent.state import AgentState
from app.agent.tools import get_tools

# ---------------------------------------------------------------------------
# Тесты get_tools()
# ---------------------------------------------------------------------------


def test_get_tools_returns_nine_tools() -> None:
    """get_tools() возвращает все 9 инструментов."""
    tools = get_tools()
    assert len(tools) == 9


def test_get_tools_names() -> None:
    """Инструменты: list_documents, rag_search, sheets_*, history_*."""
    tools = get_tools()
    names = {t.name for t in tools}
    expected = {
        "list_documents",
        "rag_search",
        "sheets_list",
        "sheets_write",
        "sheets_write_rows",
        "write_structured_data",
        "get_conversation_history",
        "get_recent_messages",
        "get_conversation_summary",
    }
    assert names == expected


def test_get_tools_have_descriptions() -> None:
    """У каждого инструмента есть описание для LLM."""
    for tool in get_tools():
        assert tool.description, f"Инструмент {tool.name} не имеет описания"


# ---------------------------------------------------------------------------
# Тесты AgentState
# ---------------------------------------------------------------------------


def test_agent_state_structure() -> None:
    """AgentState содержит нужные поля."""
    annotations = AgentState.__annotations__
    assert "messages" in annotations
    assert "thread_id" in annotations
    assert "sources" in annotations


# ---------------------------------------------------------------------------
# Тесты rag_search инструмента
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rag_search_returns_string_on_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """rag_search возвращает строку-подсказку если нет результатов."""
    from langchain_core.messages import ToolMessage
    from app.agent.tools.rag_tool import get_retriever, set_retriever

    # Создаём mock ретризер
    class MockRetriever:
        async def search_with_sources(self, **kwargs):
            from dataclasses import dataclass
            @dataclass
            class MockResult:
                content: str
                sources: list[str]
            return MockResult("Ничего релевантного не найдено. Попробуйте уточнить запрос.", [])

    set_retriever(MockRetriever())

    from app.agent.tools.rag_tool import rag_search

    result = await rag_search.ainvoke(
        {"name": "rag_search", "args": {"query": "тестовый запрос"}, "id": "call_1", "type": "tool_call"}
    )

    assert isinstance(result, ToolMessage)
    assert len(result.content) > 0

    # Сбрасываем глобальный ретризер
    set_retriever(None)

@pytest.mark.asyncio
async def test_rag_search_formats_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    """rag_search включает источники в результат."""
    from langchain_core.messages import ToolMessage
    from app.agent.tools.rag_tool import get_retriever, set_retriever

    # Создаём mock ретризер, возвращающий отформатированную строку
    class MockRetriever:
        async def search_with_sources(self, **kwargs):
            from dataclasses import dataclass
            @dataclass
            class MockResult:
                content: str
                sources: list[str]
            return MockResult(
                "Найдено 1 фрагментов.\n\n"
                "[1] Источник: test.pdf (релевантность: 0.95)\n"
                "Содержание документа",
                ["test.pdf"]
            )

    set_retriever(MockRetriever())

    from app.agent.tools.rag_tool import rag_search

    result = await rag_search.ainvoke(
        {"name": "rag_search", "args": {"query": "запрос"}, "id": "call_1", "type": "tool_call"}
    )

    assert isinstance(result, ToolMessage)
    # Проверяем, что результат содержит источник и содержание
    assert "Источник: test.pdf" in result.content
    assert "(релевантность: 0.95)" in result.content
    assert "Содержание документа" in result.content
    assert result.response_metadata == {"sources": ["test.pdf"]}

    # Сбрасываем глобальный ретризер
    set_retriever(None)


# ---------------------------------------------------------------------------
# Тесты nodes.py (parse_response_node)
# ---------------------------------------------------------------------------


def test_parse_response_node_updates_sources() -> None:
    """parse_response_node извлекает источники из ToolMessage rag_search."""
    from langchain_core.messages import ToolMessage

    from app.agent.nodes import parse_response_node
    from app.agent.state import AgentState

    # Создаём состояние с ToolMessage, содержащим источники
    state: AgentState = {
        "messages": [
            ToolMessage(
                name="rag_search",
                content="[Источник: doc1.pdf]\nСодержание.\n\n[Источник: doc2.pdf]\nДругое.",
                tool_call_id="call_1",
                response_metadata={"sources": ["doc1.pdf", "doc2.pdf"]},
            )
        ],
        "thread_id": "t",
        "sources": [],
        "step_count": 1,
        "executed_actions": [],
        "need_retry": False,
    }
    result = parse_response_node(state)
    assert result == {"sources": ["doc1.pdf", "doc2.pdf"], "need_retry": False}


def test_parse_response_node_deduplicates_sources() -> None:
    """parse_response_node удаляет дубликаты источников."""
    from langchain_core.messages import ToolMessage

    from app.agent.nodes import parse_response_node
    from app.agent.state import AgentState

    state: AgentState = {
        "messages": [
            ToolMessage(
                name="rag_search",
                content="[Источник: doc1.pdf]\n...\n[Источник: doc1.pdf]\n...",
                tool_call_id="call_1",
                response_metadata={"sources": ["doc1.pdf", "doc1.pdf"]},
            )
        ],
        "thread_id": "t",
        "sources": [],
        "step_count": 1,
        "executed_actions": [],
        "need_retry": True,
    }
    result = parse_response_node(state)
    assert result == {"sources": ["doc1.pdf"], "need_retry": True}




def test_should_continue_with_tool_calls() -> None:
    """_should_continue → 'tools' если есть tool_calls."""
    from app.agent.graph import _should_continue

    msg = AIMessage(content="", tool_calls=[{"name": "rag_search", "args": {}, "id": "1"}])
    state: AgentState = {
        "messages": [msg],
        "thread_id": "t",
        "sources": [],
    }
    assert _should_continue(state) == "tools"


def test_should_continue_without_tool_calls() -> None:
    """_should_continue → END если нет tool_calls."""
    from langgraph.graph import END

    from app.agent.graph import _should_continue

    msg = AIMessage(content="Финальный ответ")
    state: AgentState = {
        "messages": [msg],
        "thread_id": "t",
        "sources": [],
    }
    assert _should_continue(state) == END


# ---------------------------------------------------------------------------
# Тесты chat endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_endpoint_returns_sse(monkeypatch: pytest.MonkeyPatch) -> None:
    """chat endpoint возвращает EventSourceResponse."""
    from httpx import ASGITransport, AsyncClient

    # Мокаем get_graph чтобы не поднимать реальный граф
    async def mock_graph_context():
        mock_graph = AsyncMock()

        async def mock_astream_events(*args, **kwargs):
            yield {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content="Привет")}}
            yield {
                "event": "on_chain_end",
                "name": "LangGraph",
                "data": {"output": {"sources": []}},
            }

        mock_graph.astream_events = mock_astream_events
        yield mock_graph

    monkeypatch.setattr("app.api.routes.chat.get_graph", mock_graph_context)

    # Мокаем verify_api_key чтобы не проверять реальный ключ
    monkeypatch.setattr(
        "app.api.deps.get_settings",
        lambda: MagicMock(api_key="test-key"),
    )

    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/chat",
            json={"message": "Привет", "thread_id": "test-thread"},
            headers={"X-API-Key": "test-key"},
        )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
