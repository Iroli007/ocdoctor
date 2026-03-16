"""Document library routes."""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from tcm_study_app.db import get_db
from tcm_study_app.schemas import (
    DocumentChunkResponse,
    DocumentDetailResponse,
    DocumentResponse,
    OCRBlockResponse,
    OCRPageResponse,
    ParsedDocumentUnitResponse,
)
from tcm_study_app.services import create_document_library

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _serialize_document(document) -> DocumentResponse:
    """Serialize a source document into API response form."""
    file_name = Path(document.image_url or f"文档-{document.id}").name
    chunks = list(document.chunks)
    return DocumentResponse(
        id=document.id,
        collection_id=document.collection_id,
        type=document.type,
        status=document.status,
        file_name=file_name,
        source_book_key=document.source_book_key,
        book_section=document.book_section,
        parser_version=document.parser_version,
        preview=(document.raw_text or "")[:180] or None,
        page_count=max((chunk.page_number for chunk in chunks), default=0),
        chunk_count=len(chunks),
        parsed_unit_count=len(document.parsed_units),
        created_at=document.created_at,
    )


@router.get("", response_model=list[DocumentResponse])
async def get_documents(
    collection_id: int = Query(..., description="Collection ID"),
    db: Session = Depends(get_db),
):
    """List documents in a collection."""
    library = create_document_library(db)
    try:
        documents = library.get_documents(collection_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [_serialize_document(document) for document in documents]


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(document_id: int, db: Session = Depends(get_db)):
    """Fetch one document with its parsed chunks."""
    library = create_document_library(db)
    try:
        document = library.get_document(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    payload = _serialize_document(document)
    return DocumentDetailResponse(
        **payload.model_dump(),
        chunks=[
            DocumentChunkResponse(
                id=chunk.id,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                heading=chunk.heading,
                content=chunk.content,
            )
            for chunk in document.chunks
        ],
        ocr_pages=[
            OCRPageResponse(
                id=page.id,
                page_number=page.page_number,
                page_kind=page.page_kind,
                book_section=page.book_section,
                quality_flags=page.quality_flags,
                raw_text=page.raw_text,
                blocks=[
                    OCRBlockResponse(
                        id=block.id,
                        block_type=block.block_type,
                        text=block.text,
                        sequence_no=block.sequence_no,
                    )
                    for block in page.blocks
                ],
            )
            for page in sorted(document.ocr_pages, key=lambda item: item.page_number)
        ],
        parsed_units=[
            ParsedDocumentUnitResponse(
                id=unit.id,
                page_number_start=unit.page_number_start,
                page_number_end=unit.page_number_end,
                book_section=unit.book_section,
                unit_type=unit.unit_type,
                source_heading=unit.source_heading,
                source_text=unit.source_text,
                sequence_no=unit.sequence_no,
                parser_version=unit.parser_version,
                validation_state=unit.validation_state,
            )
            for unit in sorted(document.parsed_units, key=lambda item: item.sequence_no)
        ],
    )


@router.delete("/{document_id}")
async def delete_document(document_id: int, db: Session = Depends(get_db)):
    """Delete one document and all learning data generated from it."""
    library = create_document_library(db)
    try:
        document = library.delete_document(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "status": "deleted",
        "document_id": document_id,
        "file_name": Path(document.image_url or f"文档-{document.id}").name,
    }
