"""Needling technique card model."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tcm_study_app.db.session import Base


class NeedlingTechniqueCard(Base):
    """Structured typed record for needling-technique cards."""

    __tablename__ = "needling_technique_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    knowledge_card_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_cards.id"),
        nullable=False,
        unique=True,
    )
    technique_name: Mapped[str] = mapped_column(String(100), nullable=False)
    section_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    definition_or_scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_points: Mapped[str | None] = mapped_column(Text, nullable=True)
    indications: Mapped[str | None] = mapped_column(Text, nullable=True)
    contraindications: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    knowledge_card: Mapped["KnowledgeCard"] = relationship(
        "KnowledgeCard",
        back_populates="needling_technique_card",
    )

