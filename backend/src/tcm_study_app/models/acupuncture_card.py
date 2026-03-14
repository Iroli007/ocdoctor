"""Acupuncture card model - structured acupuncture data."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tcm_study_app.db.session import Base


class AcupunctureCard(Base):
    """Acupuncture card model."""

    __tablename__ = "acupuncture_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    knowledge_card_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_cards.id"), nullable=False, unique=True
    )
    acupoint_name: Mapped[str] = mapped_column(String(100), nullable=False)
    meridian: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    indication: Mapped[str | None] = mapped_column(Text, nullable=True)
    technique: Mapped[str | None] = mapped_column(Text, nullable=True)
    caution: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    knowledge_card: Mapped["KnowledgeCard"] = relationship(
        "KnowledgeCard", back_populates="acupuncture_card"
    )
