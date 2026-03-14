"""Review record model."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tcm_study_app.db.session import Base


class ReviewRecord(Base):
    """Review record model - for tracking review history."""

    __tablename__ = "review_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    target_type: Mapped[str] = mapped_column(
        String(20)
    )  # card / quiz / comparison
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    result: Mapped[str] = mapped_column(
        String(20)
    )  # correct / wrong / skipped
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="review_records")
