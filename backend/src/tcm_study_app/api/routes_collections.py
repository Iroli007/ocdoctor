"""Collection routes."""
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from tcm_study_app.core import get_subject_definition
from tcm_study_app.db import get_db
from tcm_study_app.models import KnowledgeCard, StudyCollection, User
from tcm_study_app.schemas import (
    CollectionCreateRequest,
    CollectionExportResponse,
    CollectionResponse,
)

router = APIRouter(prefix="/api/collections", tags=["collections"])


def _ensure_user(db: Session, user_id: int) -> User:
    """Look up a user by ID; raise 404 if not found."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return user


@router.get("", response_model=list[CollectionResponse])
async def list_collections(db: Session = Depends(get_db)):
    """List all collections (visible to every user)."""
    collections = (
        db.query(StudyCollection)
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


@router.delete("/{collection_id}")
async def delete_collection(collection_id: int, db: Session = Depends(get_db)):
    """Delete a collection and all of its dependent learning data."""
    collection = db.get(StudyCollection, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail=f"Collection {collection_id} not found")

    title = collection.title
    db.delete(collection)
    db.commit()
    return {"status": "deleted", "collection_id": collection_id, "title": title}


@router.get("/{collection_id}/export", response_model=CollectionExportResponse)
async def export_collection(collection_id: int, db: Session = Depends(get_db)):
    """Export one collection as Markdown."""
    collection = db.get(StudyCollection, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail=f"Collection {collection_id} not found")

    cards = (
        db.query(KnowledgeCard)
        .filter(KnowledgeCard.collection_id == collection_id)
        .order_by(KnowledgeCard.created_at.asc())
        .all()
    )

    lines = [
        f"# {collection.title}",
        "",
        f"- 学科：{collection.subject_display_name}",
        f"- 说明：{collection.description or '无'}",
        "",
    ]

    for card in cards:
        normalized = {}
        if card.normalized_content_json:
            try:
                normalized = json.loads(card.normalized_content_json)
            except json.JSONDecodeError:
                normalized = {}

        lines.append(f"## {card.title}")
        lines.append("")
        for key, value in normalized.items():
            if not value or key in {"template_key", "template_label"}:
                continue
            lines.append(f"- **{key}**：{value}")
        if card.citations:
            lines.append("")
            lines.append("### 引用")
            for citation in card.citations:
                document_name = Path(
                    citation.source_document.image_url or f"文档-{citation.source_document_id}"
                ).name
                lines.append(
                    f"- {document_name} · 第 {citation.page_number} 页：{citation.quote[:180]}"
                )
        lines.append("")

    filename = f"{collection.title.replace(' ', '-')}.md"
    return CollectionExportResponse(filename=filename, content="\n".join(lines))
