"""Зависимости FastAPI: аутентификация и другие cross-cutting concerns."""

from fastapi import Security
from fastapi.security import APIKeyHeader

from app.config import get_settings
from app.core.exceptions import AuthenticationError
from app.core.logger import get_logger

log = get_logger(__name__)

# Схема аутентификации — ищет ключ в заголовке X-API-Key
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str | None = Security(API_KEY_HEADER)) -> None:
    """Зависимость FastAPI для проверки API ключа.

    Используется через Depends(verify_api_key) в защищённых endpoints.

    Args:
        api_key: Значение заголовка X-API-Key.

    Raises:
        AuthenticationError: Если ключ отсутствует или неверный.
    """
    settings = get_settings()

    if not api_key or api_key != settings.api_key:
        log.warning("Попытка доступа с неверным API ключом")
        raise AuthenticationError()
