"""RAG Tool — инструмент агента для поиска по документам.

Использует RAGRetriever для multi-query поиска, дедупликации и агрегации.
Возвращает ToolMessage с content и sources в response_metadata.
"""

from typing import Annotated

from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool

from app.core.logger import get_logger
from app.rag.retriever import RAGRetriever, get_rag_config

log = get_logger(__name__)

# Глобальный ретризер (инициализируется в FastAPI lifespan)
_retriever_global: RAGRetriever | None = None


def set_retriever(retriever: RAGRetriever) -> None:
    """Устанавливает глобальный ретризер для использования в tool."""
    global _retriever_global
    _retriever_global = retriever


def get_retriever() -> RAGRetriever:
    """Возвращает глобальный ретризер."""
    global _retriever_global
    if _retriever_global is None:
        # Fallback: создаем дефолтный (без LLM для multi-query)
        _retriever_global = RAGRetriever()
    return _retriever_global


@tool
async def rag_search(
    query: str,
    k: int | None = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = None,
) -> ToolMessage:
    """RAG поиск по документам.

    Args:
        query: Поисковый запрос
        k: Количество результатов (по умолчанию 4, максимум 8)
        tool_call_id: Внедряемый ID вызова инструмента (не указывать)

    Returns:
        ToolMessage с aggregated content и sources в response_metadata
    """
    retriever = get_retriever()
    config = get_rag_config()

    # Валидация k
    if k is None:
        k = config.default_k
    k = max(1, min(k, config.max_k))

    log.info(f"RAG search: '{query}' (k={k}, multi_query={config.multi_query_enabled})")

    try:
        result = await retriever.search_with_sources(
            query=query,
            k=k,
            use_multi_query=config.multi_query_enabled,
            deduplicate=True,
        )

        return ToolMessage(
            content=result.content,
            name="rag_search",
            tool_call_id=tool_call_id,
            response_metadata={"sources": result.sources},
        )

    except Exception as exc:
        log.exception(f"Ошибка rag_search: {exc}")
        return ToolMessage(
            content=f"Ошибка при поиске: {str(exc)}. Попробуйте переформулировать запрос.",
            name="rag_search",
            tool_call_id=tool_call_id,
            response_metadata={"sources": []},
        )
