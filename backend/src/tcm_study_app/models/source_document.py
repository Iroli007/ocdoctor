"""Source document model."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tcm_study_app.db.session import Base


class SourceDocument(Base):
    """Source document model - imported content source."""

    __tablename__ = "source_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    collection_id: Mapped[int] = mapped_column(
        ForeignKey("study_collections.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(20), default="text")  # text / image
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_book_key: Mapped[str | None] = mapped_column(String(50), nullable=True)
    book_section: Mapped[str | None] = mapped_column(String(40), nullable=True)
    section_confidence: Mapped[str | None] = mapped_column(String(20), nullable=True)
    parser_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    ocr_engine: Mapped[str | None] = mapped_column(String(50), nullable=True)
    has_layout_blocks: Mapped[bool] = mapped_column(default=False)
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending / processed / failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    collection: Mapped["StudyCollection"] = relationship(
        "StudyCollection", back_populates="source_documents"
    )
    knowledge_cards: Mapped[list["KnowledgeCard"]] = relationship(
        "KnowledgeCard",
        back_populates="source_document",
        cascade="all, delete-orphan",
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="source_document",
        cascade="all, delete-orphan",
    )
    ocr_pages: Mapped[list["OCRPage"]] = relationship(
        "OCRPage",
        back_populates="source_document",
        cascade="all, delete-orphan",
    )
    parsed_units: Mapped[list["ParsedDocumentUnit"]] = relationship(
        "ParsedDocumentUnit",
        back_populates="source_document",
        cascade="all, delete-orphan",
    )
    citations: Mapped[list["CardCitation"]] = relationship(
        "CardCitation",
        back_populates="source_document",
        cascade="all, delete-orphan",
    )
