"""Per-user card importance (star rating) model."""
from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from tcm_study_app.db.session import Base


class UserCardImportance(Base):
    """Stores each user's independent star-rating for a card."""

    __tablename__ = "user_card_importance"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    card_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("knowledge_cards.id", ondelete="CASCADE"), primary_key=True
    )
    importance_level: Mapped[int] = mapped_column(Integer, default=0)
