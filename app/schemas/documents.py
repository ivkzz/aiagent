"""Pydantic схемы для загрузки и индексации документов."""

from datetime import datetime
from pydantic import BaseModel, Field


class IngestResponse(BaseModel):
    """Ответ на запрос индексации документов."""

    status: str = Field("ok", description="Статус операции")
    documents_processed: int = Field(..., description="Количество обработанных файлов")
    chunks_added: int = Field(..., description="Количество chunks добавленных в vector store")
    errors: list[str] = Field(
        default_factory=list,
        description="Список ошибок при обработке отдельных файлов",
    )


class DocumentInfo(BaseModel):
    """Информация об отдельном документе при индексации."""

    filename: str = Field(..., description="Имя файла")
    chunks: int = Field(..., description="Количество chunks из файла")
    status: str = Field("processed", description="Статус: 'processed' | 'error'")
    error: str | None = Field(None, description="Сообщение об ошибке, если status='error'")


class DocumentMetadata(BaseModel):
    """Метаданные документа для отображения в списке."""

    filename: str = Field(..., description="Имя файла")
    chunks: int = Field(..., description="Количество chunks файла в векторной базе")
    file_type: str | None = Field(None, description="Расширение файла (например, .pdf)")
    uploaded_at: datetime | None = Field(None, description="Дата первой индексации файла")
