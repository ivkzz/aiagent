"""Инструменты для работы с историей диалога."""

from typing import Annotated

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.agent.context import graph_var, thread_id_var
from app.core.llm_factory import create_llm
from app.core.logger import get_logger

log = get_logger(__name__)


@tool
async def get_conversation_history() -> str:
    """Возвращает полную историю текущего диалога в виде текста.

    Используй для анализа всего разговора, когда нужно понять контекст
    или найти информацию, которая была сказана ранее.

    Returns:
        Форматированная история диалога или сообщение об ошибке.
    """
    thread_id = thread_id_var.get()
    if not thread_id:
        return "Ошибка: thread_id не установлен."

    # Ленивый импорт чтобы избежать циклической зависимости
    from app.agent.graph import get_graph

    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    messages_formatted: list[str] = []

    graph = graph_var.get()
    if not graph:
        return "Ошибка: graph не доступен в контексте."

    try:
        state = await graph.aget_state(config)
        for msg in state.values.get("messages", []):
            if msg.type == "human":
                messages_formatted.append(f"Пользователь: {msg.content}")
            elif msg.type == "ai" and msg.content and not getattr(msg, "tool_calls", None):
                messages_formatted.append(f"Ассистент: {msg.content}")
        if not messages_formatted:
            return "История диалога пуста (нет сообщений)."
        return "\n".join(messages_formatted)
    except Exception as exc:
        log.error(f"Ошибка получения истории: {exc}")
        return f"Ошибка получения истории: {exc}"


@tool
async def get_recent_messages(
    n: Annotated[int, "Количество последних сообщений (по умолчанию 5)"] = 5,
) -> str:
    """Возвращает последние N сообщений из текущего диалога.

    Используй, когда нужно быстро вспомнить недавний контекст,
    не загружая всю длинную историю.

    Args:
        n: Количество последних сообщений для возврата (минимум 1, максимум 20).

    Returns:
        Форматированные последние сообщения.
    """
    thread_id = thread_id_var.get()
    if not thread_id:
        return "Ошибка: thread_id не установлен."

    # Ленивый импорт чтобы избежать циклической зависимости
    from app.agent.graph import get_graph

    n = max(1, min(n, 20))
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    messages_formatted: list[str] = []

    graph = graph_var.get()
    if not graph:
        return "Ошибка: graph не доступен в контексте."

    try:
        state = await graph.aget_state(config)
        all_messages = state.values.get("messages", [])
        # Берем последние n сообщений
        recent_msgs = all_messages[-n:] if all_messages else []
        for msg in recent_msgs:
            if msg.type == "human":
                messages_formatted.append(f"Пользователь: {msg.content}")
            elif msg.type == "ai" and msg.content and not getattr(msg, "tool_calls", None):
                messages_formatted.append(f"Ассистент: {msg.content}")
        if not messages_formatted:
            return "Не найдено recent сообщений."
        return "\n".join(messages_formatted)
    except Exception as exc:
        log.error(f"Ошибка получения recent сообщений: {exc}")
        return f"Ошибка получения recent сообщений: {exc}"


@tool
async def get_conversation_summary() -> str:
    """Возвращает краткую сводку текущего диалога (тему, ключевые моменты, цели).

    Используй для быстрого понимания, о чём был разговор, особенно
    если диалог очень длинный.

    Returns:
        Краткая сводка (2-3 предложения) или сообщение об ошибке.
    """
    thread_id = thread_id_var.get()
    if not thread_id:
        return "Ошибка: thread_id не установлен."

    # Ленивый импорт чтобы избежать циклической зависимости
    from app.agent.graph import get_graph

    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}

    graph = graph_var.get()
    if not graph:
        return "Ошибка: graph не доступен в контексте."

    try:
        state = await graph.aget_state(config)
        messages = state.values.get("messages", [])

        if not messages:
            return "Диалог пуст."

        # Формируем текст для суммаризации
        formatted_parts = []
        for msg in messages:
            if msg.type == "human":
                formatted_parts.append(f"Пользователь: {msg.content}")
            elif msg.type == "ai" and msg.content and not getattr(msg, "tool_calls", None):
                formatted_parts.append(f"Ассистент: {msg.content}")
        conversation_text = "\n".join(formatted_parts)

        if len(conversation_text.strip()) == 0:
            return "Диалог не содержит текстовых сообщений."

        # Генерируем суммаризацию с помощью LLM
        llm = create_llm(streaming=False, temperature=0.3)
        prompt = (
            "Ниже приведена история диалога. Сделай краткую сводку (2-3 предложения), "
            "выделив ключевую тему и цели пользователя.\n\n"
            f"{conversation_text}\n\n"
            "Сводка:"
        )
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content
        if content is None:
            summary = "Не удалось создать сводку."
        elif isinstance(content, str):
            summary = content.strip()
        else:
            summary = str(content).strip()
        return summary

    except Exception as exc:
        log.error(f"Ошибка создания сводки: {exc}")
        return f"Ошибка создания сводки: {exc}"
