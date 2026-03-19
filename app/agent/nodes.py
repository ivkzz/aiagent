"""Узлы LangGraph графа."""

import re
from collections.abc import Awaitable, Callable
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.runnables import Runnable

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.state import AgentState
from app.core.logger import get_logger

log = get_logger(__name__)

# Константы для анти-зацикливания
MAX_STEPS = 15
MAX_REPEATS = 2
MAX_RAG_HISTORY = 20  # Максимальное количество записей истории поиска


def _normalize_query(query: str) -> str:
    """Нормализует поисковый запрос для сравнения.
    Убирает пунктуацию, приводит к нижнему регистру, удаляет лишние пробелы.
    """
    query = re.sub(r"[^\w\s]", " ", query.lower())
    query = re.sub(r"\s+", " ", query).strip()
    return query


def _are_queries_semantically_similar(q1: str, q2: str, threshold: float = 0.7) -> bool:
    """Проверяет семантическую схожесть двух нормализованных запросов по коэффициенту Жаккара."""
    if not q1 or not q2:
        return False
    words1 = set(q1.split())
    words2 = set(q2.split())
    if not words1 or not words2:
        return False
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    if union == 0:
        return False
    jaccard = intersection / union
    return jaccard >= threshold


def _extract_sources_from_rag_message(content: str) -> set[str]:
    """Извлекает названия источников из текста ответа rag_search.

    Поддерживает форматы:
    - Старый: [Источник: filename]
    - Новый: [1] Источник: filename (релевантность: 0.95)

    Args:
        content: Текст ToolMessage от rag_search

    Returns:
        Множество уникальных имён источников
    """
    sources: set[str] = set()

    for line in content.splitlines():
        if "Источник:" in line:
            # Извлекаем часть после "Источник:"
            after_source = line.split("Источник:", 1)[1]
            # Берём первое слово (до пробела или скобки) и удаляем завершающие скобки
            source = after_source.strip().split()[0].rstrip(')]')
            if source:
                sources.add(source)

    return sources


def _process_completed_rag_searches(state: AgentState) -> None:
    """Обрабатывает завершённые rag_search (ToolMessage) и обновляет статистику.

    RAGRetriever сам выполняет дедупликацию, поэтому здесь только собираем
    источники из ToolMessage (response_metadata["sources"]) в общее состояние rag_found_sources.

    Обновляет поля:
      - rag_found_sources: set[str] — все уникальные источники, найденные через rag_search
      - rag_search_history: list[dict] — история для anti-loop логики
      - pending_rag_searches — удаляет обработанные
    """
    messages = state.get("messages", [])
    pending = state.setdefault("pending_rag_searches", {})
    current_sources = state.setdefault("rag_found_sources", set())
    history = state.setdefault("rag_search_history", [])

    for msg in messages:
        if isinstance(msg, ToolMessage) and getattr(msg, "name", None) == "rag_search":
            tool_call_id = getattr(msg, "tool_call_id", None)

            # Получаем исходный запрос из pending
            query = None
            if tool_call_id and tool_call_id in pending:
                query = pending.pop(tool_call_id)

            # Извлекаем источники из response_metadata (всегда список)
            msg_sources: set[str] = set()
            if msg.response_metadata:
                sources_list = msg.response_metadata.get("sources", [])
                if isinstance(sources_list, list):
                    msg_sources = set(sources_list)

            # Добавляем только новые источники
            new_sources = msg_sources - current_sources
            current_sources.update(msg_sources)

            # Обновляем историю, если есть запрос
            if query:
                norm_query = _normalize_query(query)
                history.append({
                    "query": query,
                    "query_norm": norm_query,
                    "new_sources": len(new_sources),
                    "total_sources_after": len(current_sources),
                })

                # Ограничиваем размер истории
                if len(history) > MAX_RAG_HISTORY:
                    history.pop(0)

            log.debug(
                f"RAG ToolMessage обработан: источников={len(msg_sources)}, новых={len(new_sources)}"
            )


def _check_anti_loop_for_query(state: AgentState, query: str) -> bool:
    """Проверяет, не является ли запрос повторением с малым приростом.

    Args:
        state: Состояние агента
        query: Текущий запрос

    Returns:
        True если нужно предупредить о зацикливании
    """
    history = state.get("rag_search_history", [])
    norm_query = _normalize_query(query)

    # Проверяем последние 5 запросов
    recent = history[-5:] if len(history) > 5 else history

    for entry in recent:
        if _are_queries_semantically_similar(norm_query, entry["query_norm"]):
            # Если похожий запрос ранее дал мало новых источников (0-1)
            if entry["new_sources"] <= 1:
                log.warning(
                    f"Anti-loop: запрос '{query[:50]}' похож на предыдущий "
                    f"'{entry['query'][:50]}' с новыми источниками={entry['new_sources']}"
                )
                return True

    return False


