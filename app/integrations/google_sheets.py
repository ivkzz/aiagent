"""Google Sheets интеграция — запись логов диалогов.

Использует gspread с аутентификацией через Service Account (JSON файл).
Все операции асинхронны через run_in_executor (gspread — синхронный клиент).

Лист "DialogLog" структура:
| A: timestamp | B: thread_id | C: user_message | D: agent_response | E: sources |

First row — заголовки (создаются автоматически если лист пустой).
"""

import asyncio
from functools import lru_cache
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

from app.config import get_settings
from app.core.exceptions import SheetsAuthError, SheetsWriteError
from app.core.logger import get_logger
from app.schemas.sheets import SheetLogEntry

log = get_logger(__name__)

_SHEET_NAME = "DialogLog"
_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


@lru_cache(maxsize=1)
def _get_sheets_client() -> gspread.Client:
    """Создаёт авторизованный gspread клиент (кешируется).

    Raises:
        SheetsAuthError: Если файл service account не найден или невалиден.
    """
    settings = get_settings()
    key_path = Path(settings.google_service_account_file)

    if not key_path.exists():
        raise SheetsAuthError(
            f"Service Account файл не найден: {key_path}. "
            "Положите credentials/service_account.json"
        )

    try:
        creds = Credentials.from_service_account_file(str(key_path), scopes=_SCOPES)  # type: ignore[no-untyped-call]
        client = gspread.authorize(creds)
        log.info("Google Sheets клиент авторизован")
        return client
    except Exception as exc:
        raise SheetsAuthError(f"Ошибка авторизации Google Sheets: {exc}") from exc


def _get_or_create_worksheet() -> gspread.Worksheet:
    """Возвращает или создаёт лист DialogLog в таблице.

    Если лист пустой — добавляет строку заголовков.

    Returns:
        gspread.Worksheet готовый для записи.
    """
    settings = get_settings()
    client = _get_sheets_client()

    try:
        spreadsheet = client.open_by_key(settings.google_spreadsheet_id)
    except gspread.SpreadsheetNotFound as exc:
        raise SheetsWriteError(
            f"Таблица с ID={settings.google_spreadsheet_id} не найдена. "
            "Проверьте GOOGLE_SPREADSHEET_ID и права доступа."
        ) from exc

    try:
        worksheet = spreadsheet.worksheet(_SHEET_NAME)
    except gspread.WorksheetNotFound:
        # Создаём лист с заголовками
        worksheet = spreadsheet.add_worksheet(title=_SHEET_NAME, rows=1000, cols=5)
        worksheet.append_row(SheetLogEntry.headers())
        log.info(f"Создан лист {_SHEET_NAME} с заголовками")

    # Если лист существует но пустой — добавляем заголовки
    if worksheet.row_count == 0 or not worksheet.get("A1:E1"):
        worksheet.insert_row(SheetLogEntry.headers(), index=1)

    return worksheet


def get_sheet_names() -> list[str]:
    """Возвращает названия всех листов таблицы.

    Returns:
        Список названий листов.

    Raises:
        SheetsWriteError: Если не удалось получить список.
    """
    settings = get_settings()
    client = _get_sheets_client()

    try:
        spreadsheet = client.open_by_key(settings.google_spreadsheet_id)
        return [ws.title for ws in spreadsheet.worksheets()]
    except gspread.SpreadsheetNotFound as exc:
        raise SheetsWriteError(
            f"Таблица с ID={settings.google_spreadsheet_id} не найдена."
        ) from exc
    except Exception as exc:
        raise SheetsWriteError(f"Ошибка получения списка листов: {exc}") from exc


async def get_sheet_names_async() -> list[str]:
    """Асинхронно возвращает названия всех листов таблицы.

    Raises:
        SheetsWriteError: Если не удалось получить список.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, get_sheet_names)


async def write_to_sheet(sheet_name: str, row: list[str]) -> None:
    """Асинхронно записывает произвольную строку в указанный лист таблицы.

    Если лист не существует — создаёт его автоматически.

    Args:
        sheet_name: Название листа в таблице.
        row: Список значений для записи в строку.

    Raises:
        SheetsWriteError: Если запись не удалась.
    """

    def _sync_write() -> None:
        settings = get_settings()
        client = _get_sheets_client()

        try:
            spreadsheet = client.open_by_key(settings.google_spreadsheet_id)
        except gspread.SpreadsheetNotFound as exc:
            raise SheetsWriteError(
                f"Таблица с ID={settings.google_spreadsheet_id} не найдена."
            ) from exc

        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
            log.info(f"Создан лист '{sheet_name}'")

        worksheet.append_row(row, value_input_option="USER_ENTERED")  # type: ignore[arg-type]
        log.debug(f"Записана строка в лист '{sheet_name}': {row}")

    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _sync_write)
    except SheetsWriteError:
        raise
    except Exception as exc:
        raise SheetsWriteError(f"Ошибка записи в Google Sheets: {exc}") from exc


async def write_rows_to_sheet(sheet_name: str, rows: list[list[str]]) -> None:
    """Асинхронно записывает несколько строк в указанный лист таблицы.

    Если лист не существует — создаёт его автоматически.

    Args:
        sheet_name: Название листа в таблице.
        rows: Список списков, где каждый внутренний список — это строка таблицы.

    Raises:
        SheetsWriteError: Если запись не удалась.
    """

    def _sync_write() -> None:
        settings = get_settings()
        client = _get_sheets_client()

        try:
            spreadsheet = client.open_by_key(settings.google_spreadsheet_id)
        except gspread.SpreadsheetNotFound as exc:
            raise SheetsWriteError(
                f"Таблица с ID={settings.google_spreadsheet_id} не найдена."
            ) from exc

        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
            log.info(f"Создан лист '{sheet_name}'")

        # gspread поддерживает append_rows
        worksheet.append_rows(rows, value_input_option="USER_ENTERED")  # type: ignore[arg-type]
        log.debug(f"Записано {len(rows)} строк в лист '{sheet_name}'")

    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _sync_write)
    except SheetsWriteError:
        raise
    except Exception as exc:
        raise SheetsWriteError(f"Ошибка записи в Google Sheets: {exc}") from exc


async def log_dialog_entry(entry: SheetLogEntry) -> None:
    """Асинхронно записывает строку диалога в Google Sheets.

    gspread — синхронная библиотека, выполняется в thread pool executor
    чтобы не блокировать event loop FastAPI.

    Args:
        entry: Структурированная запись диалога.

    Raises:
        SheetsWriteError: Если запись не удалась.
    """

    def _sync_write() -> None:
        """Синхронная запись — выполняется в executor."""
        worksheet = _get_or_create_worksheet()
        worksheet.append_row(
            entry.to_row(),
            value_input_option="USER_ENTERED",  # type: ignore[arg-type]
        )
        log.debug(
            f"Записан диалог: thread_id={entry.thread_id}, "
            f"timestamp={entry.timestamp.isoformat()}"
        )

    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _sync_write)
    except SheetsWriteError:
        raise
    except Exception as exc:
        raise SheetsWriteError(f"Ошибка записи в Google Sheets: {exc}") from exc
