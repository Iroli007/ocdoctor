"""Card generator service."""
import json

from sqlalchemy.orm import Session

from tcm_study_app.core import get_card_template, get_subject_definition
from tcm_study_app.models import CardCitation, KnowledgeCard, SourceDocument, StudyCollection
from tcm_study_app.services.llm_service import llm_service


class CardGenerator:
    """Generate template-based cards from parsed documents."""

    def __init__(self, db: Session):
        self.db = db

    def generate_cards_from_document(
        self,
        document_id: int,
        template_key: str,
    ) -> list[KnowledgeCard]:
        """Generate cards from a document using a fixed template."""
        document = self.db.get(SourceDocument, document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")

        collection = self.db.get(StudyCollection, document.collection_id)
        if not collection:
            raise ValueError(f"Collection {document.collection_id} not found")

        subject = get_subject_definition(collection.subject)
        template = get_card_template(template_key, subject.key)
        chunks = sorted(
            document.chunks,
            key=lambda item: (item.page_number, item.chunk_index),
        )
        if not chunks:
            raise ValueError("Document has no parsed chunks")

        self._remove_existing_cards(document.id, template.key)
        generated_titles = set()
        generated_cards = []

        for chunk in self._candidate_chunks(subject.key, chunks):
            extracted = subject.extract(llm_service, chunk.content)
            title = extracted.get(subject.title_field) or subject.default_title
            if title == subject.default_title or title in generated_titles:
                continue

            filtered = self._filter_template_fields(extracted, template)
            if len(filtered) < template.minimum_fields:
                continue

            normalized_content = {
                "template_key": template.key,
                "template_label": template.label,
                **filtered,
            }

            knowledge_card = KnowledgeCard(
                collection_id=document.collection_id,
                source_document_id=document.id,
                title=title,
                category=template.key,
                raw_excerpt=chunk.content[:500],
                normalized_content_json=json.dumps(normalized_content, ensure_ascii=False),
            )
            self.db.add(knowledge_card)
            self.db.flush()

            self.db.add(subject.build_record(knowledge_card.id, extracted))
            self.db.add(
                CardCitation(
                    knowledge_card_id=knowledge_card.id,
                    source_document_id=document.id,
                    document_chunk_id=chunk.id,
                    page_number=chunk.page_number,
                    quote=chunk.content[:800],
                )
            )

            generated_cards.append(knowledge_card)
            generated_titles.add(title)

        if not generated_cards:
            raise ValueError("No cards could be generated from this document")

        document.status = "processed"
        self.db.commit()
        for card in generated_cards:
            self.db.refresh(card)
        return generated_cards

    def _remove_existing_cards(self, document_id: int, template_key: str) -> None:
        """Remove previous cards for the same document/template before regenerating."""
        existing_cards = (
            self.db.query(KnowledgeCard)
            .filter(
                KnowledgeCard.source_document_id == document_id,
                KnowledgeCard.category == template_key,
            )
            .all()
        )
        for card in existing_cards:
            self.db.delete(card)
        self.db.flush()

    def _candidate_chunks(self, subject_key: str, chunks: list) -> list:
        """Keep chunks likely to contain extractable card content."""
        keywords = {
            "acupuncture": ("主治", "定位", "刺灸法", "经络", "归经", "穴"),
            "warm_disease": ("证候", "治法", "方药", "辨证", "阶段", "卫分", "气分"),
        }.get(subject_key, ())
        candidates = [
            chunk
            for chunk in chunks
            if any(keyword in chunk.content for keyword in keywords)
        ]
        return candidates or chunks

    def _filter_template_fields(self, extracted: dict, template) -> dict:
        """Filter the extracted subject payload down to the template fields."""
        filtered = {}
        for field in template.fields:
            value = extracted.get(field)
            if value:
                filtered[field] = value
        return filtered


def create_card_generator(db: Session) -> CardGenerator:
    """Factory function to create CardGenerator."""
    return CardGenerator(db)
