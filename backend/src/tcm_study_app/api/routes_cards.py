"""Card routes."""
from typing import Any
import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from tcm_study_app.db import get_db
from tcm_study_app.models import KnowledgeCard, StudyCollection
from tcm_study_app.schemas import (
    GenerateCardsRequest,
    GenerateCardsResponse,
    KnowledgeCardResponse,
    FormulaCardData,
)
from tcm_study_app.services import create_card_generator

router = APIRouter(prefix="/api/cards", tags=["cards"])


@router.post("/generate", response_model=GenerateCardsResponse)
async def generate_cards(request: GenerateCardsRequest, db: Session = Depends(get_db)):
    """Generate knowledge cards from a document."""
    generator = create_card_generator(db)
    cards = generator.generate_cards_from_document(request.document_id)

    response_cards = []
    for card in cards:
        formula_data = None
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

        response_cards.append(
            KnowledgeCardResponse(
                id=card.id,
                title=card.title,
                category=card.category,
                raw_excerpt=card.raw_excerpt,
                formula_card=formula_data,
                created_at=card.created_at,
            )
        )

    return GenerateCardsResponse(cards=response_cards, status="generated")


@router.get("", response_model=list[KnowledgeCardResponse])
async def get_cards(
    collection_id: int = Query(..., description="Collection ID"),
    db: Session = Depends(get_db),
):
    """Get all cards for a collection."""
    cards = (
        db.query(KnowledgeCard)
        .filter(KnowledgeCard.collection_id == collection_id)
        .all()
    )

    response_cards = []
    for card in cards:
        formula_data = None
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

        response_cards.append(
            KnowledgeCardResponse(
                id=card.id,
                title=card.title,
                category=card.category,
                raw_excerpt=card.raw_excerpt,
                formula_card=formula_data,
                created_at=card.created_at,
            )
        )

    return response_cards


@router.get("/{card_id}", response_model=KnowledgeCardResponse)
async def get_card(card_id: int, db: Session = Depends(get_db)):
    """Get a specific card."""
    card = db.get(KnowledgeCard, card_id)
    if not card:
        raise ValueError(f"Card {card_id} not found")

    formula_data = None
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

    return KnowledgeCardResponse(
        id=card.id,
        title=card.title,
        category=card.category,
        raw_excerpt=card.raw_excerpt,
        formula_card=formula_data,
        created_at=card.created_at,
    )
