"""Card generator service."""
import json

from sqlalchemy.orm import Session

from tcm_study_app.core import get_subject_definition
from tcm_study_app.models import KnowledgeCard, StudyCollection
from tcm_study_app.services.llm_service import llm_service


class CardGenerator:
    """Service for generating knowledge cards."""

    def __init__(self, db: Session):
        self.db = db

    def generate_cards_from_document(
        self, document_id: int
    ) -> list[KnowledgeCard]:
        """
        Generate knowledge cards from a source document.

        Args:
            document_id: ID of the source document

        Returns:
            List of generated knowledge cards
        """
        from tcm_study_app.models import SourceDocument

        # Get the source document
        document = self.db.get(SourceDocument, document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")
        collection = self.db.get(StudyCollection, document.collection_id)
        if not collection:
            raise ValueError(f"Collection {document.collection_id} not found")

        # Get the text to process (OCR text or raw text)
        text = document.ocr_text or document.raw_text
        if not text:
            raise ValueError("No text available in document")

        subject = get_subject_definition(collection.subject)
        normalized_content = subject.extract(llm_service, text)
        card_title = normalized_content.get(subject.title_field) or subject.default_title

        # Create knowledge card
        knowledge_card = KnowledgeCard(
            collection_id=document.collection_id,
            source_document_id=document.id,
            title=card_title,
            category=subject.category,
            raw_excerpt=text[:500] if len(text) > 500 else text,
            normalized_content_json=json.dumps(normalized_content, ensure_ascii=False),
        )
        self.db.add(knowledge_card)
        self.db.flush()

        self.db.add(subject.build_record(knowledge_card.id, normalized_content))

        # Update document status
        document.status = "processed"

        self.db.commit()
        self.db.refresh(knowledge_card)

        return [knowledge_card]

    def get_card_with_formula(self, card_id: int) -> KnowledgeCard | None:
        """Get a knowledge card with its formula data."""
        card = self.db.get(KnowledgeCard, card_id)
        if not card:
            return None

        # Force load any subject relationship for serialization.
        _ = card.formula_card
        _ = card.acupuncture_card
        _ = card.warm_disease_card
        return card


def create_card_generator(db: Session) -> CardGenerator:
    """Factory function to create CardGenerator."""
    return CardGenerator(db)
