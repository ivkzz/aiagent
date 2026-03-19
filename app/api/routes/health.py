"""Health check endpoint."""

from fastapi import APIRouter

from app.schemas.chat import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Проверка работоспособности сервиса.

    Возвращает статус и версию без аутентификации.
    Используется Docker HEALTHCHECK.
    """
    return HealthResponse(status="ok", version="0.1.0")
