"""Card request API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from tcm_study_app.db import get_db
from tcm_study_app.models import CardRequest, User
from tcm_study_app.schemas.card_schema import (
    CardRequestCreate,
    CardRequestResponse,
    CardRequestUpdate,
)

router = APIRouter(prefix="/api/card-requests", tags=["card-requests"])


def _ensure_user(db: Session, user_id: int) -> User:
    """Look up a user by ID; raise 404 if not found."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return user


@router.post("", response_model=CardRequestResponse)
async def create_card_request(
    request: CardRequestCreate,
    user_id: int = 1,
    db: Session = Depends(get_db),
):
    """Create a new card request."""
    _ensure_user(db, user_id)

    card_request = CardRequest(
        user_id=user_id,
        requested_name=request.requested_name,
        collection_id=request.collection_id,
        source_document_id=request.source_document_id,
        chapter_info=request.chapter_info,
        notes=request.notes,
        status="pending",
    )
    db.add(card_request)
    db.commit()
    db.refresh(card_request)
    return card_request


@router.get("", response_model=list[CardRequestResponse])
async def list_card_requests(
    user_id: int = 1,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    """List card requests for a user."""
    query = db.query(CardRequest).filter(CardRequest.user_id == user_id)
    if status:
        query = query.filter(CardRequest.status == status)
    return query.order_by(CardRequest.created_at.desc()).all()


@router.get("/{request_id}", response_model=CardRequestResponse)
async def get_card_request(
    request_id: int,
    user_id: int = 1,
    db: Session = Depends(get_db),
):
    """Get a single card request."""
    card_request = db.get(CardRequest, request_id)
    if not card_request:
        raise HTTPException(status_code=404, detail=f"Card request {request_id} not found")
    if card_request.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this request")
    return card_request


@router.patch("/{request_id}", response_model=CardRequestResponse)
async def update_card_request(
    request_id: int,
    request: CardRequestUpdate,
    user_id: int = 1,
    db: Session = Depends(get_db),
):
    """Update a card request (e.g., cancel it)."""
    card_request = db.get(CardRequest, request_id)
    if not card_request:
        raise HTTPException(status_code=404, detail=f"Card request {request_id} not found")
    if card_request.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this request")

    if request.status is not None:
        card_request.status = request.status
    if request.notes is not None:
        card_request.notes = request.notes

    db.commit()
    db.refresh(card_request)
    return card_request


@router.delete("/{request_id}")
async def delete_card_request(
    request_id: int,
    user_id: int = 1,
    db: Session = Depends(get_db),
):
    """Delete a card request."""
    card_request = db.get(CardRequest, request_id)
    if not card_request:
        raise HTTPException(status_code=404, detail=f"Card request {request_id} not found")
    if card_request.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this request")

    db.delete(card_request)
    db.commit()
    return {"status": "deleted", "request_id": request_id}
