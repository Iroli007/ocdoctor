"""Document import routes."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from tcm_study_app.db import get_db
from tcm_study_app.schemas import (
    ImportOcrPagesRequest,
    ImportPdfResponse,
    ImportTextRequest,
    ImportTextResponse,
)
from tcm_study_app.services import create_document_library

router = APIRouter(prefix="/api/import", tags=["import"])

MAX_PDF_UPLOAD_BYTES = 4 * 1024 * 1024


def _page_kind_breakdown(document) -> dict[str, int]:
    counts: dict[str, int] = {}
    for page in document.ocr_pages:
        counts[page.page_kind] = counts.get(page.page_kind, 0) + 1
    return counts


def _unit_breakdown(document) -> dict[str, int]:
    counts: dict[str, int] = {}
    for unit in document.parsed_units:
        counts[unit.unit_type] = counts.get(unit.unit_type, 0) + 1
    return counts


@router.post("/text", response_model=ImportTextResponse)
async def import_text(request: ImportTextRequest, db: Session = Depends(get_db)):
    """Import plain text into the knowledge library."""
    library = create_document_library(db)
    try:
        document = library.import_text_document(request.collection_id, request.text)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc

    return ImportTextResponse(
        document_id=document.id,
        status=document.status,
        chunk_count=len(document.chunks),
        page_count=max((chunk.page_number for chunk in document.chunks), default=0),
    )


@router.post("/pdf", response_model=ImportPdfResponse)
async def import_pdf(
    collection_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Import a PDF and build document chunks for later card generation."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file")

    content = await file.read()
    if len(content) > MAX_PDF_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                "PDF 文件过大。当前网页上传路径仅支持 4 MB 以内 PDF；"
                "更大的文件请先压缩/拆分，或改成直传对象存储后再解析。"
            ),
        )
    library = create_document_library(db)
    try:
        document = library.import_pdf_document(collection_id, file.filename, content)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc

    return ImportPdfResponse(
        document_id=document.id,
        status=document.status,
        chunk_count=len(document.chunks),
        page_count=max((chunk.page_number for chunk in document.chunks), default=0),
        book_section=document.book_section,
        parsed_unit_count=len(document.parsed_units),
        page_kind_breakdown=_page_kind_breakdown(document),
        unit_breakdown=_unit_breakdown(document),
    )


@router.post("/ocr-pages", response_model=ImportPdfResponse)
async def import_ocr_pages(
    request: ImportOcrPagesRequest,
    db: Session = Depends(get_db),
):
    """Import OCR page text generated locally from a scanned PDF."""
    library = create_document_library(db)
    try:
        document = library.import_ocr_document(
            request.collection_id,
            request.file_name,
            request.pages,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc

    return ImportPdfResponse(
        document_id=document.id,
        status=document.status,
        chunk_count=len(document.chunks),
        page_count=max((page.page_number for page in request.pages), default=0),
        book_section=document.book_section,
        parsed_unit_count=len(document.parsed_units),
        page_kind_breakdown=_page_kind_breakdown(document),
        unit_breakdown=_unit_breakdown(document),
    )
