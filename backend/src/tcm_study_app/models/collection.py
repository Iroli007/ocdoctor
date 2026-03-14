"""Study collection model."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tcm_study_app.core.subjects import get_subject_definition
from tcm_study_app.db.session import Base


class StudyCollection(Base):
    """Study collection model (e.g., 方剂学-解表剂)."""

    __tablename__ = "study_collections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(100), default="方剂学")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="collections")
    source_documents: Mapped[list["SourceDocument"]] = relationship(
        "SourceDocument", back_populates="collection", cascade="all, delete-orphan"
    )
    knowledge_cards: Mapped[list["KnowledgeCard"]] = relationship(
        "KnowledgeCard", back_populates="collection", cascade="all, delete-orphan"
    )
    comparison_items: Mapped[list["ComparisonItem"]] = relationship(
        "ComparisonItem", back_populates="collection", cascade="all, delete-orphan"
    )
    quizzes: Mapped[list["Quiz"]] = relationship(
        "Quiz", back_populates="collection", cascade="all, delete-orphan"
    )

    @property
    def subject_key(self) -> str:
        """Return the normalized subject key for API consumers."""
        return get_subject_definition(self.subject).key

    @property
    def subject_display_name(self) -> str:
        """Return the display name for the stored subject."""
        return get_subject_definition(self.subject).display_name
