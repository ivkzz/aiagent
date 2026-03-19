"""Обновлённый endpoint загрузки документов — подключает реальный RAG pipeline."""

import tempfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import verify_api_key
from app.core.exceptions import DocumentIngestError, DocumentLoadError
from app.core.logger import get_logger
from app.rag.chunker import split_documents
from app.rag.loader import load_document
from app.rag.vectorstore import add_documents, delete_by_source, get_vectorstore
from app.schemas.documents import DocumentInfo, DocumentMetadata, IngestResponse

log = get_logger(__name__)
router = APIRouter()

ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".html", ".csv"}


@router.post("/ingest", response_model=IngestResponse, dependencies=[Depends(verify_api_key)])
async def ingest_documents(
    files: list[UploadFile] = File(..., description="Файлы для индексации"),
) -> IngestResponse:
    """Загружает и индексирует документы в Chroma vector store.

    Pipeline: загрузка файла → load_document → split_documents → add_documents (Chroma).
    Формат .pdf обрабатывается постранично через PyPDFLoader.

    Args:
        files: Список файлов через multipart/form-data.

    Returns:
        Результат с количеством обработанных файлов и chunks.
    """
    log.info(f"Получено файлов для индексации: {len(files)}")

    results: list[DocumentInfo] = []
    total_chunks = 0

    for upload_file in files:
        filename = upload_file.filename or "unknown"
        extension = Path(filename).suffix.lower()

        if extension not in ALLOWED_EXTENSIONS:
            results.append(
                DocumentInfo(
                    filename=filename,
                    chunks=0,
                    status="error",
                    error=f"Формат '{extension}' не поддерживается. "
                    f"Допустимые: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
                )
            )
            continue

        tmp_path: Path | None = None
        try:
            # Сохраняем в временный файл с правильным расширением
            content = await upload_file.read()
            with tempfile.NamedTemporaryFile(
                suffix=extension, delete=False
            ) as tmp:
                tmp.write(content)
                tmp_path = Path(tmp.name)

            # RAG pipeline
            docs = load_document(tmp_path)
            # Устанавливаем оригинальное имя файла в source (не tmp-путь)
            for doc in docs:
                doc.metadata["source"] = filename

            chunks = split_documents(docs)

            # Добавляем дату индексации в метаданные каждого chunk
            now_str = datetime.now().isoformat()
            for chunk in chunks:
                chunk.metadata["uploaded_at"] = now_str

            chunk_count = add_documents(chunks)

            results.append(
                DocumentInfo(filename=filename, chunks=chunk_count, status="processed")
            )
            total_chunks += chunk_count
            log.info(f"✓ {filename}: {chunk_count} chunks")

        except (DocumentLoadError, DocumentIngestError) as exc:
            log.error(f"✗ {filename}: {exc}")
            results.append(
                DocumentInfo(filename=filename, chunks=0, status="error", error=str(exc))
            )
        except Exception as exc:
            log.exception(f"Неожиданная ошибка при обработке {filename}")
            results.append(
                DocumentInfo(
                    filename=filename,
                    chunks=0,
                    status="error",
                    error=f"Внутренняя ошибка: {exc}",
                )
            )
        finally:
            if tmp_path:
                tmp_path.unlink(missing_ok=True)

    errors = [f"{r.filename}: {r.error}" for r in results if r.error]
    processed_count = len([r for r in results if r.status == "processed"])

    return IngestResponse(
        documents_processed=processed_count,
        chunks_added=total_chunks,
        errors=errors,
    )


@router.get("/list", response_model=list[DocumentMetadata], dependencies=[Depends(verify_api_key)])
async def list_documents() -> list[DocumentMetadata]:
    """Возвращает список всех уникальных файлов в векторной базе.

    Группирует chunks по полю metadata['source'] и считает количество.
    Также извлекает file_type и uploaded_at из метаданных (если присутствуют).

    Returns:
        Список DocumentMetadata отсортированный по имени файла.
    """
    vectorstore = get_vectorstore()

    try:
        # Получаем только метаданные (без документов и embeddings) — экономит память
        result = vectorstore.get(include=["metadatas"])
        metadatas = result.get("metadatas", [])

        # Группируем по source
        groups = defaultdict(list)
        for meta in metadatas:
            if not meta:
                continue
            source = meta.get("source")
            if source:
                groups[source].append(meta)

        # Формируем ответ
        documents: list[DocumentMetadata] = []
        for source, meta_list in groups.items():
            # Определяем file_type из первого попавшегося metadata
            file_type = meta_list[0].get("file_type") if meta_list else None

            # Пытаемся получить uploaded_at (ISO строка или datetime)
            uploaded_at = None
            for meta in meta_list:
                if "uploaded_at" in meta:
                    val = meta["uploaded_at"]
                    if isinstance(val, datetime):
                        uploaded_at = val
                        break
                    try:
                        uploaded_at = datetime.fromisoformat(str(val))
                        break
                    except (ValueError, TypeError):
                        pass

            documents.append(
                DocumentMetadata(
                    filename=source,
                    chunks=len(meta_list),
                    file_type=file_type,
                    uploaded_at=uploaded_at,
                )
            )

        # Сортируем по имени файла
        documents.sort(key=lambda d: d.filename.lower())

        log.info(f"list_documents: найдено {len(documents)} уникальных источников")
        return documents

    except Exception as exc:
        log.error(f"Ошибка получения списка документов: {exc}")
        raise


@router.delete("/{filename}", dependencies=[Depends(verify_api_key)])
async def delete_document(filename: str) -> dict[str, str]:
    """Удаляет все chunks документа из векторной базы.

    Args:
        filename: Имя файла (должно совпадать с metadata['source']).

    Returns:
        {"status": "deleted", "filename": filename}
    """
    delete_by_source(filename)
    log.info(f"Документ удалён: {filename}")
    return {"status": "deleted", "filename": filename}
