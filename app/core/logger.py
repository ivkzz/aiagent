"""Централизованная обёртка над loguru.

Единая точка конфигурации логирования для всего приложения.
Использовать get_logger(__name__) в каждом модуле.
"""

import sys
from typing import Any

from loguru import logger


def setup_logger(level: str = "INFO", json_logs: bool = False) -> None:
    """Настраивает глобальный логгер приложения.

    Вызывается один раз при старте приложения в lifespan.

    Args:
        level: Уровень логирования (DEBUG/INFO/WARNING/ERROR/CRITICAL).
        json_logs: Если True — вывод в JSON формате (для production / log-агрегаторов).
    """
    logger.remove()  # Удаляем все дефолтные хендлеры

    if json_logs:
        # JSON формат — для Loki, ELK, CloudWatch и т.п.
        logger.add(
            sys.stdout,
            level=level,
            serialize=True,
            backtrace=False,
            diagnose=False,
        )
    else:
        # Читаемый формат для разработки
        logger.add(
            sys.stdout,
            level=level,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{extra[module]}</cyan> | "
                "<level>{message}</level>"
            ),
            colorize=True,
            backtrace=True,
            diagnose=True,
        )

    # Ротация файлов — всегда, независимо от формата
    logger.add(
        "logs/app.log",
        level=level,
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        serialize=True,  # файл всегда в JSON
        backtrace=True,
        diagnose=False,  # без дампа переменных в файл (безопасность)
    )


def get_logger(module: str) -> Any:
    """Возвращает логгер, привязанный к конкретному модулю.

    Args:
        module: Имя модуля, обычно __name__.

    Returns:
        Loguru logger с контекстом module.

    Пример:
        log = get_logger(__name__)
        log.info("Документ загружен")
    """
    return logger.bind(module=module)
