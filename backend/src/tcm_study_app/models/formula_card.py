"""Formula card model - TCM formula specific structured data."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tcm_study_app.db.session import Base


class FormulaCard(Base):
    """Formula card model - structured formula data."""

    __tablename__ = "formula_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    knowledge_card_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_cards.id"), nullable=False, unique=True
    )
    formula_name: Mapped[str] = mapped_column(String(100), nullable=False)
    composition: Mapped[str | None] = mapped_column(Text, nullable=True)
    effect: Mapped[str | None] = mapped_column(Text, nullable=True)
    indication: Mapped[str | None] = mapped_column(Text, nullable=True)
    pathogenesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    usage_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    memory_tip: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    knowledge_card: Mapped["KnowledgeCard"] = relationship(
        "KnowledgeCard", back_populates="formula_card"
    )
