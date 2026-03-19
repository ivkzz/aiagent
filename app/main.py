"""Точка входа FastAPI приложения.

Конфигурирует middleware, подключает роутеры и настраивает логирование.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.agent.graph import init_agent_graph
from app.api.routes import chat, documents, health
from app.api.routes.export import router as export_router
from app.config import get_settings
from app.core.exceptions import AIAgentError
from app.core.logger import get_logger, setup_logger
from app.integrations.google_sheets import _get_sheets_client
from app.rag.embeddings import get_embeddings
from app.rag.vectorstore import get_vectorstore

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Жизненный цикл приложения."""
    settings = get_settings()
    setup_logger(level=settings.log_level, json_logs=settings.log_json)
    log.info(f"AI Agent запускается: model={settings.llm_model}, port={settings.api_port}")

    get_embeddings()  # прогрев embeddings
    get_vectorstore()  # прогрев Chroma
    _get_sheets_client()  # прогрев кеша и проверка авторизации
    init_agent_graph()

    yield

    log.info("AI Agent останавливается")


def create_app() -> FastAPI:
    """Фабрика FastAPI приложения.

    Разделение создания и запуска позволяет удобно тестировать app.
    """
    app = FastAPI(
        title="AI Agent API",
        description="Эталонный шаблон AI-агента с RAG, LangGraph и Google Sheets",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # --- CORS ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # В production заменить на список разрешённых origin
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Глобальный exception handler ---
    @app.exception_handler(AIAgentError)
    async def agent_error_handler(request: Request, exc: AIAgentError) -> JSONResponse:
        log.error(f"AgentError на {request.url}: {exc}")
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    # --- Роутеры ---
    app.include_router(health.router)
    app.include_router(chat.router, prefix="/chat")
    app.include_router(documents.router, prefix="/documents")
    app.include_router(export_router, prefix="/export")

    return app


app = create_app()
