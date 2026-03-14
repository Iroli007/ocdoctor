"""Quiz model."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tcm_study_app.db.session import Base


class Quiz(Base):
    """Quiz model - quiz questions."""

    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    collection_id: Mapped[int] = mapped_column(
        ForeignKey("study_collections.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(
        String(20), default="choice"
    )  # choice / true_false / recall
    question: Mapped[str] = mapped_column(Text, nullable=False)
    options_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer: Mapped[str] = mapped_column(String(10), nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[str] = mapped_column(
        String(20), default="medium"
    )  # easy / medium / hard
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    collection: Mapped["StudyCollection"] = relationship(
        "StudyCollection", back_populates="quizzes"
    )
