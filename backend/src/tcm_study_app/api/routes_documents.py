"""Document library routes."""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from tcm_study_app.db import get_db
from tcm_study_app.schemas import (
    DocumentChunkResponse,
    DocumentDetailResponse,
    DocumentResponse,
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
        preview=(document.raw_text or "")[:180] or None,
        page_count=max((chunk.page_number for chunk in chunks), default=0),
        chunk_count=len(chunks),
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
