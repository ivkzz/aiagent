"""Тесты Фазы 3: Google Sheets интеграция.

Все тесты изолированы от реального Google API через monkeypatch/MagicMock.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from app.schemas.sheets import SheetLogEntry

# ---------------------------------------------------------------------------
# Тесты SheetLogEntry схемы
# ---------------------------------------------------------------------------


def test_sheet_log_entry_to_row() -> None:
    """to_row() возвращает список из 5 элементов в правильном порядке."""
    ts = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    entry = SheetLogEntry(
        timestamp=ts,
        thread_id="thread-1",
        user_message="Вопрос",
        agent_response="Ответ",
        sources=["doc.pdf", "readme.md"],
    )
    row = entry.to_row()

    assert len(row) == 5
    assert row[0] == ts.isoformat()
    assert row[1] == "thread-1"
    assert row[2] == "Вопрос"
    assert row[3] == "Ответ"
    assert "doc.pdf" in row[4]
    assert "readme.md" in row[4]


def test_sheet_log_entry_to_row_empty_sources() -> None:
    """to_row() с пустыми sources возвращает пустую строку в колонке sources."""
    entry = SheetLogEntry(
        thread_id="t",
        user_message="q",
        agent_response="a",
        sources=[],
    )
    row = entry.to_row()
    assert row[4] == ""


def test_sheet_log_entry_headers() -> None:
    """headers() возвращает 5 заголовков в правильном порядке."""
    headers = SheetLogEntry.headers()
    assert headers == ["timestamp", "thread_id", "user_message", "agent_response", "sources"]


# ---------------------------------------------------------------------------
# Тесты google_sheets.py клиента
# ---------------------------------------------------------------------------


def test_get_sheets_client_raises_if_no_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """SheetsAuthError если service_account.json не существует."""
    from app.core.exceptions import SheetsAuthError
    from app.integrations import google_sheets

    monkeypatch.setattr(
        "app.integrations.google_sheets.get_settings",
        lambda: MagicMock(
            google_service_account_file=str(tmp_path / "missing.json"),
            google_spreadsheet_id="sheet-id",
        ),
    )
    google_sheets._get_sheets_client.cache_clear()

    with pytest.raises(SheetsAuthError, match="не найден"):
        google_sheets._get_sheets_client()

    google_sheets._get_sheets_client.cache_clear()


def test_get_sheets_client_raises_on_auth_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """SheetsAuthError если авторизация gspread упала."""
    from app.core.exceptions import SheetsAuthError
    from app.integrations import google_sheets

    key_file = tmp_path / "sa.json"
    key_file.write_text("{}")

    monkeypatch.setattr(
        "app.integrations.google_sheets.get_settings",
        lambda: MagicMock(
            google_service_account_file=str(key_file),
            google_spreadsheet_id="sheet-id",
        ),
    )
    monkeypatch.setattr(
        "app.integrations.google_sheets.Credentials.from_service_account_file",
        MagicMock(side_effect=Exception("invalid json")),
    )
    google_sheets._get_sheets_client.cache_clear()

    with pytest.raises(SheetsAuthError, match="Ошибка авторизации"):
        google_sheets._get_sheets_client()

    google_sheets._get_sheets_client.cache_clear()


def test_get_or_create_worksheet_creates_sheet_if_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Если лист DialogLog не найден — создаётся новый с заголовками."""
    import gspread

    from app.integrations import google_sheets

    mock_worksheet = MagicMock()
    mock_worksheet.row_count = 1
    mock_worksheet.get.return_value = [["timestamp"]]  # заголовки уже есть

    mock_spreadsheet = MagicMock()
    mock_spreadsheet.worksheet.side_effect = gspread.WorksheetNotFound
    mock_spreadsheet.add_worksheet.return_value = mock_worksheet

    mock_client = MagicMock()
    mock_client.open_by_key.return_value = mock_spreadsheet

    monkeypatch.setattr(
        "app.integrations.google_sheets._get_sheets_client",
        lambda: mock_client,
    )
    monkeypatch.setattr(
        "app.integrations.google_sheets.get_settings",
        lambda: MagicMock(google_spreadsheet_id="sheet-id"),
    )

    worksheet = google_sheets._get_or_create_worksheet()

    mock_spreadsheet.add_worksheet.assert_called_once_with(
        title="DialogLog", rows=1000, cols=5
    )
    mock_worksheet.append_row.assert_called_once_with(SheetLogEntry.headers())
    assert worksheet is mock_worksheet


def test_get_or_create_worksheet_raises_on_missing_spreadsheet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SheetsWriteError если таблица не найдена."""
    import gspread

    from app.core.exceptions import SheetsWriteError
    from app.integrations import google_sheets

    mock_client = MagicMock()
    mock_client.open_by_key.side_effect = gspread.SpreadsheetNotFound

    monkeypatch.setattr(
        "app.integrations.google_sheets._get_sheets_client",
        lambda: mock_client,
    )
    monkeypatch.setattr(
        "app.integrations.google_sheets.get_settings",
        lambda: MagicMock(google_spreadsheet_id="bad-id"),
    )

    with pytest.raises(SheetsWriteError, match="не найдена"):
        google_sheets._get_or_create_worksheet()


# ---------------------------------------------------------------------------
# Тесты log_dialog_entry (async)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_log_dialog_entry_calls_append_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """log_dialog_entry вызывает append_row с правильными данными."""
    from app.integrations import google_sheets

    mock_worksheet = MagicMock()
    monkeypatch.setattr(
        "app.integrations.google_sheets._get_or_create_worksheet",
        lambda: mock_worksheet,
    )

    entry = SheetLogEntry(
        thread_id="t-1",
        user_message="Вопрос",
        agent_response="Ответ",
        sources=["file.pdf"],
    )
    await google_sheets.log_dialog_entry(entry)

    mock_worksheet.append_row.assert_called_once()
    call_args = mock_worksheet.append_row.call_args[0][0]
    assert call_args[1] == "t-1"
    assert call_args[2] == "Вопрос"
    assert call_args[3] == "Ответ"


@pytest.mark.asyncio
async def test_log_dialog_entry_raises_sheets_write_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """log_dialog_entry оборачивает неожиданные ошибки в SheetsWriteError."""
    from app.core.exceptions import SheetsWriteError
    from app.integrations import google_sheets

    monkeypatch.setattr(
        "app.integrations.google_sheets._get_or_create_worksheet",
        MagicMock(side_effect=RuntimeError("connection refused")),
    )

    entry = SheetLogEntry(
        thread_id="t",
        user_message="q",
        agent_response="a",
    )
    with pytest.raises(SheetsWriteError, match="connection refused"):
        await google_sheets.log_dialog_entry(entry)
