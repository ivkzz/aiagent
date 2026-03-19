"""Эндпоинт для экспорта полной истории чата со всеми деталями."""

from typing import Any

from fastapi import APIRouter, Depends
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.api.deps import verify_api_key
from app.agent.context import graph_var, thread_id_var
from app.agent.graph import get_graph
from app.core.logger import get_logger
from app.schemas.chat import HistoryResponse

log = get_logger(__name__)
router = APIRouter()


@router.get("/full/{thread_id}", dependencies=[Depends(verify_api_key)], tags=["export"])
async def export_full_history(thread_id: str) -> dict[str, Any]:
    """Возвращает полную историю чата со всеми деталями для анализа.

    Включает:
    - Все сообщения (user/agent)
    - Все шаги агента и вызовы инструментов
    - Источники (RAG results)
    - Список загруженных документов
    - Статистику сессии

    Args:
        thread_id: Идентификатор диалога.

    Returns:
        Полная структура данных для экспорта и анализа.
    """
    from app.api.routes.documents import list_documents

    config = {"configurable": {"thread_id": thread_id}}
    messages: list[dict[str, Any]] = []
    execution_events: list[dict[str, Any]] = []
    all_sources: list[str] = []
    stats = {
        "total_user_messages": 0,
        "total_agent_messages": 0,
        "total_tool_calls": 0,
        "total_steps": 0,
        "tools_used": set(),
    }

    try:
        async with get_graph() as graph:
            state = await graph.aget_state(config)
            raw_messages = state.values.get("messages", [])

            for msg in raw_messages:
                if msg.type == "human":
                    messages.append({
                        "role": "user",
                        "content": str(msg.content),
                        "timestamp": None,  # Не хранится в LangGraph state
                    })
                    stats["total_user_messages"] += 1

                elif msg.type == "ai":
                    # Извлекаем информаию о вызовах инструментов
                    tool_calls = getattr(msg, "tool_calls", []) or []
                    tool_call_info = []
                    for tc in tool_calls:
                        tool_call_info.append({
                            "tool": tc.get("name"),
                            "args": tc.get("args", {}),
                        })

                    messages.append({
                        "role": "agent",
                        "content": str(msg.content) if msg.content else "",
                        "tool_calls": tool_call_info,
                        "timestamp": None,
                    })
                    stats["total_agent_messages"] += 1
                    stats["total_tool_calls"] += len(tool_calls)
                    for tc in tool_calls:
                        stats["tools_used"].add(tc.get("name"))

                elif msg.type == "tool":
                    # Сообщения от инструментов (результаты)
                    all_sources.extend(getattr(msg, "sources", []) or [])
                    # Можно добавить в execution_events как tool_result
                    execution_events.append({
                        "step": None,  # Нужно восстановить из контекста
                        "type": "tool_result",
                        "tool": getattr(msg, "name", "unknown"),
                        "result": str(msg.content)[:500],  # Ограничиваем длину
                        "timestamp": None,
                    })

        # Пытаемся получить sources из последнего output (если есть)
        # В RAG sources добавляются в metadata или отдельным полем
        if not all_sources:
            # Ищем в последнем сообщении агента
            for msg in reversed(raw_messages):
                if msg.type == "ai":
                    srcs = getattr(msg, "sources", [])
                    if srcs:
                        all_sources = srcs
                        break

    except Exception as exc:
        log.error(f"Ошибка получения полной истории: {exc}")
        raise

    # Получаем список документов
    try:
        documents = await list_documents()
    except Exception as exc:
        log.error(f"Ошибка получения списка документов: {exc}")
        documents = []

    # Преобразуем set в list для JSON
    stats["tools_used"] = list(stats["tools_used"])

    return {
        "thread_id": thread_id,
        "exported_at": None,  # Заполнит клиент
        "messages": messages,
        "execution_events": execution_events,
        "sources": list(set(all_sources)),  # Уникальные
        "documents": documents,
        "statistics": stats,
    }
