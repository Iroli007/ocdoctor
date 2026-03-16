"""Card generator service."""
import json
import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from tcm_study_app.core import get_card_template, get_subject_definition
from tcm_study_app.models import CardCitation, KnowledgeCard, SourceDocument, StudyCollection
from tcm_study_app.services.llm_service import llm_service


@dataclass(frozen=True)
class _ExtractableUnit:
    """A chunk-like extractable text unit used during card generation."""

    chunk_id: int
    page_number: int
    content: str


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

        for unit in self._iter_extractable_units(subject.key, template.key, chunks):
            extracted = self._extract_card(subject.key, template.key, unit.content)
            title = self._resolve_title(subject, template.key, extracted)
            if title == self._default_title(subject.key, template.key) or title in generated_titles:
                continue
            if not self._passes_subject_quality_gate(subject.key, template.key, title, extracted):
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
                raw_excerpt=unit.content[:500],
                normalized_content_json=json.dumps(normalized_content, ensure_ascii=False),
            )
            self.db.add(knowledge_card)
            self.db.flush()

            record = self._build_subject_record(subject, template.key, knowledge_card.id, extracted)
            if record is not None:
                self.db.add(record)
            self.db.add(
                CardCitation(
                    knowledge_card_id=knowledge_card.id,
                    source_document_id=document.id,
                    document_chunk_id=unit.chunk_id,
                    page_number=unit.page_number,
                    quote=unit.content[:800],
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

    def _candidate_chunks(self, subject_key: str, template_key: str, chunks: list) -> list:
        """Keep chunks likely to contain extractable card content."""
        if subject_key == "acupuncture" and template_key == "clinical_treatment":
            keywords = ("病", "症", "治法", "处方", "取穴", "主穴", "配穴", "加减", "治疗")
        else:
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

    def _iter_extractable_units(
        self,
        subject_key: str,
        template_key: str,
        chunks: list,
    ) -> list[_ExtractableUnit]:
        """Expand source chunks into smaller subject-friendly extraction units."""
        if subject_key == "acupuncture" and template_key == "clinical_treatment":
            return self._build_clinical_treatment_units(chunks)

        units: list[_ExtractableUnit] = []
        for chunk in self._candidate_chunks(subject_key, template_key, chunks):
            if subject_key == "acupuncture":
                sub_units = self._split_acupuncture_chunk(chunk.content)
                if sub_units:
                    units.extend(
                        _ExtractableUnit(
                            chunk_id=chunk.id,
                            page_number=chunk.page_number,
                            content=sub_unit,
                        )
                        for sub_unit in sub_units
                    )
                    continue

            units.append(
                _ExtractableUnit(
                    chunk_id=chunk.id,
                    page_number=chunk.page_number,
                    content=chunk.content,
                )
            )
        return units

    def _build_clinical_treatment_units(self, chunks: list) -> list[_ExtractableUnit]:
        """Create single-chunk and adjacent-chunk windows for clinical treatment extraction."""
        candidates = self._candidate_chunks("acupuncture", "clinical_treatment", chunks)
        units: list[_ExtractableUnit] = []
        seen_contents: set[str] = set()

        for index, chunk in enumerate(candidates):
            single = re.sub(r"\s+", " ", chunk.content).strip()
            if single and single not in seen_contents:
                units.append(
                    _ExtractableUnit(
                        chunk_id=chunk.id,
                        page_number=chunk.page_number,
                        content=single,
                    )
                )
                seen_contents.add(single)

            if index + 1 >= len(candidates):
                continue

            pair = "\n\n".join(
                item.content.strip()
                for item in candidates[index : index + 2]
                if item.content.strip()
            ).strip()
            pair = re.sub(r"\s+", " ", pair)
            if pair and pair not in seen_contents:
                units.append(
                    _ExtractableUnit(
                        chunk_id=chunk.id,
                        page_number=chunk.page_number,
                        content=pair,
                    )
                )
                seen_contents.add(pair)

        return units

    def _extract_card(self, subject_key: str, template_key: str, text: str) -> dict:
        """Route extraction through the right template-aware extractor."""
        if subject_key == "acupuncture" and template_key == "clinical_treatment":
            return llm_service.extract_acupuncture_clinical_card(text)

        subject = get_subject_definition(subject_key)
        return subject.extract(llm_service, text)

    def _resolve_title(self, subject, template_key: str, extracted: dict) -> str:
        """Resolve the card title for a subject/template pair."""
        if subject.key == "acupuncture" and template_key == "clinical_treatment":
            return extracted.get("disease_name") or "未知病证"
        return extracted.get(subject.title_field) or subject.default_title

    def _default_title(self, subject_key: str, template_key: str) -> str:
        """Return the placeholder title for the subject/template pair."""
        if subject_key == "acupuncture" and template_key == "clinical_treatment":
            return "未知病证"
        return get_subject_definition(subject_key).default_title

    def _build_subject_record(
        self,
        subject,
        template_key: str,
        knowledge_card_id: int,
        extracted: dict,
    ):
        """Create an optional typed record for templates that need one."""
        if subject.key == "acupuncture" and template_key == "clinical_treatment":
            return None
        return subject.build_record(knowledge_card_id, extracted)

    def _passes_subject_quality_gate(
        self,
        subject_key: str,
        template_key: str,
        title: str,
        extracted: dict,
    ) -> bool:
        """Filter obviously noisy cards before persistence."""
        if subject_key == "acupuncture" and template_key == "clinical_treatment":
            blocked_title_patterns = (
                r"^本病",
                r"^必要时",
                r"^用于临床",
                r"^血管情况",
                r"^分钟",
                r"^特殊的",
                r"^或胀痛",
                r"^风寒证$",
                r"^风热证$",
                r"^风湿证$",
                r"^肝阳上亢证$",
                r"^肾虚证$",
                r"^血虚证$",
                r"^痰浊证$",
                r"^血瘀证$",
                r"^气滞证$",
                r"^寒凝证$",
            )
            if any(re.search(pattern, title) for pattern in blocked_title_patterns):
                return False
            if not extracted.get("treatment_principle") or not extracted.get("acupoint_prescription"):
                return False
        return True

    def _split_acupuncture_chunk(self, content: str) -> list[str]:
        """Split OCR textbook prose into one-text-block-per-acupoint."""
        compact_content = re.sub(r"\s+", " ", content).strip()
        starts = list(
            re.finditer(
                r"(?:^|[。；;\s])\d+\.\s*[\u4e00-\u9fa5]{1,8}(?:\*|\s)*\([^)]*[A-Za-z]{1,3}\s*\d+[^)]*\)",
                compact_content,
            )
        )
        if not starts:
            return []

        blocks: list[str] = []
        for index, match in enumerate(starts):
            start_index = match.start()
            if compact_content[start_index].isspace():
                start_index += 1
            end_index = starts[index + 1].start() if index + 1 < len(starts) else len(compact_content)
            block = compact_content[start_index:end_index].strip()
            if block:
                blocks.append(block)
        return blocks

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
