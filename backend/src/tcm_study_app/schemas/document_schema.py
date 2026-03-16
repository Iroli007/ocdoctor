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


class OCRBlockResponse(BaseModel):
    """Response schema for an OCR block."""

    id: int
    block_type: str
    text: str
    sequence_no: int


class OCRPageResponse(BaseModel):
    """Response schema for an OCR page."""

    id: int
    page_number: int
    page_kind: str
    book_section: str | None = None
    quality_flags: str | None = None
    raw_text: str
    blocks: list[OCRBlockResponse] = []


class ParsedDocumentUnitResponse(BaseModel):
    """Response schema for a parsed document unit."""

    id: int
    page_number_start: int
    page_number_end: int
    book_section: str | None = None
    unit_type: str
    source_heading: str | None = None
    source_text: str
    sequence_no: int
    parser_version: str
    validation_state: str


class DocumentResponse(BaseModel):
    """Response schema for an imported document."""

    id: int
    collection_id: int
    type: str
    status: str
    file_name: str
    source_book_key: str | None = None
    book_section: str | None = None
    parser_version: str | None = None
    preview: str | None = None
    page_count: int
    chunk_count: int
    parsed_unit_count: int = 0
    created_at: datetime


class DocumentDetailResponse(DocumentResponse):
    """Detailed document response with parsed chunks."""

    chunks: list[DocumentChunkResponse]
    ocr_pages: list[OCRPageResponse] = []
    parsed_units: list[ParsedDocumentUnitResponse] = []


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
