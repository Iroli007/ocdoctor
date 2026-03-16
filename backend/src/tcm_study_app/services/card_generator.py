"""Card generator service."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from tcm_study_app.core import get_card_template, get_subject_definition
from tcm_study_app.models import (
    AcupointKnowledgeCard,
    CardCitation,
    ConditionTreatmentCard,
    KnowledgeCard,
    NeedlingTechniqueCard,
    SourceDocument,
    StudyCollection,
)
from tcm_study_app.services.acupuncture_card_cleanup import (
    clean_acupuncture_card_payload,
    is_valid_acupuncture_card_payload,
)
from tcm_study_app.services.clinical_card_cleanup import (
    clean_clinical_card_payload,
    is_valid_clinical_card_payload,
)
from tcm_study_app.services.llm_service import llm_service
from tcm_study_app.services.needling_technique_cleanup import (
    clean_needling_technique_payload,
    is_valid_needling_technique_payload,
)


@dataclass(frozen=True)
class _UnitPayload:
    """Minimal extraction unit for card generation."""

    unit_id: int
    page_number_start: int
    source_heading: str | None
    source_text: str
    unit_type: str

    @property
    def content(self) -> str:
        """Backward-compatible alias used by older tests."""
        return self.source_text


class CardGenerator:
    """Generate template-based cards from parsed documents."""

    _TEMPLATE_UNIT_TYPE = {
        "acupoint_knowledge": "acupoint_entry",
        "needling_technique": "technique_topic",
        "condition_treatment": "condition_entry",
    }

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
        response_template_key = template_key
        self._remove_existing_cards(document.id, template.key)

        if subject.key == "acupuncture":
            generated_cards = self._generate_acupuncture_cards(document, template, response_template_key)
        else:
            generated_cards = self._generate_generic_subject_cards(document, template, response_template_key)

        if not generated_cards:
            if self._document_has_matching_units(document, template.key):
                self.db.commit()
                return []
            raise ValueError("No cards could be generated from this document")

        document.status = "processed"
        self.db.commit()
        for card in generated_cards:
            self.db.refresh(card)
        return generated_cards

    def _generate_acupuncture_cards(self, document: SourceDocument, template, response_template_key: str) -> list[KnowledgeCard]:
        expected_unit_type = self._TEMPLATE_UNIT_TYPE[template.key]
        units = [
            _UnitPayload(
                unit_id=unit.id,
                page_number_start=unit.page_number_start,
                source_heading=unit.source_heading,
                source_text=unit.source_text,
                unit_type=unit.unit_type,
            )
            for unit in sorted(document.parsed_units, key=lambda item: item.sequence_no)
            if unit.unit_type == expected_unit_type and unit.validation_state == "valid"
        ]
        if not units:
            raise ValueError("No cards could be generated from this document")

        existing_title_keys = self._existing_title_keys(
            collection_id=document.collection_id,
            template_key=template.key,
            exclude_document_id=document.id,
        )
        generated_titles: set[str] = set()
        generated_cards: list[KnowledgeCard] = []

        for unit in units:
            extracted = self._extract_acupuncture_payload(template.key, unit.source_text)
            title = self._resolve_acupuncture_title(template.key, extracted)
            title_key = self._normalize_title_key(title)
            if (
                not title
                or title_key in existing_title_keys
                or title in generated_titles
                or not self._passes_acupuncture_quality_gate(template.key, extracted)
            ):
                continue

            filtered = {
                field: value
                for field in template.fields
                if (value := extracted.get(field))
            }
            if len(filtered) < template.minimum_fields:
                continue

            normalized_content = {
                "template_key": response_template_key,
                "template_label": self._response_template_label(response_template_key, template.label),
                "_source_book": "临床针灸学",
                "_book_part": document.book_section,
                **filtered,
            }
            knowledge_card = KnowledgeCard(
                collection_id=document.collection_id,
                source_document_id=document.id,
                title=title,
                category=template.key,
                raw_excerpt=unit.source_text[:500],
                normalized_content_json=json.dumps(normalized_content, ensure_ascii=False),
            )
            self.db.add(knowledge_card)
            self.db.flush()

            self._add_acupuncture_typed_record(knowledge_card.id, template.key, extracted)
            self.db.add(
                CardCitation(
                    knowledge_card_id=knowledge_card.id,
                    source_document_id=document.id,
                    parsed_document_unit_id=unit.unit_id,
                    page_number=unit.page_number_start,
                    quote=unit.source_text[:800],
                )
            )
            generated_cards.append(knowledge_card)
            generated_titles.add(title)
            existing_title_keys.add(title_key)

        return generated_cards

    def _generate_generic_subject_cards(self, document: SourceDocument, template, response_template_key: str) -> list[KnowledgeCard]:
        chunks = sorted(document.chunks, key=lambda item: (item.page_number, item.chunk_index))
        if not chunks:
            raise ValueError("Document has no parsed chunks")
        subject = get_subject_definition(document.collection.subject)
        generated_cards: list[KnowledgeCard] = []

        existing_title_keys = self._existing_title_keys(
            collection_id=document.collection_id,
            template_key=template.key,
            exclude_document_id=document.id,
        )
        for chunk in chunks:
            extracted = subject.extract(llm_service, chunk.content)
            title = extracted.get(subject.title_field) or subject.default_title
            title_key = self._normalize_title_key(title)
            if title_key in existing_title_keys:
                continue
            filtered = {
                field: value
                for field in template.fields
                if (value := extracted.get(field))
            }
            if len(filtered) < template.minimum_fields:
                continue
            knowledge_card = KnowledgeCard(
                collection_id=document.collection_id,
                source_document_id=document.id,
                title=title,
                category=template.key,
                raw_excerpt=chunk.content[:500],
                normalized_content_json=json.dumps(
                    {
                        "template_key": template.key,
                        "template_label": self._response_template_label(response_template_key, template.label),
                        "template_key": response_template_key,
                        **filtered,
                    },
                    ensure_ascii=False,
                ),
            )
            self.db.add(knowledge_card)
            self.db.flush()
            record = subject.build_record(knowledge_card.id, extracted)
            if record is not None:
                self.db.add(record)
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
            existing_title_keys.add(title_key)
        return generated_cards

    def _extract_acupuncture_payload(self, template_key: str, text: str) -> dict:
        if template_key == "acupoint_knowledge":
            return clean_acupuncture_card_payload(llm_service.extract_acupuncture_card(text), source_text=text)
        if template_key == "needling_technique":
            return clean_needling_technique_payload(llm_service.extract_needling_technique_card(text), source_text=text)
        return clean_clinical_card_payload(llm_service.extract_acupuncture_clinical_card(text), source_text=text)

    def _resolve_acupuncture_title(self, template_key: str, payload: dict) -> str:
        if template_key == "acupoint_knowledge":
            return payload.get("acupoint_name") or "未知穴位"
        if template_key == "needling_technique":
            return payload.get("technique_name") or "未知技术"
        return payload.get("disease_name") or "未知病证"

    def _passes_acupuncture_quality_gate(self, template_key: str, payload: dict) -> bool:
        if template_key == "acupoint_knowledge":
            return is_valid_acupuncture_card_payload(payload)
        if template_key == "needling_technique":
            return is_valid_needling_technique_payload(payload)
        return is_valid_clinical_card_payload(payload)

    def _add_acupuncture_typed_record(self, knowledge_card_id: int, template_key: str, payload: dict) -> None:
        if template_key == "acupoint_knowledge":
            self.db.add(
                AcupointKnowledgeCard(
                    knowledge_card_id=knowledge_card_id,
                    acupoint_name=payload.get("acupoint_name") or "未知穴位",
                    meridian=payload.get("meridian"),
                    acupoint_property=payload.get("acupoint_property"),
                    location=payload.get("location"),
                    indication=payload.get("indication"),
                    technique=payload.get("technique"),
                    caution=payload.get("caution"),
                )
            )
            return
        if template_key == "needling_technique":
            self.db.add(
                NeedlingTechniqueCard(
                    knowledge_card_id=knowledge_card_id,
                    technique_name=payload.get("technique_name") or "未知技术",
                    section_title=payload.get("section_title"),
                    definition_or_scope=payload.get("definition_or_scope"),
                    key_points=payload.get("key_points"),
                    indications=payload.get("indications"),
                    contraindications=payload.get("contraindications"),
                    notes=payload.get("notes"),
                )
            )
            return
        self.db.add(
            ConditionTreatmentCard(
                knowledge_card_id=knowledge_card_id,
                disease_name=payload.get("disease_name") or "未知病证",
                pattern_name=payload.get("pattern_name"),
                treatment_principle=payload.get("treatment_principle"),
                acupoint_prescription=payload.get("acupoint_prescription"),
                modifications=payload.get("modifications"),
                notes=payload.get("notes"),
            )
        )

    def _remove_existing_cards(self, document_id: int, template_key: str) -> None:
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
        cards = (
            self.db.query(KnowledgeCard.title)
            .filter(
                KnowledgeCard.collection_id == collection_id,
                KnowledgeCard.category == template_key,
                KnowledgeCard.source_document_id != exclude_document_id,
            )
            .all()
        )
        return {key for (title,) in cards if (key := self._normalize_title_key(title))}

    def _normalize_title_key(self, title: str | None) -> str:
        if not title:
            return ""
        normalized = re.sub(r"\s+", "", title)
        normalized = re.sub(r"[（(].*?[）)]", "", normalized)
        normalized = re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9]", "", normalized)
        return normalized.lower()

    def _document_has_matching_units(self, document: SourceDocument, template_key: str) -> bool:
        """Return whether the document had any matching extraction input."""
        unit_type = self._TEMPLATE_UNIT_TYPE.get(template_key)
        if unit_type:
            return any(unit.unit_type == unit_type for unit in document.parsed_units)
        return bool(document.chunks)

    def _response_template_label(self, template_key: str, default_label: str) -> str:
        """Preserve legacy labels for legacy request keys."""
        return {
            "acupoint_foundation": "穴位基础卡",
            "acupoint_review": "穴位复习卡",
            "clinical_treatment": "病证治疗卡",
            "theory_review": "总论高频卡",
        }.get(template_key, default_label)

    def _passes_subject_quality_gate(
        self,
        subject_key: str,
        template_key: str,
        title: str,
        extracted: dict,
    ) -> bool:
        """Backward-compatible quality gate used by older tests."""
        if subject_key != "acupuncture":
            return True
        template_key = {
            "clinical_treatment": "condition_treatment",
            "acupoint_foundation": "acupoint_knowledge",
            "acupoint_review": "acupoint_knowledge",
            "theory_review": "needling_technique",
        }.get(template_key, template_key)
        payload = dict(extracted)
        if template_key == "acupoint_knowledge":
            payload["acupoint_name"] = title
        elif template_key == "needling_technique":
            payload["technique_name"] = title
        else:
            payload["disease_name"] = title
        return self._passes_acupuncture_quality_gate(template_key, payload)

    def _build_clinical_treatment_units(self, chunks: list) -> list[_UnitPayload]:
        """Backward-compatible helper for spanning treatment chunks."""
        units: list[_UnitPayload] = []
        current_heading: str | None = None
        current_parts: list[str] = []
        current_chunk_id: int | None = None
        current_page_number: int | None = None

        for chunk in chunks:
            heading = self._extract_condition_heading(chunk.content)
            if heading:
                if current_heading and current_parts and current_chunk_id is not None and current_page_number is not None:
                    combined = "\n".join(current_parts).strip()
                    if self._looks_like_condition_payload(combined):
                        units.append(
                            _UnitPayload(
                                unit_id=current_chunk_id,
                                page_number_start=current_page_number,
                                source_heading=current_heading,
                                source_text=combined,
                                unit_type="condition_entry",
                            )
                        )
                current_heading = heading
                current_parts = [chunk.content.strip()]
                current_chunk_id = chunk.id
                current_page_number = chunk.page_number
                continue
            if current_heading:
                current_parts.append(chunk.content.strip())

        if current_heading and current_parts and current_chunk_id is not None and current_page_number is not None:
            combined = "\n".join(current_parts).strip()
            if self._looks_like_condition_payload(combined):
                units.append(
                    _UnitPayload(
                        unit_id=current_chunk_id,
                        page_number_start=current_page_number,
                        source_heading=current_heading,
                        source_text=combined,
                        unit_type="condition_entry",
                    )
                )
        return units

    def _extract_condition_heading(self, text: str) -> str | None:
        compact = re.sub(r"\s+", " ", text).strip()
        match = re.search(
            r"(?:^|[。；\s])(?:第[一二三四五六七八九十百]+[章节]\s*[^\s]{0,12}\s+)?(?:[一二三四五六七八九十百]+[、\.．]|\d+[、\.．])?\s*([\u4e00-\u9fa5]{2,20}(?:病|证|症|综合征|痹|痛|瘫|聋|哮|痫|闭经|带下|遗尿|呕吐|泄泻))",
            compact,
        )
        if match:
            return match.group(1)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return None
        for line in lines[:2]:
            candidate = re.sub(r"^第[一二三四五六七八九十百]+章\s*", "", line).strip()
            if re.fullmatch(r"[\u4e00-\u9fa5]{2,20}(?:病|证|症|综合征|痹|痛|瘫|聋|哮|痫|闭经|带下|遗尿|呕吐|泄泻)", candidate):
                return candidate
        return None

    def _looks_like_condition_payload(self, text: str) -> bool:
        return bool(
            re.search(r"(治法|治则|治疗原则|辨证论治)", text)
            and re.search(r"(处方|取穴|主穴|配穴|选穴|基本处方)", text)
        )


def create_card_generator(db: Session) -> CardGenerator:
    """Factory function to create CardGenerator."""
    return CardGenerator(db)
