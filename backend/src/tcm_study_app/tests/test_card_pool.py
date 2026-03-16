"""Tests for weighted card pool selection."""
from __future__ import annotations

import random
from datetime import UTC, datetime

from tcm_study_app.schemas import KnowledgeCardResponse
from tcm_study_app.services.card_pool import select_weighted_card_batch


def _card(card_id: int, title: str, importance_level: int) -> KnowledgeCardResponse:
    return KnowledgeCardResponse(
        id=card_id,
        title=title,
        template_key="clinical_treatment",
        subject="针灸学",
        subject_key="acupuncture",
        subject_display_name="针灸学",
        category="clinical_treatment",
        source_document_id=None,
        source_document_name=None,
        importance_level=importance_level,
        raw_excerpt=None,
        normalized_content={"template_key": "clinical_treatment", "disease_name": title},
        citations=[],
        formula_card=None,
        acupuncture_card=None,
        warm_disease_card=None,
        created_at=datetime.now(UTC),
    )


def test_select_weighted_card_batch_respects_exclusions_and_limit():
    cards = [
        _card(1, "头痛", 0),
        _card(2, "眩晕", 5),
        _card(3, "胃痛", 2),
    ]

    selected = select_weighted_card_batch(
        cards,
        limit=2,
        exclude_card_ids={2},
        rng=random.Random(7),
    )

    assert [card.id for card in selected] == [3, 1]


def test_select_weighted_card_batch_prefers_higher_importance_with_seeded_rng():
    cards = [
        _card(1, "头痛", 0),
        _card(2, "眩晕", 5),
    ]

    first = select_weighted_card_batch(cards, limit=1, rng=random.Random(11))

    assert first[0].id == 2
