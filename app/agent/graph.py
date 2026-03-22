"""LangGraph граф AI-агента.

Граф строится один раз при старте через init_agent_graph().
SQLite checkpointer открывается новым соединением на каждый запрос —
aiosqlite не поддерживает повторный запуск потока.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from app.agent.nodes import make_agent_node, parse_response_node, should_continue_after_parse
from app.agent.state import AgentState
from app.agent.tools import get_tools, set_retriever
from app.config import get_settings
from app.core.llm_factory import create_llm
from app.core.logger import get_logger
from app.rag.retriever import RAGRetriever, get_rag_config

log = get_logger(__name__)

# Некомпилированный граф — создаётся один раз, компилируется с checkpointer на каждый запрос
_uncompiled_graph: StateGraph[AgentState] | None = None


def _should_continue(state: AgentState) -> str:
    messages = state.get("messages", [])
    if not messages:
        return END
    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


def init_agent_graph() -> None:
    """Строит граф без checkpointer.

    Вызывать один раз в lifespan FastAPI.
    Инициализирует RAGRetriever для multi-query поиска.
    """
    global _uncompiled_graph

    tools = get_tools()
    llm = create_llm(streaming=True).bind_tools(tools)

    # Инициализируем RAGRetriever с LLM для multi-query
    rag_config = get_rag_config()
    rag_retriever = RAGRetriever(llm=llm, config=rag_config)

    # Устанавливаем глобальный ретризер для rag_tool
    set_retriever(rag_retriever)

    log.info(
        f"RAGRetriever инициализирован: multi_query={rag_config.multi_query_enabled}, "
        f"dedup_threshold={rag_config.dedup_similarity_threshold}"
    )

    graph: StateGraph[AgentState] = StateGraph(AgentState)
    graph.add_node("agent", make_agent_node(llm))  # type: ignore[call-overload]
    graph.add_node("tools", ToolNode(tools))
    graph.add_node("parse", parse_response_node)

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", _should_continue, {"tools": "tools", END: "parse"})
    graph.add_edge("tools", "agent")
    graph.add_conditional_edges("parse", should_continue_after_parse, {"agent": "agent", END: END})

    _uncompiled_graph = graph
    log.info("LangGraph граф инициализирован")


@asynccontextmanager
async def get_graph() -> AsyncIterator[Any]:
    """Открывает новое SQLite соединение и компилирует граф для одного запроса.

    Raises:
        RuntimeError: Если init_agent_graph() не был вызван.
    """
    if _uncompiled_graph is None:
        raise RuntimeError("Граф не инициализирован. Вызовите init_agent_graph() в lifespan.")

    settings = get_settings()
    async with AsyncSqliteSaver.from_conn_string(settings.sqlite_path) as checkpointer:
        yield _uncompiled_graph.compile(checkpointer=checkpointer)
