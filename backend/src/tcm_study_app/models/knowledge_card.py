"""Knowledge card model."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tcm_study_app.db.session import Base


class KnowledgeCard(Base):
    """Knowledge card model - core learning card."""

    __tablename__ = "knowledge_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    collection_id: Mapped[int] = mapped_column(
        ForeignKey("study_collections.id"), nullable=False
    )
    source_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_documents.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), default="formula"
    )  # formula / comparison / quiz_basis
    raw_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_content_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    collection: Mapped["StudyCollection"] = relationship(
        "StudyCollection", back_populates="knowledge_cards"
    )
    source_document: Mapped["SourceDocument"] = relationship(
        "SourceDocument", back_populates="knowledge_cards"
    )
    formula_card: Mapped["FormulaCard"] = relationship(
        "FormulaCard",
        back_populates="knowledge_card",
        uselist=False,
        cascade="all, delete-orphan",
        single_parent=True,
    )
    acupuncture_card: Mapped["AcupunctureCard"] = relationship(
        "AcupunctureCard",
        back_populates="knowledge_card",
        uselist=False,
        cascade="all, delete-orphan",
        single_parent=True,
    )
    acupoint_knowledge_card: Mapped["AcupointKnowledgeCard"] = relationship(
        "AcupointKnowledgeCard",
        back_populates="knowledge_card",
        uselist=False,
        cascade="all, delete-orphan",
        single_parent=True,
    )
    needling_technique_card: Mapped["NeedlingTechniqueCard"] = relationship(
        "NeedlingTechniqueCard",
        back_populates="knowledge_card",
        uselist=False,
        cascade="all, delete-orphan",
        single_parent=True,
    )
    condition_treatment_card: Mapped["ConditionTreatmentCard"] = relationship(
        "ConditionTreatmentCard",
        back_populates="knowledge_card",
        uselist=False,
        cascade="all, delete-orphan",
        single_parent=True,
    )
    warm_disease_card: Mapped["WarmDiseaseCard"] = relationship(
        "WarmDiseaseCard",
        back_populates="knowledge_card",
        uselist=False,
        cascade="all, delete-orphan",
        single_parent=True,
    )
    citations: Mapped[list["CardCitation"]] = relationship(
        "CardCitation",
        back_populates="knowledge_card",
        cascade="all, delete-orphan",
    )
