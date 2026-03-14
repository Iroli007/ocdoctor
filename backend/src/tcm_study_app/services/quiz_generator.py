"""Quiz generator service."""
import json
import random

from sqlalchemy.orm import Session

from tcm_study_app.models import KnowledgeCard, Quiz, StudyCollection
from tcm_study_app.services.llm_service import llm_service


class QuizGenerator:
    """Service for generating quiz questions."""

    def __init__(self, db: Session):
        self.db = db

    def generate_quizzes(
        self, collection_id: int, count: int = 5, difficulty: str = "medium"
    ) -> list[Quiz]:
        """
        Generate quiz questions for a collection.

        Args:
            collection_id: ID of the study collection
            count: Number of quizzes to generate
            difficulty: Difficulty level (easy/medium/hard)

        Returns:
            List of generated quizzes
        """
        # Get cards from collection
        cards = (
            self.db.query(KnowledgeCard)
            .filter(KnowledgeCard.collection_id == collection_id)
            .all()
        )

        if not cards:
            raise ValueError("No cards available in collection")

        quizzes = []
        for _ in range(min(count, len(cards))):
            # Pick a random card
            card = random.choice(cards)
            card_content = {}

            # Try to parse formula card data
            if card.normalized_content_json:
                try:
                    card_content = json.loads(card.normalized_content_json)
                except json.JSONDecodeError:
                    pass

            if not card_content:
                card_content = {"formula_name": card.title}

            # Generate quiz using LLM
            quiz_data = llm_service.generate_quiz(card_content, difficulty)

            # Create quiz
            quiz = Quiz(
                collection_id=collection_id,
                type=quiz_data.get("type", "choice"),
                question=quiz_data.get("question", ""),
                options_json=json.dumps(quiz_data.get("options", [])),
                answer=quiz_data.get("answer", ""),
                explanation=quiz_data.get("explanation"),
                difficulty=difficulty,
            )
            self.db.add(quiz)
            quizzes.append(quiz)

        self.db.commit()

        # Refresh to get IDs
        for quiz in quizzes:
            self.db.refresh(quiz)

        return quizzes

    def get_quizzes_by_collection(
        self, collection_id: int, limit: int = 10
    ) -> list[Quiz]:
        """Get quizzes for a collection."""
        return (
            self.db.query(Quiz)
            .filter(Quiz.collection_id == collection_id)
            .limit(limit)
            .all()
        )


def create_quiz_generator(db: Session) -> QuizGenerator:
    """Factory function to create QuizGenerator."""
    return QuizGenerator(db)
