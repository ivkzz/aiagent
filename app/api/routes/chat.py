"""Chat endpoint с SSE streaming.

Принимает сообщение пользователя и возвращает ответ агента
в виде Server-Sent Events (SSE) — нативно поддерживается Vue 3 EventSource.

Формат SSE событий:
  data: {"type": "token", "content": "часть ответа"}
  data: {"type": "sources", "sources": ["doc1.pdf"]}
  data: {"type": "done", "thread_id": "user-123"}
  data: {"type": "error", "detail": "описание ошибки"}

LangGraph astream_events (v2) используется для получения токенов от LLM.
"""

from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from sse_starlette.sse import EventSourceResponse

from app.agent.context import graph_var, thread_id_var
from app.agent.graph import get_graph
from app.api.deps import verify_api_key
from app.core.exceptions import AgentError
from app.core.logger import get_logger
from app.schemas.chat import ChatRequest, HistoryMessage, HistoryResponse, StreamChunk
from app.agent.nodes import MAX_STEPS

log = get_logger(__name__)
router = APIRouter()

_AGENT_NODE = "agent"


async def _stream_agent(request: ChatRequest) -> AsyncIterator[dict[str, str]]:
    """Запускает граф агента и генерирует SSE события (включая статусные).

    Args:
        request: Запрос с message и thread_id.

    Yields:
        Словари {"data": json_string} для EventSourceResponse.
        События: token, step_start, tool_call, tool_result, sources, done, error.
    """
    # Устанавливаем thread_id в контекст для инструментов
    thread_token = thread_id_var.set(request.thread_id)
    config: RunnableConfig = {"configurable": {"thread_id": request.thread_id}}
    input_state = {"messages": [HumanMessage(content=request.message)]}
    sources: list[str] = []
    current_step = 0
    graph_token = None

    try:
        async with get_graph() as graph:
            # Устанавливаем graph в контекст для инструментов истории
            graph_token = graph_var.set(graph)
            try:
                async for event in graph.astream_events(
                    input_state, config=config, version="v2"
                ):
                    kind = event.get("event", "")
                    metadata = event.get("metadata", {})
                    node = metadata.get("langgraph_node")
                    data = event.get("data", {})

                    # Событие: начало шага агента
                    if kind == "on_chain_start" and node == "agent":
                        current_step += 1
                        log.debug(f"Шаг агента #{current_step} начат")
                        yield {
                            "data": StreamChunk(
                                type="step_start",
                                step=current_step,
                                total=MAX_STEPS,
                            ).model_dump_json()
                        }

                    # Токены ответа агента (стриминг)
                    elif (
                        kind == "on_chat_model_stream"
                        and node == "agent"
                    ):
                        chunk = data.get("chunk")
                        if chunk and chunk.content:
                            yield {
                                "data": StreamChunk(
                                    type="token", content=chunk.content
                                ).model_dump_json()
                            }

                    # Событие: агент вызвал инструменты
                    elif kind == "on_chain_end" and node == "agent":
                        output: dict[str, Any] | str = data.get("output", {})
                        # В LangGraph 1.1+ output может быть строкой (например '__end__')
                        if isinstance(output, dict):
                            messages = output.get("messages", [])
                            if messages:
                                last_msg = messages[-1]
                                if isinstance(last_msg, AIMessage) and getattr(last_msg, "tool_calls", None):
                                    for tool_call in last_msg.tool_calls:
                                        log.info(
                                            f"Инструмент: {tool_call['name']}, "
                                            f"args={tool_call.get('args', {})}"
                                        )
                                        yield {
                                            "data": StreamChunk(
                                                type="tool_call",
                                                tool=tool_call["name"],
                                                args=tool_call.get("args", {}),
                                                step=current_step,
                                            ).model_dump_json()
                                        }

                    # Событие: инструменты завершили выполнение
                    elif kind == "on_chain_end" and node == "tools":
                        output = data.get("output", {})
                        # Защита от не-dict output (например, строка '__end__')
                        if isinstance(output, dict):
                            tool_messages = output.get("messages", [])
                            for msg in tool_messages:
                                if isinstance(msg, ToolMessage):
                                    # Краткий результат (первые 300 символов)
                                    result_text = str(msg.content)
                                    result_preview = result_text[:300]
                                    if len(result_text) > 300:
                                        result_preview += "..."
                                    log.debug(
                                        f"Результат инструмента {msg.name}: "
                                        f"{(result_preview[:50] + '...') if len(result_preview) > 50 else result_preview}"
                                    )
                                    yield {
                                        "data": StreamChunk(
                                            type="tool_result",
                                            tool=msg.name,
                                            result=result_preview,
                                            step=current_step,
                                        ).model_dump_json()
                                    }

                    # Завершение графа: извлекаем источники
                    elif kind == "on_chain_end" and event.get("name") == "LangGraph":
                        output: dict[str, Any] | str = data.get("output", {})
                        if isinstance(output, dict):
                            sources = output.get("sources", [])
                        else:
                            sources = []

            finally:
                if graph_token is not None:
                    graph_var.reset(graph_token)

        if sources:
            log.info(f"Найдено источников: {len(sources)}")
            yield {
                "data": StreamChunk(type="sources", sources=sources).model_dump_json()
            }

        log.info(f"Граф завершён за {current_step} шагов")
        yield {
            "data": StreamChunk(type="done", thread_id=request.thread_id).model_dump_json()
        }
    except Exception as exc:
        log.exception(f"Ошибка в _stream_agent: {exc}")
        yield {
            "data": StreamChunk(
                type="error", detail=f"Ошибка агента: {exc}"
            ).model_dump_json()
        }
    finally:
        thread_id_var.reset(thread_token)


