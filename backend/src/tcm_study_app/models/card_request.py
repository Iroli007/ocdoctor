"""Card request model - user requests for new cards."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tcm_study_app.db.session import Base


class CardRequest(Base):
    """User requests for new cards to be created from documents."""

    __tablename__ = "card_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    collection_id: Mapped[int | None] = mapped_column(
        ForeignKey("study_collections.id"), nullable=True
    )
    source_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_documents.id"), nullable=True
    )
    requested_name: Mapped[str] = mapped_column(String(255), nullable=False)
    chapter_info: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="card_requests")
    collection: Mapped["StudyCollection"] = relationship("StudyCollection")
    source_document: Mapped["SourceDocument"] = relationship("SourceDocument")
