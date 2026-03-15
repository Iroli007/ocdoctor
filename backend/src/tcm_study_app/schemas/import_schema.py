"""Import schemas."""
from pydantic import BaseModel


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


class OCRResultRequest(BaseModel):
    """Request schema for editing OCR result."""

    document_id: int
    corrected_text: str
