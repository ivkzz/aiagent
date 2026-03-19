"""Тесты API endpoints (Фаза 4).

E2E тесты через TestClient с моками внешних зависимостей.
"""

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient


def test_health_check(test_client: TestClient) -> None:
    """Health endpoint возвращает ok без аутентификации."""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_chat_without_api_key(test_client: TestClient) -> None:
    """Запрос без API ключа возвращает 401."""
    response = test_client.post(
        "/chat",
        json={"message": "Привет", "thread_id": "test-thread"},
    )
    assert response.status_code == 401


def test_chat_with_wrong_api_key(test_client: TestClient) -> None:
    """Запрос с неверным API ключом возвращает 401."""
    response = test_client.post(
        "/chat",
        json={"message": "Привет", "thread_id": "test-thread"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401


def test_ingest_without_api_key(test_client: TestClient) -> None:
    """Загрузка документов без API ключа возвращает 401."""
    response = test_client.post("/documents/ingest")
    assert response.status_code == 401


def test_ingest_unsupported_format(
    test_client: TestClient, api_headers: dict
) -> None:
    """Файл с неподдерживаемым расширением возвращает ошибку в results."""
    response = test_client.post(
        "/documents/ingest",
        files={"files": ("data.xyz", BytesIO(b"content"), "text/plain")},
        headers=api_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["documents_processed"] == 0
    assert len(data["errors"]) == 1
    assert "data.xyz" in data["errors"][0]


def test_ingest_txt_file(
    test_client: TestClient,
    api_headers: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Успешная загрузка .txt файла возвращает chunks_added > 0."""
    from langchain_core.documents import Document

    monkeypatch.setattr(
        "app.api.routes.documents.load_document",
        lambda path: [Document(page_content="Тестовый контент", metadata={"source": "test.txt"})],
    )
    monkeypatch.setattr(
        "app.api.routes.documents.split_documents",
        lambda docs: docs,
    )
    monkeypatch.setattr(
        "app.api.routes.documents.add_documents",
        lambda chunks: len(chunks),
    )

    response = test_client.post(
        "/documents/ingest",
        files={"files": ("test.txt", BytesIO(b"Test content"), "text/plain")},
        headers=api_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["documents_processed"] == 1
    assert data["chunks_added"] == 1
    assert data["errors"] == []


def test_ingest_multiple_files(
    test_client: TestClient,
    api_headers: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Загрузка нескольких файлов — обрабатываются все поддерживаемые."""
    from langchain_core.documents import Document

    monkeypatch.setattr(
        "app.api.routes.documents.load_document",
        lambda path: [Document(page_content="content", metadata={"source": path.name})],
    )
    monkeypatch.setattr("app.api.routes.documents.split_documents", lambda docs: docs)
    monkeypatch.setattr("app.api.routes.documents.add_documents", lambda chunks: 2)

    response = test_client.post(
        "/documents/ingest",
        files=[
            ("files", ("a.txt", BytesIO(b"aaa"), "text/plain")),
            ("files", ("b.md", BytesIO(b"bbb"), "text/markdown")),
            ("files", ("c.xyz", BytesIO(b"ccc"), "text/plain")),
        ],
        headers=api_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["documents_processed"] == 2
    assert data["chunks_added"] == 4
    assert len(data["errors"]) == 1  # только c.xyz


@pytest.mark.asyncio
async def test_chat_endpoint_returns_sse(monkeypatch: pytest.MonkeyPatch) -> None:
    """chat endpoint возвращает EventSourceResponse с SSE событиями."""
    from contextlib import asynccontextmanager

    from httpx import ASGITransport, AsyncClient

    @asynccontextmanager
    async def mock_graph_context():
        mock_graph = AsyncMock()

        async def mock_astream_events(*args, **kwargs):
            yield {
                "event": "on_chat_model_stream",
                "metadata": {"langgraph_node": "agent"},
                "data": {"chunk": MagicMock(content="Привет")},
            }
            yield {
                "event": "on_chain_end",
                "name": "LangGraph",
                "data": {"output": {"sources": ["doc.pdf"]}},
            }

        mock_graph.astream_events = mock_astream_events
        yield mock_graph

    monkeypatch.setattr("app.api.routes.chat.get_graph", mock_graph_context)
    monkeypatch.setattr(
        "app.api.deps.get_settings",
        lambda: MagicMock(api_key="test-key"),
    )

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/chat",
            json={"message": "Привет", "thread_id": "t-1"},
            headers={"X-API-Key": "test-key"},
        )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    body = response.text
    assert "token" in body
    assert "done" in body


@pytest.mark.asyncio
async def test_chat_endpoint_includes_sources_event(monkeypatch: pytest.MonkeyPatch) -> None:
    """SSE поток содержит событие sources если RAG нашёл документы."""
    from contextlib import asynccontextmanager

    from httpx import ASGITransport, AsyncClient

    @asynccontextmanager
    async def mock_graph_context():
        mock_graph = AsyncMock()

        async def mock_astream_events(*args, **kwargs):
            yield {
                "event": "on_chain_end",
                "name": "LangGraph",
                "data": {"output": {"sources": ["file.pdf"]}},
            }

        mock_graph.astream_events = mock_astream_events
        yield mock_graph

    monkeypatch.setattr("app.api.routes.chat.get_graph", mock_graph_context)
    monkeypatch.setattr(
        "app.api.deps.get_settings",
        lambda: MagicMock(api_key="test-key"),
    )

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/chat",
            json={"message": "Вопрос", "thread_id": "t-2"},
            headers={"X-API-Key": "test-key"},
        )

    assert "sources" in response.text
    assert "file.pdf" in response.text
