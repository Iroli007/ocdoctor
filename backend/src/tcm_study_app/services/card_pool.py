"""Card pool helpers for buffered random draws."""
from __future__ import annotations

import math
import random
from typing import Iterable

from tcm_study_app.schemas import KnowledgeCardResponse


def select_weighted_card_batch(
    cards: Iterable[KnowledgeCardResponse],
    *,
    limit: int,
    exclude_card_ids: set[int] | None = None,
    rng: random.Random | None = None,
) -> list[KnowledgeCardResponse]:
    """Pick a weighted unique batch of cards for the draw buffer.

    The weight follows the current product rule:
    each card starts at 1 and gains one extra occurrence per star.
    """
    if limit <= 0:
        return []

    excluded = exclude_card_ids or set()
    random_source = rng or random.Random()
    ranked_cards: list[tuple[float, int, int, KnowledgeCardResponse]] = []

    for card in cards:
        if card.id in excluded:
            continue
        weight = max(1, 1 + int(card.importance_level or 0))
        # Weighted random ordering without replacement.
        score = math.log(max(random_source.random(), 1e-9)) / weight
        ranked_cards.append((score, weight, card.id, card))

    ranked_cards.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    return [item[3] for item in ranked_cards[:limit]]
