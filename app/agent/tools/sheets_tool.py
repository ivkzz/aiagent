"""Sheets Tool — инструмент агента для записи данных в Google Sheets."""

from typing import Any

from langchain_core.tools import tool

from app.core.exceptions import SheetsError
from app.core.logger import get_logger
from app.integrations.google_sheets import (
    get_sheet_names_async,
    write_rows_to_sheet,
    write_to_sheet,
)

log = get_logger(__name__)


@tool
async def sheets_list() -> str:
    """Возвращает список существующих листов в Google Sheets.

    Используй этот инструмент перед записью, чтобы узнать в какой лист
    записать данные, если пользователь не указал название явно.

    Returns:
        Перечисление названий листов или сообщение об ошибке.
    """
    try:
        names = await get_sheet_names_async()
        if not names:
            return "В таблице пока нет листов."
        return "Существующие листы: " + ", ".join(f"'{n}'" for n in names)
    except SheetsError as exc:
        log.warning(f"Не удалось получить список листов: {exc}")
        return f"Ошибка получения списка листов: {exc}"


@tool
async def sheets_write(sheet_name: str, values: list[str]) -> str:
    """Записывает строку данных в указанный лист Google Sheets.

    Используй этот инструмент когда пользователь просит записать,
    сохранить или добавить данные в таблицу.
    Если лист не существует — он будет создан автоматически.

    Args:
        sheet_name: Название листа в таблице (например "Задачи", "Отчёт").
        values: Список значений для записи в строку таблицы.

    Returns:
        Подтверждение записи или сообщение об ошибке.
    """
    try:
        await write_to_sheet(sheet_name, values)
        log.info(f"Записана строка в лист '{sheet_name}': {values}")
        return f"Данные успешно записаны в лист '{sheet_name}'"
    except SheetsError as exc:
        log.warning(f"Не удалось записать в Sheets: {exc}")
        return f"Ошибка записи в Google Sheets: {exc}"


@tool
async def sheets_write_rows(sheet_name: str, rows: list[list[str]]) -> str:
    """Записывает несколько строк данных в указанный лист Google Sheets.

    Используй, когда нужно записать много строк за один раз.
    Если лист не существует — он будет создан автоматически.

    Args:
        sheet_name: Название листа в таблице (например "Задачи", "Отчёт").
        rows: Список строк, каждая строка — список значений.

    Returns:
        Подтверждение записи или сообщение об ошибке.
    """
    if not rows:
        return "Нет данных для записи."
    try:
        await write_rows_to_sheet(sheet_name, rows)
        log.info(f"Записано {len(rows)} строк в лист '{sheet_name}'")
        return f"Успешно записано {len(rows)} строк в лист '{sheet_name}'"
    except SheetsError as exc:
        log.warning(f"Не удалось записать строки в Sheets: {exc}")
        return f"Ошибка записи в Google Sheets: {exc}"


@tool
async def write_structured_data(sheet_name: str, data: list[dict[str, Any]]) -> str:
    """Записывает структурированные данные (список словарей) в лист.

    Автоматически извлекает заголовки из ключей первого словаря.
    Используй для записи табличных данных с колонками.

    Args:
        sheet_name: Название листа в таблице.
        data: Список словарей, где каждый словарь — одна запись.

    Returns:
        Подтверждение записи или сообщение об ошибке.
    """
    if not data:
        return "Нет данных для записи."

    # Преобразуем список словарей в строки таблицы
    headers = list(data[0].keys())
    rows = [headers]
    for item in data:
        row = [str(item.get(h, "")) for h in headers]
        rows.append(row)

    try:
        # Вызываем функцию записи нескольких строк напрямую
        from app.integrations.google_sheets import write_rows_to_sheet

        await write_rows_to_sheet(sheet_name, rows)
        log.info(f"Записано {len(data)} записей структурированных данных в лист '{sheet_name}'")
        return f"Успешно записано {len(data)} записей в лист '{sheet_name}'"
    except Exception as exc:
        log.warning(f"Не удалось записать структурированные данные: {exc}")
        return f"Ошибка записи в Google Sheets: {exc}"
