"""Comparison generator service."""
import json

from sqlalchemy.orm import Session

from tcm_study_app.models import ComparisonItem, StudyCollection
from tcm_study_app.services.llm_service import llm_service


class ComparisonGenerator:
    """Service for generating comparison items."""

    def __init__(self, db: Session):
        self.db = db

    def generate_comparison(
        self,
        collection_id: int,
        left_entity: str,
        right_entity: str,
    ) -> ComparisonItem:
        """
        Generate a comparison item between two entities.

        Args:
            collection_id: ID of the study collection
            left_entity: Left entity name
            right_entity: Right entity name

        Returns:
            Generated comparison item
        """
        # Get context from existing cards
        collection = self.db.get(StudyCollection, collection_id)
        context = None
        if collection and collection.knowledge_cards:
            cards_text = "\n".join(
                [
                    f"{card.title}: {card.raw_excerpt[:200]}"
                    for card in collection.knowledge_cards[:5]
                ]
            )
            context = cards_text

        # Generate comparison using LLM
        comparison_data = llm_service.generate_comparison(
            left_entity, right_entity, context
        )

        # Create comparison item
        comparison = ComparisonItem(
            collection_id=collection_id,
            left_entity=left_entity,
            right_entity=right_entity,
            comparison_points_json=json.dumps(
                comparison_data.get("comparison_points", []), ensure_ascii=False
            ),
            question_text=comparison_data.get("question_text"),
            answer_text=comparison_data.get("answer_text"),
        )
        self.db.add(comparison)
        self.db.commit()
        self.db.refresh(comparison)

        return comparison

    def get_comparisons_by_collection(
        self, collection_id: int
    ) -> list[ComparisonItem]:
        """Get all comparison items for a collection."""
        return (
            self.db.query(ComparisonItem)
            .filter(ComparisonItem.collection_id == collection_id)
            .all()
        )


def create_comparison_generator(db: Session) -> ComparisonGenerator:
    """Factory function to create ComparisonGenerator."""
    return ComparisonGenerator(db)
