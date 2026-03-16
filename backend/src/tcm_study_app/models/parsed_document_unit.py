"""Structured parsed document unit model."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tcm_study_app.db.session import Base


class ParsedDocumentUnit(Base):
    """One structure-aware extraction unit derived from OCR blocks."""

    __tablename__ = "parsed_document_units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_document_id: Mapped[int] = mapped_column(
        ForeignKey("source_documents.id"),
        nullable=False,
    )
    page_number_start: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number_end: Mapped[int] = mapped_column(Integer, nullable=False)
    book_section: Mapped[str | None] = mapped_column(String(40), nullable=True)
    unit_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_heading: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    parser_version: Mapped[str] = mapped_column(String(40), default="clinical-acupuncture-v1")
    validation_state: Mapped[str] = mapped_column(String(30), default="valid")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    source_document: Mapped["SourceDocument"] = relationship(
        "SourceDocument",
        back_populates="parsed_units",
    )
    citations: Mapped[list["CardCitation"]] = relationship(
        "CardCitation",
        back_populates="parsed_document_unit",
    )

