"""Контекстные переменные для передачи данных между узлами графа."""

import contextvars

# thread_id текущего запроса
thread_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "thread_id", default=None
)

# Compiled graph instance (для повторного использования в инструментах, избегая новых SQLite connections)
graph_var: contextvars.ContextVar[object | None] = contextvars.ContextVar(
    "graph", default=None
)
