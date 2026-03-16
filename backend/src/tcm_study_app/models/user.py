"""User model."""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tcm_study_app.db.session import Base


class User(Base):
    """User model."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    collections: Mapped[list["StudyCollection"]] = relationship(
        "StudyCollection", back_populates="user", cascade="all, delete-orphan"
    )
    review_records: Mapped[list["ReviewRecord"]] = relationship(
        "ReviewRecord", back_populates="user", cascade="all, delete-orphan"
    )
    card_requests: Mapped[list["CardRequest"]] = relationship(
        "CardRequest", back_populates="user", cascade="all, delete-orphan"
    )
