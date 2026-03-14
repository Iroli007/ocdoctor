"""Comparison item model."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tcm_study_app.db.session import Base


class ComparisonItem(Base):
    """Comparison item model - for comparing similar formulas."""

    __tablename__ = "comparison_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    collection_id: Mapped[int] = mapped_column(
        ForeignKey("study_collections.id"), nullable=False
    )
    left_entity: Mapped[str] = mapped_column(String(100), nullable=False)
    right_entity: Mapped[str] = mapped_column(String(100), nullable=False)
    comparison_points_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    question_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    collection: Mapped["StudyCollection"] = relationship(
        "StudyCollection", back_populates="comparison_items"
    )
