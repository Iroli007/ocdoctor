"""Collection routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from tcm_study_app.core import get_subject_definition
from tcm_study_app.db import get_db
from tcm_study_app.models import StudyCollection, User
from tcm_study_app.schemas import CollectionCreateRequest, CollectionResponse

router = APIRouter(prefix="/api/collections", tags=["collections"])


def _ensure_user(db: Session, user_id: int) -> User:
    """Ensure a demo user exists for the given ID."""
    user = db.get(User, user_id)
    if user:
        return user

    user = User(
        id=user_id,
        email=f"demo{user_id}@example.com",
        name=f"Demo User {user_id}",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("", response_model=list[CollectionResponse])
async def list_collections(user_id: int = 1, db: Session = Depends(get_db)):
    """List collections for a user."""
    _ensure_user(db, user_id)
    collections = (
        db.query(StudyCollection)
        .filter(StudyCollection.user_id == user_id)
        .order_by(StudyCollection.created_at.desc())
        .all()
    )
    return collections


@router.post("", response_model=CollectionResponse)
async def create_collection(
    request: CollectionCreateRequest,
    db: Session = Depends(get_db),
):
    """Create a collection."""
    user = _ensure_user(db, request.user_id)
    collection = StudyCollection(
        user_id=user.id,
        title=request.title,
        subject=get_subject_definition(request.subject).display_name,
        description=request.description,
    )
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return collection
