"""Card generator service."""
import json
import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from tcm_study_app.core import get_card_template, get_subject_definition
from tcm_study_app.models import CardCitation, KnowledgeCard, SourceDocument, StudyCollection
from tcm_study_app.services.acupuncture_card_cleanup import (
    clean_acupuncture_card_payload,
    is_valid_acupuncture_card_payload,
)
from tcm_study_app.services.clinical_card_cleanup import (
    clean_clinical_card_payload,
    extract_clinical_disease_name,
    is_valid_clinical_card_payload,
)
from tcm_study_app.services.theory_card_cleanup import (
    clean_theory_card_payload,
    is_valid_theory_card_payload,
)
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
        existing_title_keys = self._existing_title_keys(
            collection_id=document.collection_id,
            template_key=template.key,
            exclude_document_id=document.id,
        )
        generated_titles = set()
        generated_cards = []

        for unit in self._iter_extractable_units(subject.key, template.key, chunks):
            extracted = self._extract_card(subject.key, template.key, unit.content)
            title = self._resolve_title(subject, template.key, extracted)
            title_key = self._normalize_title_key(title)
            if (
                title == self._default_title(subject.key, template.key)
                or title in generated_titles
                or title_key in existing_title_keys
            ):
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
            existing_title_keys.add(title_key)

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

    def _existing_title_keys(
        self,
        *,
        collection_id: int,
        template_key: str,
        exclude_document_id: int,
    ) -> set[str]:
        """Load normalized title keys already present in the collection/template."""
        cards = (
            self.db.query(KnowledgeCard.title)
            .filter(
                KnowledgeCard.collection_id == collection_id,
                KnowledgeCard.category == template_key,
                KnowledgeCard.source_document_id != exclude_document_id,
            )
            .all()
        )
        return {
            title_key
            for (title,) in cards
            if (title_key := self._normalize_title_key(title))
        }

    def _normalize_title_key(self, title: str | None) -> str:
        """Normalize a card title for lightweight cross-document dedupe."""
        if not title:
            return ""
        normalized = re.sub(r"\s+", "", title)
        normalized = re.sub(r"[（(].*?[）)]", "", normalized)
        normalized = re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9]", "", normalized)
        return normalized.lower()

    def _candidate_chunks(self, subject_key: str, template_key: str, chunks: list) -> list:
        """Keep chunks likely to contain extractable card content."""
        if subject_key == "acupuncture" and template_key == "clinical_treatment":
            keywords = ("病", "症", "治法", "处方", "取穴", "主穴", "配穴", "加减", "治疗")
        elif subject_key == "acupuncture" and template_key == "theory_review":
            keywords = (
                "原则",
                "作用",
                "特点",
                "定义",
                "概念",
                "定位法",
                "取穴",
                "配穴",
                "特定穴",
                "五输穴",
                "原穴",
                "络穴",
                "募穴",
                "下合穴",
                "八会穴",
                "郄穴",
                "八脉交会穴",
                "交会穴",
                "毫针",
                "灸法",
                "拔罐",
                "耳针",
                "头针",
                "电针",
                "针灸处方",
            )
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
        max_window = 8

        for index, chunk in enumerate(candidates):
            has_heading = bool(extract_clinical_disease_name(chunk.content))
            if not has_heading:
                continue

            window_parts: list[str] = []
            for next_chunk in candidates[index : index + max_window]:
                if (
                    window_parts
                    and next_chunk is not chunk
                    and extract_clinical_disease_name(next_chunk.content)
                ):
                    break

                content = next_chunk.content.strip()
                if not content:
                    continue
                window_parts.append(content)
                window_text = re.sub(r"\s+", " ", "\n\n".join(window_parts)).strip()
                if (
                    window_text
                    and self._clinical_window_has_core_markers(window_text)
                    and window_text not in seen_contents
                ):
                    units.append(
                        _ExtractableUnit(
                            chunk_id=chunk.id,
                            page_number=chunk.page_number,
                            content=window_text,
                        )
                    )
                    seen_contents.add(window_text)

        return units

    def _clinical_window_has_core_markers(self, text: str) -> bool:
        """Require a clinical window to reach the treatment/prescription core."""
        return bool(
            re.search(r"(治法|治则|治疗原则|辨证论治)", text)
            and re.search(r"(处方|取穴|主穴|配穴|选穴|基本处方)", text)
        )

    def _extract_card(self, subject_key: str, template_key: str, text: str) -> dict:
        """Route extraction through the right template-aware extractor."""
        if subject_key == "acupuncture" and template_key == "clinical_treatment":
            return clean_clinical_card_payload(
                llm_service.extract_acupuncture_clinical_card(text),
                source_text=text,
            )
        if subject_key == "acupuncture" and template_key == "theory_review":
            return clean_theory_card_payload(
                llm_service.extract_acupuncture_theory_card(text),
                source_text=text,
            )
        if subject_key == "acupuncture":
            return clean_acupuncture_card_payload(
                llm_service.extract_acupuncture_card(text),
                source_text=text,
            )

        subject = get_subject_definition(subject_key)
        return subject.extract(llm_service, text)

    def _resolve_title(self, subject, template_key: str, extracted: dict) -> str:
        """Resolve the card title for a subject/template pair."""
        if subject.key == "acupuncture" and template_key == "clinical_treatment":
            return extracted.get("disease_name") or "未知病证"
        if subject.key == "acupuncture" and template_key == "theory_review":
            return extracted.get("concept_name") or "未知考点"
        return extracted.get(subject.title_field) or subject.default_title

    def _default_title(self, subject_key: str, template_key: str) -> str:
        """Return the placeholder title for the subject/template pair."""
        if subject_key == "acupuncture" and template_key == "clinical_treatment":
            return "未知病证"
        if subject_key == "acupuncture" and template_key == "theory_review":
            return "未知考点"
        return get_subject_definition(subject_key).default_title

    def _build_subject_record(
        self,
        subject,
        template_key: str,
        knowledge_card_id: int,
        extracted: dict,
    ):
        """Create an optional typed record for templates that need one."""
        if subject.key == "acupuncture" and template_key in {"clinical_treatment", "theory_review"}:
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
            cleaned = clean_clinical_card_payload(
                {
                    "disease_name": title,
                    **extracted,
                },
            )
            return is_valid_clinical_card_payload(cleaned)
        if subject_key == "acupuncture" and template_key == "theory_review":
            cleaned = clean_theory_card_payload(
                {
                    "concept_name": title,
                    **extracted,
                },
            )
            return is_valid_theory_card_payload(cleaned)
        if subject_key == "acupuncture":
            cleaned = clean_acupuncture_card_payload(
                {
                    "acupoint_name": title,
                    **extracted,
                },
            )
            return is_valid_acupuncture_card_payload(cleaned)
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
