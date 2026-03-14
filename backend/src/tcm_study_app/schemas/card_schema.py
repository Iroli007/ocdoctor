"""Card schemas."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class FormulaCardData(BaseModel):
    """Formula card data schema."""

    formula_name: str
    composition: str | None = None
    effect: str | None = None
    indication: str | None = None
    pathogenesis: str | None = None
    usage_notes: str | None = None
    memory_tip: str | None = None


class KnowledgeCardCreate(BaseModel):
    """Request schema for creating knowledge card."""

    collection_id: int
    source_document_id: int | None = None
    title: str
    category: str = "formula"
    raw_excerpt: str | None = None
    normalized_content: dict[str, Any]


class KnowledgeCardResponse(BaseModel):
    """Response schema for knowledge card."""

    id: int
    title: str
    category: str
    raw_excerpt: str | None = None
    formula_card: FormulaCardData | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class GenerateCardsRequest(BaseModel):
    """Request schema for generating cards from document."""

    document_id: int


class GenerateCardsResponse(BaseModel):
    """Response schema for generating cards."""

    cards: list[KnowledgeCardResponse]
    status: str
