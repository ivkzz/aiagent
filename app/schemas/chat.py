"""Pydantic схемы для API чата и health endpoint."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Запрос к агенту."""

    message: str = Field(..., min_length=1, max_length=10000, description="Сообщение пользователя")
    thread_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Идентификатор диалога для персистентной памяти",
    )


class StreamChunk(BaseModel):
    """Один SSE-чанк в потоковом ответе агента."""

    type: str = Field(
        ...,
        description="Тип чанка: 'token' | 'sources' | 'done' | 'error' | 'step_start' | 'tool_call' | 'tool_result'",
    )
    content: str | None = Field(None, description="Текстовый токен (для type='token')")
    sources: list[str] | None = Field(
        None,
        description="Список источников из RAG (для type='sources')",
    )
    thread_id: str | None = Field(None, description="ID диалога (для type='done')")
    detail: str | None = Field(None, description="Сообщение об ошибке (для type='error')")
    # Поля для статусных событий
    step: int | None = Field(None, description="Номер текущего шага (для step_start, tool_call, tool_result)")
    total: int | None = Field(None, description="Общее количество шагов (для step_start)")
    tool: str | None = Field(None, description="Имя инструмента (для tool_call, tool_result)")
    args: dict | None = Field(None, description="Аргументы вызова (для tool_call)")
    result: str | None = Field(None, description="Результат выполнения (для tool_result, кратко)")


class AgentResponse(BaseModel):
    """Структурированный ответ агента (используется в .with_structured_output).

    LangGraph возвращает этот объект, который затем стримится токен за токеном.
    """

    answer: str = Field(..., description="Ответ агента на вопрос пользователя")
    sources: list[str] = Field(
        default_factory=list,
        description="Список файлов/источников, использованных для ответа",
    )
    needs_clarification: bool = Field(
        False,
        description="True если агент не уверен и просит уточнить вопрос",
    )


class HistoryMessage(BaseModel):
    """Сообщение из истории диалога."""

    role: str = Field(..., description="'user' или 'agent'")
    content: str = Field(..., description="Текст сообщения")


class HistoryResponse(BaseModel):
    """История диалога по thread_id."""

    thread_id: str
    messages: list[HistoryMessage]


class HealthResponse(BaseModel):
    """Ответ health endpoint."""

    status: str = Field("ok", description="Статус сервиса")
    version: str = Field(..., description="Версия приложения")
