"""OCR block model."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tcm_study_app.db.session import Base


class OCRBlock(Base):
    """One OCR-derived block within a page."""

    __tablename__ = "ocr_blocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ocr_page_id: Mapped[int] = mapped_column(ForeignKey("ocr_pages.id"), nullable=False)
    block_type: Mapped[str] = mapped_column(String(30), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    ocr_page: Mapped["OCRPage"] = relationship(
        "OCRPage",
        back_populates="blocks",
    )

