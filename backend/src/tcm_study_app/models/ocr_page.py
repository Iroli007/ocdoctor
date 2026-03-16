"""OCR page model."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tcm_study_app.db.session import Base


class OCRPage(Base):
    """One OCR-imported page with coarse layout classification."""

    __tablename__ = "ocr_pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_document_id: Mapped[int] = mapped_column(
        ForeignKey("source_documents.id"),
        nullable=False,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    page_kind: Mapped[str] = mapped_column(String(20), default="prose")
    book_section: Mapped[str | None] = mapped_column(String(40), nullable=True)
    quality_flags: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    source_document: Mapped["SourceDocument"] = relationship(
        "SourceDocument",
        back_populates="ocr_pages",
    )
    blocks: Mapped[list["OCRBlock"]] = relationship(
        "OCRBlock",
        back_populates="ocr_page",
        cascade="all, delete-orphan",
    )

