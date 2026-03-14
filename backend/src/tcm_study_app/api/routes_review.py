"""Review routes."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from tcm_study_app.db import get_db
from tcm_study_app.schemas import (
    SubmitReviewRequest,
    ReviewRecordResponse,
    ReviewStats,
)
from tcm_study_app.services import create_review_service

router = APIRouter(prefix="/api/reviews", tags=["review"])


@router.post("/submit", response_model=ReviewRecordResponse)
async def submit_review(request: SubmitReviewRequest, db: Session = Depends(get_db)):
    """Submit a review result."""
    service = create_review_service(db)
    record = service.submit_review(
        user_id=request.user_id,
        target_type=request.target_type,
        target_id=request.target_id,
        result=request.result,
        response=request.response,
    )

    return ReviewRecordResponse(
        id=record.id,
        target_type=record.target_type,
        target_id=record.target_id,
        result=record.result,
        response=record.response,
        reviewed_at=record.reviewed_at,
    )


@router.get("/stats/{user_id}", response_model=ReviewStats)
async def get_review_stats(user_id: int, db: Session = Depends(get_db)):
    """Get review statistics for a user."""
    service = create_review_service(db)
    stats = service.get_review_stats(user_id)

    return ReviewStats(
        total_reviews=stats["total_reviews"],
        correct_count=stats["correct_count"],
        wrong_count=stats["wrong_count"],
        skipped_count=stats["skipped_count"],
        accuracy=stats["accuracy"],
    )


@router.get("/due/{user_id}")
async def get_due_items(
    user_id: int,
    collection_id: int | None = Query(None, description="Collection ID"),
    db: Session = Depends(get_db),
):
    """Get items due for review."""
    service = create_review_service(db)
    items = service.get_due_items(user_id, collection_id)

    return {
        "items": [
            {
                "id": item.id,
                "title": item.title,
                "type": "card",
            }
            for item in items
        ]
    }


@router.get("/wrong/{user_id}")
async def get_wrong_items(
    user_id: int,
    collection_id: int | None = Query(None, description="Collection ID"),
    db: Session = Depends(get_db),
):
    """Get items that were answered wrong."""
    service = create_review_service(db)
    records = service.get_wrong_items(user_id, collection_id)

    return {
        "items": [
            {
                "id": record.target_id,
                "type": record.target_type,
                "result": record.result,
                "reviewed_at": record.reviewed_at.isoformat(),
            }
            for record in records
        ]
    }
