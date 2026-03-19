"""Иерархия исключений приложения.

Все кастомные исключения наследуются от AIAgentError.
Это позволяет централизованно перехватывать ошибки в FastAPI exception handlers.
"""

from fastapi import HTTPException


class AIAgentError(Exception):
    """Базовое исключение всего приложения.

    Используется для перехвата любой ошибки агента в exception handler.
    """


# --- RAG ---


class RAGError(AIAgentError):
    """Базовая ошибка RAG pipeline."""


class DocumentLoadError(RAGError):
    """Ошибка при загрузке или парсинге документа."""


class DocumentIngestError(RAGError):
    """Ошибка при индексации документа в vector store."""


class VectorStoreError(RAGError):
    """Ошибка vector store (Chroma и т.п.)."""


# --- LLM ---


class LLMError(AIAgentError):
    """Ошибка при вызове LLM провайдера."""


class LLMTimeoutError(LLMError):
    """Превышено время ожидания ответа от LLM."""


class LLMStructuredOutputError(LLMError):
    """Ошибка парсинга структурированного ответа LLM."""


# --- Agent ---


class AgentError(AIAgentError):
    """Ошибка выполнения агента (LangGraph граф)."""


# --- Google Sheets ---


class SheetsError(AIAgentError):
    """Базовая ошибка Google Sheets интеграции."""


class SheetsAuthError(SheetsError):
    """Ошибка аутентификации Google Service Account."""


class SheetsWriteError(SheetsError):
    """Ошибка записи данных в Google Sheets."""


# --- HTTP (FastAPI) ---


class AuthenticationError(HTTPException):
    """Ошибка аутентификации API (неверный X-API-Key)."""

    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            detail="Неверный или отсутствующий API ключ",
            headers={"WWW-Authenticate": "ApiKey"},
        )


class NotFoundError(HTTPException):
    """Запрошенный ресурс не найден."""

    def __init__(self, resource: str = "Ресурс") -> None:
        super().__init__(
            status_code=404,
            detail=f"{resource} не найден",
        )
