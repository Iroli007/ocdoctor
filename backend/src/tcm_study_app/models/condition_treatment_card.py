"""Condition treatment card model."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tcm_study_app.db.session import Base


class ConditionTreatmentCard(Base):
    """Structured typed record for acupuncture condition-treatment cards."""

    __tablename__ = "condition_treatment_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    knowledge_card_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_cards.id"),
        nullable=False,
        unique=True,
    )
    disease_name: Mapped[str] = mapped_column(String(100), nullable=False)
    pattern_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    treatment_principle: Mapped[str | None] = mapped_column(Text, nullable=True)
    acupoint_prescription: Mapped[str | None] = mapped_column(Text, nullable=True)
    modifications: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    knowledge_card: Mapped["KnowledgeCard"] = relationship(
        "KnowledgeCard",
        back_populates="condition_treatment_card",
    )
