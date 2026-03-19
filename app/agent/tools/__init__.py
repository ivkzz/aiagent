"""Инструменты LangGraph агента.

Экспортирует:
- get_tools() — полный список доступных инструментов
- set_retriever(), get_retriever() — управление RAGRetriever'ом
"""

from langchain_core.tools import BaseTool

from app.agent.tools.document_tools import list_documents
from app.agent.tools.history_tools import (
    get_conversation_history,
    get_conversation_summary,
    get_recent_messages,
)
from app.agent.tools.rag_tool import get_retriever, rag_search, set_retriever
from app.agent.tools.sheets_tool import (
    sheets_list,
    sheets_write,
    sheets_write_rows,
    write_structured_data,
)


def get_tools() -> list[BaseTool]:
    """Возвращает список инструментов агента.

    Returns:
        Полный список инструментов: RAG, Google Sheets, история диалога, список документов.
    """
    return [
        list_documents,
        rag_search,
        sheets_list,
        sheets_write,
        sheets_write_rows,
        write_structured_data,
        get_conversation_history,
        get_recent_messages,
        get_conversation_summary,
    ]


__all__ = [
    "get_tools",
    "set_retriever",
    "get_retriever",
    "rag_search",
    "list_documents",
    "sheets_list",
    "sheets_write",
    "sheets_write_rows",
    "write_structured_data",
    "get_conversation_history",
    "get_recent_messages",
    "get_conversation_summary",
]
