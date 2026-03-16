"""Card routes."""
import json
import logging
from pathlib import Path
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from tcm_study_app.core import get_subject_definition
from tcm_study_app.db import get_db
from tcm_study_app.models import KnowledgeCard, StudyCollection, User
from tcm_study_app.models.user_card_importance import UserCardImportance
from tcm_study_app.schemas import (
    AcupunctureCardData,
    CardCitationResponse,
    FormulaCardData,
    GenerateCardsRequest,
    GenerateCardsResponse,
    KnowledgeCardResponse,
    SetCardImportanceRequest,
    WarmDiseaseCardData,
)
from tcm_study_app.services import create_card_generator
from tcm_study_app.services.acupuncture_card_cleanup import (
    clean_acupuncture_card_payload,
    is_valid_acupuncture_card_payload,
)
from tcm_study_app.services.card_pool import select_weighted_card_batch
from tcm_study_app.services.clinical_card_cleanup import (
    clean_clinical_card_payload,
    is_valid_clinical_card_payload,
    normalize_clinical_title_key,
)

router = APIRouter(prefix="/api/cards", tags=["cards"])

logger = logging.getLogger(__name__)

_IMPORTANCE_MIGRATED = False


def _ensure_user(db: Session, user_id: int) -> User:
    """Look up a user by ID; raise 404 if not found."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return user


def _load_normalized_content(card: KnowledgeCard) -> tuple[dict | None, str]:
    """Decode card JSON content and extract template metadata.

    Returns (normalized_content_dict, template_key).
    importance_level is no longer stored in the JSON.
    """
    normalized_content = None
    template_key = card.category

    if card.normalized_content_json:
        try:
            normalized_content = json.loads(card.normalized_content_json)
            template_key = normalized_content.get("template_key", card.category)
            normalized_content = {
                key: value
                for key, value in normalized_content.items()
                if key != "importance_level"
            }
        except (json.JSONDecodeError, TypeError, ValueError):
            normalized_content = None

    return normalized_content, template_key


def _get_importance(db: Session, user_id: int, card_id: int) -> int:
    """Look up the per-user importance level for a card."""
    row = db.get(UserCardImportance, (user_id, card_id))
    return row.importance_level if row else 0


def _clinical_source_text(card: KnowledgeCard) -> str:
    """Build a best-effort source snippet for clinical card cleanup."""
    parts = [card.raw_excerpt or ""]
    parts.extend(citation.quote for citation in card.citations if citation.quote)
    unique_parts: list[str] = []
    seen_parts: set[str] = set()
    for part in parts:
        normalized = part.strip()
        if not normalized or normalized in seen_parts:
            continue
        seen_parts.add(normalized)
        unique_parts.append(normalized)
    return "\n\n".join(unique_parts)


def _serialize_card(
    card: KnowledgeCard, db: Session, user_id: int
) -> KnowledgeCardResponse | None:
    """Convert a model into the API response shape."""
    formula_data = None
    acupuncture_data = None
    warm_disease_data = None

    if card.formula_card:
        fp = card.formula_card
        formula_data = FormulaCardData(
            formula_name=fp.formula_name,
            composition=fp.composition,
            effect=fp.effect,
            indication=fp.indication,
            pathogenesis=fp.pathogenesis,
            usage_notes=fp.usage_notes,
            memory_tip=fp.memory_tip,
        )

    if card.acupuncture_card:
        ap = card.acupuncture_card
        acupuncture_data = AcupunctureCardData(
            acupoint_name=ap.acupoint_name,
            meridian=ap.meridian,
            location=ap.location,
            indication=ap.indication,
            technique=ap.technique,
            caution=ap.caution,
        )

    if card.warm_disease_card:
        wd = card.warm_disease_card
        warm_disease_data = WarmDiseaseCardData(
            pattern_name=wd.pattern_name,
            stage=wd.stage,
            syndrome=wd.syndrome,
            treatment=wd.treatment,
            formula=wd.formula,
            differentiation=wd.differentiation,
        )

    subject = get_subject_definition(card.collection.subject if card.collection else None)
    normalized_content, template_key = _load_normalized_content(card)
    importance_level = _get_importance(db, user_id, card.id)
    title = card.title

    source_document_name = None
    if card.source_document:
        source_document_name = Path(
            card.source_document.image_url or f"文档-{card.source_document.id}"
        ).name

    if template_key == "clinical_treatment":
        cleaned = clean_clinical_card_payload(
            {
                "disease_name": (normalized_content or {}).get("disease_name") or card.title,
                "treatment_principle": (normalized_content or {}).get("treatment_principle"),
                "acupoint_prescription": (normalized_content or {}).get("acupoint_prescription"),
                "notes": (normalized_content or {}).get("notes"),
            },
            source_text=_clinical_source_text(card),
        )
        if not is_valid_clinical_card_payload(cleaned):
            return None
        title = cleaned["disease_name"]
        normalized_content = {
            "template_key": template_key,
            "template_label": (normalized_content or {}).get("template_label", "病证治疗卡"),
            **cleaned,
        }
    elif template_key in {"acupoint_foundation", "acupoint_review"}:
        cleaned = clean_acupuncture_card_payload(
            {
                "acupoint_name": (normalized_content or {}).get("acupoint_name") or card.title,
                "meridian": (normalized_content or {}).get("meridian"),
                "location": (normalized_content or {}).get("location"),
                "indication": (normalized_content or {}).get("indication"),
                "technique": (normalized_content or {}).get("technique"),
                "caution": (normalized_content or {}).get("caution"),
            },
            source_text=_clinical_source_text(card),
        )
        if not is_valid_acupuncture_card_payload(cleaned):
            return None
        title = cleaned["acupoint_name"]
        normalized_content = {
            "template_key": template_key,
            "template_label": (normalized_content or {}).get("template_label", "穴位基础卡"),
            **cleaned,
        }

    return KnowledgeCardResponse(
        id=card.id,
        title=title,
        template_key=template_key,
        subject=subject.display_name,
        subject_key=subject.key,
        subject_display_name=subject.display_name,
        category=card.category,
        source_document_id=card.source_document_id,
        source_document_name=source_document_name,
        importance_level=importance_level,
        raw_excerpt=card.raw_excerpt,
        normalized_content=normalized_content,
        citations=[
            CardCitationResponse(
                id=citation.id,
                page_number=citation.page_number,
                quote=citation.quote,
                document_name=Path(
                    citation.source_document.image_url
                    or f"文档-{citation.source_document_id}"
                ).name,
            )
            for citation in card.citations
        ],
        formula_card=formula_data,
        acupuncture_card=acupuncture_data,
        warm_disease_card=warm_disease_data,
        created_at=card.created_at,
    )


def _serialize_card_list(
    cards: list[KnowledgeCard],
    db: Session,
    user_id: int,
) -> list[KnowledgeCardResponse]:
    """Serialize cards and dedupe cleaned clinical titles."""
    results: list[KnowledgeCardResponse] = []
    seen_clinical_titles: set[str] = set()

    for card in cards:
        serialized = _serialize_card(card, db, user_id)
        if serialized is None:
            continue
        if serialized.template_key == "clinical_treatment":
            title_key = normalize_clinical_title_key(serialized.title)
            if title_key in seen_clinical_titles:
                continue
            seen_clinical_titles.add(title_key)
        results.append(serialized)

    return results


def _normalize_card_key(value: str | None) -> str:
    """Normalize a card title-like key for cross-source dedupe."""
    if not value:
        return ""
    normalized = "".join(str(value).split())
    normalized = re.sub(r"[（(].*?[）)]", "", normalized)
    normalized = "".join(
        char for char in normalized if char.isalnum() or "\u4e00" <= char <= "\u9fa5"
    )
    return normalized.lower()


def _card_dedupe_key(card: KnowledgeCardResponse) -> str:
    """Build a stable cross-document dedupe key."""
    normalized_content = card.normalized_content or {}
    canonical_name = (
        normalized_content.get("acupoint_name")
        or normalized_content.get("disease_name")
        or normalized_content.get("pattern_name")
        or card.title
    )
    key = _normalize_card_key(canonical_name)
    return f"{card.template_key}:{key or card.id}"


def _card_quality_score(card: KnowledgeCardResponse) -> int:
    """Prefer richer cards when duplicates are encountered."""
    normalized_content = card.normalized_content or {}
    field_count = sum(
        1
        for key, value in normalized_content.items()
        if value and key not in {"template_key", "template_label"}
    )
    citation_count = len(card.citations)
    return field_count * 10 + citation_count


def _dedupe_response_cards(cards: list[KnowledgeCardResponse]) -> list[KnowledgeCardResponse]:
    """Dedupe cards using the same canonical title rules as the frontend."""
    deduped: dict[str, KnowledgeCardResponse] = {}
    for card in cards:
        key = _card_dedupe_key(card)
        current = deduped.get(key)
        if current is None or _card_quality_score(card) >= _card_quality_score(current):
            deduped[key] = card
    return sorted(deduped.values(), key=lambda item: item.id, reverse=True)


def _load_serialized_cards(
    db: Session,
    *,
    collection_ids: list[int],
    user_id: int,
    template_key: str | None,
) -> list[KnowledgeCardResponse]:
    """Load, clean, and dedupe cards across one or more collections."""
    query = db.query(KnowledgeCard).filter(KnowledgeCard.collection_id.in_(collection_ids))
    if template_key:
        query = query.filter(KnowledgeCard.category == template_key)
    query = query.order_by(KnowledgeCard.created_at.desc())
    serialized = _serialize_card_list(query.all(), db, user_id)
    return _dedupe_response_cards(serialized)


def migrate_importance_from_json_if_needed(db: Session) -> None:
    """One-time migration: copy importance_level from card JSON to user_card_importance for user 1."""
    global _IMPORTANCE_MIGRATED  # noqa: PLW0603
    if _IMPORTANCE_MIGRATED:
        return
    _IMPORTANCE_MIGRATED = True

    cards = db.query(KnowledgeCard).all()
    migrated = 0
    for card in cards:
        if not card.normalized_content_json:
            continue
        try:
            data = json.loads(card.normalized_content_json)
        except (json.JSONDecodeError, TypeError):
            continue
        level = int(data.get("importance_level", 0) or 0)
        if level <= 0:
            continue
        existing = db.get(UserCardImportance, (1, card.id))
        if existing:
            continue
        db.add(UserCardImportance(user_id=1, card_id=card.id, importance_level=level))
        migrated += 1

    if migrated:
        db.commit()
        logger.info("Migrated %d card importance values to user_card_importance table", migrated)


@router.post("/generate", response_model=GenerateCardsResponse)
async def generate_cards(
    request: GenerateCardsRequest,
    user_id: int = Query(1, description="User ID"),
    db: Session = Depends(get_db),
):
    """Generate knowledge cards from a document."""
    _ensure_user(db, user_id)
    migrate_importance_from_json_if_needed(db)
    generator = create_card_generator(db)
    try:
        cards = generator.generate_cards_from_document(
            request.document_id,
            request.template_key,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    serialized_cards = _serialize_card_list(cards, db, user_id)
    return GenerateCardsResponse(
        cards=serialized_cards,
        status="generated",
    )


@router.post("/{card_id}/importance", response_model=KnowledgeCardResponse)
async def set_card_importance(
    card_id: int,
    request: SetCardImportanceRequest,
    user_id: int = Query(1, description="User ID"),
    db: Session = Depends(get_db),
):
    """Persist a per-user card importance level."""
    _ensure_user(db, user_id)
    migrate_importance_from_json_if_needed(db)
    card = db.get(KnowledgeCard, card_id)
    if not card:
        raise HTTPException(status_code=404, detail=f"Card {card_id} not found")
    if not 0 <= request.importance_level <= 5:
        raise HTTPException(status_code=400, detail="importance_level must be between 0 and 5")

    row = db.get(UserCardImportance, (user_id, card_id))
    if row:
        row.importance_level = request.importance_level
    else:
        db.add(
            UserCardImportance(
                user_id=user_id,
                card_id=card_id,
                importance_level=request.importance_level,
            )
        )

    db.commit()
    db.refresh(card)
    serialized = _serialize_card(card, db, user_id)
    if serialized is None:
        raise HTTPException(status_code=404, detail=f"Card {card_id} is no longer available")
    return serialized


@router.get("", response_model=list[KnowledgeCardResponse])
async def get_cards(
    collection_id: int = Query(..., description="Collection ID"),
    user_id: int = Query(1, description="User ID"),
    template_key: str | None = Query(None, description="Optional template key filter"),
    limit: int | None = Query(None, ge=1, le=100, description="Optional result limit"),
    offset: int = Query(0, ge=0, description="Optional result offset"),
    db: Session = Depends(get_db),
):
    """Get all cards for a collection."""
    _ensure_user(db, user_id)
    migrate_importance_from_json_if_needed(db)

    collection = db.get(StudyCollection, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail=f"Collection {collection_id} not found")
    cards = _load_serialized_cards(
        db,
        collection_ids=[collection_id],
        user_id=user_id,
        template_key=template_key,
    )
    return cards[offset:] if limit is None else cards[offset : offset + limit]


@router.get("/random-batch", response_model=list[KnowledgeCardResponse])
async def get_random_card_batch(
    collection_id: int | None = Query(None, description="Single collection ID"),
    collection_ids: list[int] = Query([], description="Merged collection IDs"),
    user_id: int = Query(1, description="User ID"),
    template_key: str = Query(..., description="Template key"),
    limit: int = Query(10, ge=1, le=30, description="Target batch size"),
    exclude_card_ids: list[int] = Query([], description="Card IDs to avoid"),
    db: Session = Depends(get_db),
):
    """Return a weighted random batch for the front-end draw buffer."""
    _ensure_user(db, user_id)
    migrate_importance_from_json_if_needed(db)

    target_collection_ids = collection_ids or ([collection_id] if collection_id is not None else [])
    if not target_collection_ids:
        raise HTTPException(status_code=400, detail="collection_id or collection_ids is required")

    existing_collections = (
        db.query(StudyCollection.id)
        .filter(StudyCollection.id.in_(target_collection_ids))
        .all()
    )
    existing_ids = {item[0] for item in existing_collections}
    missing_ids = [item for item in target_collection_ids if item not in existing_ids]
    if missing_ids:
        raise HTTPException(status_code=404, detail=f"Collection {missing_ids[0]} not found")

    cards = _load_serialized_cards(
        db,
        collection_ids=target_collection_ids,
        user_id=user_id,
        template_key=template_key,
    )
    return select_weighted_card_batch(
        cards,
        limit=limit,
        exclude_card_ids=set(exclude_card_ids),
    )


@router.get("/{card_id}", response_model=KnowledgeCardResponse)
async def get_card(
    card_id: int,
    user_id: int = Query(1, description="User ID"),
    db: Session = Depends(get_db),
):
    """Get a specific card."""
    _ensure_user(db, user_id)
    migrate_importance_from_json_if_needed(db)
    card = db.get(KnowledgeCard, card_id)
    if not card:
        raise HTTPException(status_code=404, detail=f"Card {card_id} not found")

    serialized = _serialize_card(card, db, user_id)
    if serialized is None:
        raise HTTPException(status_code=404, detail=f"Card {card_id} is no longer available")
    return serialized
