"""Document and template schemas."""
from datetime import datetime

from pydantic import BaseModel


class DocumentChunkResponse(BaseModel):
    """Response schema for a parsed document chunk."""

    id: int
    page_number: int
    chunk_index: int
    heading: str | None = None
    content: str


class DocumentResponse(BaseModel):
    """Response schema for an imported document."""

    id: int
    collection_id: int
    type: str
    status: str
    file_name: str
    preview: str | None = None
    page_count: int
    chunk_count: int
    created_at: datetime


class DocumentDetailResponse(DocumentResponse):
    """Detailed document response with parsed chunks."""

    chunks: list[DocumentChunkResponse]


class CardTemplateResponse(BaseModel):
    """Response schema for card templates."""

    key: str
    subject_key: str
    label: str
    description: str
    fields: list[str]


class CollectionExportResponse(BaseModel):
    """Export payload for a collection."""

    filename: str
    content: str
