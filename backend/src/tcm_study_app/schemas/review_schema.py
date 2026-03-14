"""Review schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SubmitReviewRequest(BaseModel):
    """Request schema for submitting review."""

    user_id: int
    target_type: str  # card / quiz / comparison
    target_id: int
    result: str  # correct / wrong / skipped
    response: str | None = None


class ReviewRecordResponse(BaseModel):
    """Response schema for review record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    target_type: str
    target_id: int
    result: str
    response: str | None = None
    reviewed_at: datetime


class ReviewStats(BaseModel):
    """Review statistics schema."""

    total_reviews: int
    correct_count: int
    wrong_count: int
    skipped_count: int
    accuracy: float
