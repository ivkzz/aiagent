"""pytest конфигурация и общие fixtures."""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.config import get_settings
from app.main import app


@pytest.fixture
def test_client() -> TestClient:
    """Синхронный TestClient для простых тестов."""
    return TestClient(app)


@pytest.fixture
async def async_client() -> AsyncClient:
    """Асинхронный клиент для тестов с SSE streaming."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def api_headers() -> dict[str, str]:
    """Заголовки с корректным API ключом для тестов."""
    settings = get_settings()
    return {"X-API-Key": settings.api_key}
