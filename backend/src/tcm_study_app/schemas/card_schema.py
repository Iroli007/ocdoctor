"""Card schemas."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class FormulaCardData(BaseModel):
    """Formula card data schema."""

    formula_name: str
    composition: str | None = None
    effect: str | None = None
    indication: str | None = None
    pathogenesis: str | None = None
    usage_notes: str | None = None
    memory_tip: str | None = None


class AcupunctureCardData(BaseModel):
    """Acupuncture card data schema."""

    acupoint_name: str
    meridian: str | None = None
    location: str | None = None
    indication: str | None = None
    technique: str | None = None
    caution: str | None = None


class WarmDiseaseCardData(BaseModel):
    """Warm disease card data schema."""

    pattern_name: str
    stage: str | None = None
    syndrome: str | None = None
    treatment: str | None = None
    formula: str | None = None
    differentiation: str | None = None


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

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    template_key: str
    subject: str
    subject_key: str
    subject_display_name: str
    category: str
    source_document_id: int | None = None
    source_document_name: str | None = None
    importance_level: int = 0
    raw_excerpt: str | None = None
    normalized_content: dict[str, Any] | None = None
    citations: list["CardCitationResponse"]
    formula_card: FormulaCardData | None = None
    acupuncture_card: AcupunctureCardData | None = None
    warm_disease_card: WarmDiseaseCardData | None = None
    created_at: datetime


class GenerateCardsRequest(BaseModel):
    """Request schema for generating cards from document."""

    document_id: int
    template_key: str


class GenerateCardsResponse(BaseModel):
    """Response schema for generating cards."""

    cards: list[KnowledgeCardResponse]
    status: str


class SetCardImportanceRequest(BaseModel):
    """Request schema for updating card importance."""

    importance_level: int


class SubjectResponse(BaseModel):
    """Response schema for supported subjects."""

    key: str
    display_name: str
    entity_label: str


class CardCitationResponse(BaseModel):
    """Response schema for a card citation."""

    id: int
    page_number: int
    quote: str
    document_name: str


KnowledgeCardResponse.model_rebuild()