def make_agent_node(
    llm: BaseChatModel | Runnable[Any, Any],
) -> Callable[[AgentState], Awaitable[dict[str, Any]]]:
    """Фабрика узла агента с привязанным LLM."""

    async def agent_node(state: AgentState) -> dict[str, Any]:
        # Инициализация полей состояния при первом вызове
        if "step_count" not in state:
            state["step_count"] = 0
            state["executed_actions"] = []
            state["need_retry"] = False
            state.setdefault("rag_found_sources", set())
            state.setdefault("pending_rag_searches", {})
            state.setdefault("rag_search_history", [])

        # Сброс флага retry
        state["need_retry"] = False

        # Инкремент счётчика шагов
        state["step_count"] += 1
        step = state["step_count"]

        # Проверка лимита шагов
        if step > MAX_STEPS:
            log.warning(f"Превышен лимит шагов: {step}/{MAX_STEPS}")
            limit_msg = AIMessage(
                content=f"Превышен лимит шагов ({MAX_STEPS}). Задача прервана. "
                        "Попробуйте разбить задачу на более мелкие части."
            )
            return {"messages": [limit_msg], "need_retry": False}

        # Обработка завершённых rag_search (обновляем статистику)
        _process_completed_rag_searches(state)

        log.info(f"Шаг агента #{step}")

        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT), *messages]
        response = await llm.ainvoke(messages)

        # Проверка на повторяющиеся tool calls
        if isinstance(response, AIMessage) and response.tool_calls:
            for tool_call in response.tool_calls:
                # Существующая проверка на exact duplicate
                args = tool_call.get("args", {})
                if isinstance(args, dict):
                    args_str = str(sorted(args.items()))
                else:
                    args_str = str(args)
                action_id = f"{tool_call['name']}:{args_str}"

                executed = state["executed_actions"]
                count = sum(1 for a in executed if a == action_id)

                if count >= MAX_REPEATS:
                    log.warning(f"Повторяющееся действие: {action_id} (x{count+1})")
                    state["need_retry"] = True
                    retry_warning = (
                        f"\n\n[Система: Обнаружено повторяющееся действие "
                        f"'{tool_call['name']}' (>={MAX_REPEATS} раз). "
                        "Пожалуйста, измените подход.]"
                    )
                    content_str = str(response.content) if response.content is not None else ""
                    new_content = content_str + retry_warning
                    response = AIMessage(
                        content=new_content,
                        tool_calls=response.tool_calls,
                    )

                executed.append(action_id)

                # Anti-loop логика для rag_search
                if tool_call["name"] == "rag_search":
                    query = args.get("query", "") if isinstance(args, dict) else ""
                    tool_call_id = tool_call.get("id")

                    if query and tool_call_id:
                        # Сохраняем запрос для последующей привязки к ToolMessage
                        pending = state.setdefault("pending_rag_searches", {})
                        pending[tool_call_id] = query

                        # Проверяем, не повторяется ли запрос с малым приростом источников
                        if _check_anti_loop_for_query(state, query):
                            state["need_retry"] = True
                            content_str = str(response.content) if response.content is not None else ""
                            warning_msg = (
                                "\n\n[Система: Похожий поисковый запрос ранее дал мало новых результатов. "
                                "Переформулируйте запрос или используйте list_documents для просмотра доступных файлов.]"
                            )
                            response = AIMessage(
                                content=content_str + warning_msg,
                                tool_calls=response.tool_calls,
                            )

        return {"messages": [response], "need_retry": state["need_retry"]}

    return agent_node


def parse_response_node(state: AgentState) -> dict[str, Any]:
    """Возвращает собранные источники и флаг need_retry.

    Источники берутся из response_metadata ToolMessage (sources list),
    который устанавливается rag_tool.
    """
    need_retry = state.get("need_retry", False)

    # Приоритет: используем уже собранный набор источников из состояния
    sources_set = state.get("rag_found_sources")
    if sources_set is not None:
        unique = sorted(sources_set)
        return {"sources": unique, "need_retry": need_retry}

    # Читаем из response_metadata всех ToolMessage rag_search
    sources: list[str] = []
    for msg in state["messages"]:
        if isinstance(msg, ToolMessage) and getattr(msg, "name", None) == "rag_search":
            # sources всегда в response_metadata
            meta_sources = msg.response_metadata.get("sources", []) if msg.response_metadata else []
            if isinstance(meta_sources, list):
                sources.extend(meta_sources)

    # Дедупликация с сохранением порядка
    seen: set[str] = set()
    unique = [s for s in sources if not (s in seen or seen.add(s))]  # type: ignore[func-returns-value]

    return {"sources": unique, "need_retry": need_retry}


def should_continue_after_parse(state: AgentState) -> str:
    """Определяет, нужно ли продолжить после parse_node.

    Если need_retry=True, возвращаемся к агенту для дополнительных шагов.
    Иначе завершаем граф.
    """
    from langgraph.graph import END

    return "agent" if state.get("need_retry", False) else END
