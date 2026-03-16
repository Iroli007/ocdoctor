"""Import schemas."""
from pydantic import BaseModel, Field


class ImportTextRequest(BaseModel):
    """Request schema for importing text."""

    collection_id: int
    text: str


class ImportTextResponse(BaseModel):
    """Response schema for importing text."""

    document_id: int
    status: str
    chunk_count: int = 0
    page_count: int = 0


class ImportImageRequest(BaseModel):
    """Request schema for importing image."""

    collection_id: int
    # Image is sent as file upload, this is just metadata


class ImportImageResponse(BaseModel):
    """Response schema for importing image."""

    document_id: int
    ocr_text: str | None = None
    status: str


class ImportPdfResponse(BaseModel):
    """Response schema for importing PDF."""

    document_id: int
    status: str
    chunk_count: int
    page_count: int
    book_section: str | None = None
    parsed_unit_count: int = 0
    page_kind_breakdown: dict[str, int] = {}
    unit_breakdown: dict[str, int] = {}


class OCRPageInput(BaseModel):
    """One OCR-extracted page payload."""

    page_number: int = Field(..., ge=1)
    text: str = ""


class ImportOcrPagesRequest(BaseModel):
    """Request schema for importing OCR page text from a scanned PDF."""

    collection_id: int
    file_name: str
    pages: list[OCRPageInput] = Field(..., min_length=1)


class OCRResultRequest(BaseModel):
    """Request schema for editing OCR result."""

    document_id: int
    corrected_text: str
