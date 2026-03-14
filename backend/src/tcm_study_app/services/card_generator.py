"""Card generator service."""
import json

from sqlalchemy.orm import Session

from tcm_study_app.models import FormulaCard, KnowledgeCard
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

        # Get the text to process (OCR text or raw text)
        text = document.ocr_text or document.raw_text
        if not text:
            raise ValueError("No text available in document")

        # Extract formula card data using LLM
        formula_data = llm_service.extract_formula_card(text)

        # Create knowledge card
        knowledge_card = KnowledgeCard(
            collection_id=document.collection_id,
            source_document_id=document.id,
            title=formula_data.get("formula_name", "未知方剂"),
            category="formula",
            raw_excerpt=text[:500] if len(text) > 500 else text,
            normalized_content_json=json.dumps(formula_data, ensure_ascii=False),
        )
        self.db.add(knowledge_card)
        self.db.flush()

        # Create formula card
        formula_card = FormulaCard(
            knowledge_card_id=knowledge_card.id,
            formula_name=formula_data.get("formula_name", ""),
            composition=formula_data.get("composition"),
            effect=formula_data.get("effect"),
            indication=formula_data.get("indication"),
            pathogenesis=formula_data.get("pathogenesis"),
            usage_notes=formula_data.get("usage_notes"),
            memory_tip=formula_data.get("memory_tip"),
        )
        self.db.add(formula_card)

        # Update document status
        document.status = "processed"

        self.db.commit()
        self.db.refresh(knowledge_card)

        return [knowledge_card]

    def get_card_with_formula(self, card_id: int) -> KnowledgeCard | None:
        """Get a knowledge card with its formula data."""
        card = self.db.get(KnowledgeCard, card_id)
        if card and card.formula_card:
            # Force load the relationship
            _ = card.formula_card
        return card


def create_card_generator(db: Session) -> CardGenerator:
    """Factory function to create CardGenerator."""
    return CardGenerator(db)
