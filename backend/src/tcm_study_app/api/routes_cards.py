"""Card routes."""
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from tcm_study_app.core import get_subject_definition
from tcm_study_app.db import get_db
from tcm_study_app.models import KnowledgeCard, StudyCollection
from tcm_study_app.schemas import (
    AcupunctureCardData,
    CardCitationResponse,
    FormulaCardData,
    GenerateCardsRequest,
    GenerateCardsResponse,
    KnowledgeCardResponse,
    WarmDiseaseCardData,
)
from tcm_study_app.services import create_card_generator

router = APIRouter(prefix="/api/cards", tags=["cards"])


def _load_normalized_content(card: KnowledgeCard) -> tuple[dict | None, str, int]:
    """Decode card JSON content and extract template metadata plus draw count."""
    normalized_content = None
    template_key = card.category
    draw_count = 0

    if card.normalized_content_json:
        try:
            normalized_content = json.loads(card.normalized_content_json)
            template_key = normalized_content.get("template_key", card.category)
            draw_count = int(normalized_content.get("draw_count", 0) or 0)
            normalized_content = {
                key: value
                for key, value in normalized_content.items()
                if key != "draw_count"
            }
        except (json.JSONDecodeError, TypeError, ValueError):
            normalized_content = None
            draw_count = 0

    return normalized_content, template_key, draw_count


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
    normalized_content, template_key, draw_count = _load_normalized_content(card)

    source_document_name = None
    if card.source_document:
        source_document_name = Path(
            card.source_document.image_url or f"文档-{card.source_document.id}"
        ).name

    return KnowledgeCardResponse(
        id=card.id,
        title=card.title,
        template_key=template_key,
        subject=subject.display_name,
        subject_key=subject.key,
        subject_display_name=subject.display_name,
        category=card.category,
        source_document_id=card.source_document_id,
        source_document_name=source_document_name,
        draw_count=draw_count,
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


@router.post("/generate", response_model=GenerateCardsResponse)
async def generate_cards(request: GenerateCardsRequest, db: Session = Depends(get_db)):
    """Generate knowledge cards from a document."""
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
    return GenerateCardsResponse(
        cards=[_serialize_card(card) for card in cards],
        status="generated",
    )


@router.post("/{card_id}/draw", response_model=KnowledgeCardResponse)
async def record_card_draw(card_id: int, db: Session = Depends(get_db)):
    """Record one draw for a card and persist the updated count."""
    card = db.get(KnowledgeCard, card_id)
    if not card:
        raise HTTPException(status_code=404, detail=f"Card {card_id} not found")

    normalized_content, template_key, draw_count = _load_normalized_content(card)
    payload = normalized_content.copy() if normalized_content else {}
    payload["template_key"] = template_key
    payload["draw_count"] = draw_count + 1
    card.normalized_content_json = json.dumps(payload, ensure_ascii=False)

    db.add(card)
    db.commit()
    db.refresh(card)
    return _serialize_card(card)


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
        .order_by(KnowledgeCard.created_at.desc())
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