@router.get("/history/{thread_id}", dependencies=[Depends(verify_api_key)], tags=["chat"])
async def get_history(thread_id: str) -> HistoryResponse:
    """Возвращает историю диалога из SQLite checkpointer.

    Args:
        thread_id: Идентификатор диалога.

    Returns:
        Список сообщений в хронологическом порядке.
    """
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    messages: list[HistoryMessage] = []

    async with get_graph() as graph:
        state = await graph.aget_state(config)
        for msg in state.values.get("messages", []):
            if msg.type == "human":
                messages.append(HistoryMessage(role="user", content=str(msg.content)))
            elif msg.type == "ai" and msg.content and not getattr(msg, "tool_calls", None):
                messages.append(HistoryMessage(role="agent", content=str(msg.content)))

    return HistoryResponse(thread_id=thread_id, messages=messages)


@router.post("", dependencies=[Depends(verify_api_key)], tags=["chat"])
async def chat(request: ChatRequest) -> EventSourceResponse:
    """Стриминговый endpoint для общения с агентом.

    Возвращает Server-Sent Events с токенами ответа.
    Требует заголовок X-API-Key.

    Агент использует RAG для поиска в загруженных документах
    и сохраняет историю диалога по thread_id.

    Args:
        request: Сообщение пользователя и thread_id.

    Returns:
        EventSourceResponse с потоком SSE событий.
    """
    log.info(f"Chat request: thread_id={request.thread_id}")

    async def event_generator() -> AsyncIterator[dict[str, str]]:
        """Генератор SSE событий — оборачивает логику с обработкой ошибок."""
        try:
            async for event in _stream_agent(request):
                yield event
        except AgentError as exc:
            log.error(f"Ошибка агента: {exc}")
            yield {
                "data": StreamChunk(type="error", detail=str(exc)).model_dump_json()
            }
        except Exception as exc:
            log.exception(f"Неожиданная ошибка в chat endpoint: {exc}")
            yield {
                "data": StreamChunk(
                    type="error", detail="Внутренняя ошибка сервера"
                ).model_dump_json()
            }

    return EventSourceResponse(event_generator())
