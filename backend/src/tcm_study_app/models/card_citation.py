"""Card citation model."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tcm_study_app.db.session import Base


class CardCitation(Base):
    """A citation that ties a card back to the source document."""

    __tablename__ = "card_citations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    knowledge_card_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_cards.id"),
        nullable=False,
    )
    source_document_id: Mapped[int] = mapped_column(
        ForeignKey("source_documents.id"),
        nullable=False,
    )
    document_chunk_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_chunks.id"),
        nullable=True,
    )
    parsed_document_unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("parsed_document_units.id"),
        nullable=True,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    knowledge_card: Mapped["KnowledgeCard"] = relationship(
        "KnowledgeCard",
        back_populates="citations",
    )
    source_document: Mapped["SourceDocument"] = relationship(
        "SourceDocument",
        back_populates="citations",
    )
    document_chunk: Mapped["DocumentChunk"] = relationship(
        "DocumentChunk",
        back_populates="citations",
    )
    parsed_document_unit: Mapped["ParsedDocumentUnit"] = relationship(
        "ParsedDocumentUnit",
        back_populates="citations",
    )
