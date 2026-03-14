"""Card routes."""
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from tcm_study_app.core import get_subject_definition
from tcm_study_app.db import get_db
from tcm_study_app.models import KnowledgeCard, StudyCollection
from tcm_study_app.schemas import (
    AcupunctureCardData,
    FormulaCardData,
    GenerateCardsRequest,
    GenerateCardsResponse,
    KnowledgeCardResponse,
    WarmDiseaseCardData,
)
from tcm_study_app.services import create_card_generator

router = APIRouter(prefix="/api/cards", tags=["cards"])


def _serialize_card(card: KnowledgeCard) -> KnowledgeCardResponse:
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
    normalized_content = None
    if card.normalized_content_json:
        try:
            normalized_content = json.loads(card.normalized_content_json)
        except json.JSONDecodeError:
            normalized_content = None

    return KnowledgeCardResponse(
        id=card.id,
        title=card.title,
        subject=subject.display_name,
        subject_key=subject.key,
        subject_display_name=subject.display_name,
        category=card.category,
        raw_excerpt=card.raw_excerpt,
        normalized_content=normalized_content,
        formula_card=formula_data,
        acupuncture_card=acupuncture_data,
        warm_disease_card=warm_disease_data,
        created_at=card.created_at,
    )


@router.post("/generate", response_model=GenerateCardsResponse)
async def generate_cards(request: GenerateCardsRequest, db: Session = Depends(get_db)):
    """Generate knowledge cards from a document."""
    generator = create_card_generator(db)
    try:
        cards = generator.generate_cards_from_document(request.document_id)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    return GenerateCardsResponse(
        cards=[_serialize_card(card) for card in cards],
        status="generated",
    )


@router.get("", response_model=list[KnowledgeCardResponse])
async def get_cards(
    collection_id: int = Query(..., description="Collection ID"),
    db: Session = Depends(get_db),
):
    """Get all cards for a collection."""
    collection = db.get(StudyCollection, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail=f"Collection {collection_id} not found")

    cards = (
        db.query(KnowledgeCard)
        .filter(KnowledgeCard.collection_id == collection_id)
        .all()
    )

    return [_serialize_card(card) for card in cards]


@router.get("/{card_id}", response_model=KnowledgeCardResponse)
async def get_card(card_id: int, db: Session = Depends(get_db)):
    """Get a specific card."""
    card = db.get(KnowledgeCard, card_id)
    if not card:
        raise HTTPException(status_code=404, detail=f"Card {card_id} not found")

    return _serialize_card(card)
