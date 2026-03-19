"""Pydantic схемы для Google Sheets интеграции."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class SheetLogEntry(BaseModel):
    """Строка лога диалога, записываемая в Google Sheets.

    Структура листа DialogLog:
    | timestamp | thread_id | user_message | agent_response | sources |
    """

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="Время ответа агента (UTC)",
    )
    thread_id: str = Field(..., description="ID диалога")
    user_message: str = Field(..., description="Сообщение пользователя")
    agent_response: str = Field(..., description="Ответ агента")
    sources: list[str] = Field(
        default_factory=list,
        description="Источники из RAG, использованные для ответа",
    )

    def to_row(self) -> list[str]:
        """Конвертирует запись в строку для Google Sheets API.

        Returns:
            Список строк в порядке колонок листа.
        """
        return [
            self.timestamp.isoformat(),
            self.thread_id,
            self.user_message,
            self.agent_response,
            ", ".join(self.sources) if self.sources else "",
        ]

    @classmethod
    def headers(cls) -> list[str]:
        """Возвращает заголовки колонок для первой строки листа."""
        return ["timestamp", "thread_id", "user_message", "agent_response", "sources"]
