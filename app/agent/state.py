"""Состояние LangGraph агента."""
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class BaseAgentState(TypedDict):
    """Базовые поля состояния агента (обязательные)."""

    messages: Annotated[list[BaseMessage], add_messages]
    thread_id: str
    sources: list[str]
    step_count: int
    executed_actions: list[str]
    need_retry: bool


class AgentState(BaseAgentState, total=False):
    """Полное состояние агента.

    Дополнительные поля (опциональные) используются для умного RAG:
      rag_found_sources: set[str] — все уникальные источники, найденные через rag_search.
      pending_rag_searches: dict[str, str] — tool_call_id → исходный запрос (для связи запроса с результатом).
      rag_search_history: list[dict] — история выполнения поисков:
          [{"query_norm": str, "new_sources": int, "step": int, ...}]
    """

    rag_found_sources: set[str]
    pending_rag_searches: dict[str, str]
    rag_search_history: list[dict]
