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
        "KnowledgeCard", back_populates="source_document"
    )
