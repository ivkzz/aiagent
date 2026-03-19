"""Фабрика LLM клиентов.

Единая точка создания LLM — провайдер задаётся через конфиг.
Для смены провайдера достаточно изменить переменные окружения.
"""

from langchain_openai import ChatOpenAI

from app.config import get_settings
from app.core.logger import get_logger

log = get_logger(__name__)


def create_llm(streaming: bool = False, temperature: float = 0.7, timeout: int = 60) -> ChatOpenAI:
    """Создаёт LLM клиент с настройками из конфигурации.

    Использует langchain-openai, который совместим с OpenRouter.
    Для смены провайдера — изменить OPENROUTER_BASE_URL и OPENROUTER_API_KEY.

    Args:
        streaming: Включить streaming режим (для SSE endpoint).
        temperature: Температура генерации (0.0 — детерминированно, 1.0 — творчески).
        timeout: Таймаут запроса в секундах (по умолчанию 60).

    Returns:
        Сконфигурированный ChatOpenAI клиент.
    """
    settings = get_settings()

    log.debug(
        f"Создание LLM: model={settings.llm_model}, streaming={streaming}, timeout={timeout}"
    )

    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        streaming=streaming,
        temperature=temperature,
        timeout=timeout,
        max_retries=2,
    )


def create_llm_with_structured_output(schema: type, streaming: bool = False, timeout: int = 60) -> object:
    """Создаёт LLM с привязанной Pydantic-схемой структурированного вывода.

    Args:
        schema: Pydantic модель для структурированного ответа.
        streaming: Включить streaming.
        timeout: Таймаут запроса в секундах.

    Returns:
        LLM с .with_structured_output(schema).
    """
    llm = create_llm(streaming=streaming, timeout=timeout)
    return llm.with_structured_output(schema)
