"""Collection schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CollectionCreateRequest(BaseModel):
    """Request schema for creating a collection."""

    title: str
    subject: str
    description: str | None = None
    user_id: int = 1


class CollectionResponse(BaseModel):
    """Response schema for a study collection."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    subject: str
    subject_key: str
    subject_display_name: str
    description: str | None = None
    created_at: datetime
