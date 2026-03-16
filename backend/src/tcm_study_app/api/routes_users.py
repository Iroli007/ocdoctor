"""User routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from tcm_study_app.db import get_db
from tcm_study_app.models import User

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("")
async def list_users(db: Session = Depends(get_db)):
    """Return all users (id + name only)."""
    users = db.query(User).order_by(User.id).all()
    return [{"id": u.id, "name": u.name} for u in users]
