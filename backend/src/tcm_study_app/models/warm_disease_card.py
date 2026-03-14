"""Warm disease card model - structured warm disease data."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tcm_study_app.db.session import Base


class WarmDiseaseCard(Base):
    """Warm disease card model."""

    __tablename__ = "warm_disease_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    knowledge_card_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_cards.id"), nullable=False, unique=True
    )
    pattern_name: Mapped[str] = mapped_column(String(100), nullable=False)
    stage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    syndrome: Mapped[str | None] = mapped_column(Text, nullable=True)
    treatment: Mapped[str | None] = mapped_column(Text, nullable=True)
    formula: Mapped[str | None] = mapped_column(Text, nullable=True)
    differentiation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    knowledge_card: Mapped["KnowledgeCard"] = relationship(
        "KnowledgeCard", back_populates="warm_disease_card"
    )
