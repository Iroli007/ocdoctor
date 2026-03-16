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
from tcm_study_app.services.acupuncture_source_classifier import classify_acupuncture_source
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
        source_meta = (
            classify_acupuncture_source(document.image_url or "", text=document.raw_text)
            if subject.key == "acupuncture"
            else None
        )
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
            if source_meta is not None:
                normalized_content.update(
                    {
                        "_source_book": source_meta.book_label,
                        "_book_part": source_meta.book_part,
                        "_source_style": source_meta.source_style,
                    }
                )

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
        table_blocks = self._split_acupuncture_table_chunk(content)
        if table_blocks:
            return table_blocks

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

    def _split_acupuncture_table_chunk(self, content: str) -> list[str]:
        """Split OCR table pages into one synthetic labeled block per acupoint row."""
        compact = re.sub(r"\s+", " ", content).strip()
        if not compact:
            return []

        if not self._looks_like_acupuncture_table(compact):
            return []

        row_starts = self._find_acupuncture_table_row_starts(compact)
        if len(row_starts) < 2:
            return []

        meridian = self._extract_meridian_from_text(compact)
        blocks: list[str] = []

        for index, row_start in enumerate(row_starts):
            start_index = row_start["start"]
            end_index = row_starts[index + 1]["start"] if index + 1 < len(row_starts) else len(compact)
            row_text = compact[start_index:end_index].strip(" ；;。")
            row_name = row_start["name"]
            if (
                not row_text
                or len(row_text) < 10
                or not self._looks_like_acupuncture_row_name(row_name)
            ):
                continue

            block = self._build_acupuncture_table_row_block(
                row_name=row_name,
                row_text=row_text,
                meridian=meridian,
            )
            if block:
                blocks.append(block)

        return blocks

    def _find_acupuncture_table_row_starts(self, text: str) -> list[dict[str, int | str]]:
        """Find plausible row starts in noisy OCR table text."""
        patterns = (
            re.compile(
                r"(?<!\d)(?:[1-9]|1\d|2\d|3\d|4\d|5\d)\s+(?P<name>[\u4e00-\u9fa5]{2,5})(?=\s)"
            ),
            re.compile(
                r"(?P<name>[\u4e00-\u9fa5]{2,5})\s+"
                r"(?=井穴|荥穴|荣穴|输穴|俞穴|原穴|经穴|合穴|络穴|郄穴|募穴|下合穴|交会穴|"
                r"八会穴|八脉交会穴|通于[\u4e00-\u9fa5]+|通[\u4e00-\u9fa5]{1,4}脉)"
            ),
            re.compile(
                r"(?P<name>[\u4e00-\u9fa5]{2,5})\s+"
                r"(?=在|当|于|上肢|前臂|腕|掌|手|足|头部|面部|胸部|腹部|背部|肩|颈|"
                r"耳后|耳区|眉梢|乳突|肘|膝|踝|趾|指)"
            ),
        )

        starts_by_index: dict[int, dict[str, int | str]] = {}
        for pattern in patterns:
            for match in pattern.finditer(text):
                name = match.group("name")
                if not self._looks_like_acupuncture_row_name(name):
                    continue
                start = match.start("name")
                current = starts_by_index.get(start)
                if current is None or len(str(current["name"])) < len(name):
                    starts_by_index[start] = {"start": start, "name": name}

        return [starts_by_index[index] for index in sorted(starts_by_index)]

    def _looks_like_acupuncture_table(self, text: str) -> bool:
        """Only treat true acupoint tables as acupoint-row sources."""
        if any(marker in text for marker in ("病名", "证型", "治法", "处方", "方药", "病例", "病机")):
            return False

        has_acupoint_markers = any(
            marker in text
            for marker in ("穴名", "腧穴", "俞穴", "经穴", "序号", "刺灸", "定位", "主治")
        )
        has_meridian_context = bool(self._extract_meridian_from_text(text))
        row_count = len(
            list(
                re.finditer(
                    r"(?<!\d)(?:[1-9]|1\d|2\d|3\d|4\d|5\d)\s+[\u4e00-\u9fa5]{2,5}\s+",
                    text,
                )
            )
        )
        return (has_acupoint_markers or has_meridian_context) and row_count >= 3

    def _looks_like_acupuncture_row_name(self, name: str) -> bool:
        """Guard against non-acupoint row titles in mixed tables."""
        cleaned = re.sub(r"\s+", "", name)
        if not 2 <= len(cleaned) <= 4:
            return False
        if any(
            token in cleaned
            for token in (
                "主治",
                "定位",
                "刺灸",
                "注意",
                "病",
                "症",
                "表",
                "图",
                "穴",
                "脉",
                "交会",
                "原穴",
                "经穴",
                "络穴",
                "合穴",
                "井穴",
                "荥穴",
                "荣穴",
                "输穴",
                "俞穴",
                "募穴",
                "郄穴",
                "下合",
            )
        ):
            return False
        return True

    def _build_acupuncture_table_row_block(
        self,
        *,
        row_name: str,
        row_text: str,
        meridian: str | None,
    ) -> str | None:
        """Convert one OCR table row into a labeled pseudo-paragraph for extraction."""
        body = re.sub(
            rf"^(?:(?:[1-9]|1\d|2\d|3\d|4\d|5\d)\s+)?{re.escape(row_name)}\s*",
            "",
            row_text,
        ).strip()
        body = re.sub(
            r"\s+",
            " ",
            body,
        ).strip()
        body = self._strip_acupoint_property_prefix(body)
        body = re.sub(r"\s+", " ", body).strip(" ；;。")
        if not body:
            return None

        technique_matches = list(
            re.finditer(
                r"(?:向外斜刺或平刺|向上平（斜）刺|向上平刺|向后内斜刺|微张口，直刺|"
                r"避开(?:桡动脉|动脉)，(?:直刺|平刺)|浅刺|直刺|斜刺|平刺|横刺|点刺|"
                r"不针不灸|可灸|可用灸法|艾炷灸|温针灸)[^。；;]{0,40}?(?:寸|壮|出血|疗法|不针不灸)",
                body,
            )
        )
        technique = None
        caution = None
        pre_technique = body
        if technique_matches:
            last_match = technique_matches[-1]
            pre_technique = body[: last_match.start()].strip(" ；;。")
            tail = body[last_match.start() :].strip(" ；;。")
            caution_match = re.search(
                r"(孕妇[^。；;]*|针刺[^。；;]*避开[^。；;]*|不可深刺[^。；;]*|慎用[^。；;]*)$",
                tail,
            )
            if caution_match:
                caution = caution_match.group(1).strip(" ；;。")
                caution = re.sub(r"\s+(?:[1-9]|1\d|2\d|3\d|4\d|5\d)$", "", caution).strip()
                tail = tail[: caution_match.start()].strip(" ；;。")
            technique = tail or None

        location, indication = self._split_table_row_location_and_indication(pre_technique)

        parts = [row_name]
        if meridian:
            parts.append(f"【经络】{meridian}")
        if location:
            parts.append(f"【定位】{location}")
        if indication:
            parts.append(f"【主治】{indication}")
        if technique:
            parts.append(f"【操作】{technique}")
        if caution:
            parts.append(f"【注意】{caution}")

        if len(parts) <= 1:
            return None
        return " ".join(parts)

    def _split_table_row_location_and_indication(self, text: str) -> tuple[str | None, str | None]:
        """Best-effort split of a table row into location and indication fields."""
        normalized = re.sub(r"\s+", " ", text).strip(" ；;。")
        if not normalized:
            return None, None

        disease_marker = re.search(
            r"(肺系|胸肺|头面|五官|咳|喘|痛|热病|热证|耳鸣|耳聋|咽喉|齿痛|目赤|目眩|头痛|胸痛|胁肋痛|"
            r"便秘|泄泻|呕吐|呃逆|失眠|心悸|癫|狂|痫|昏迷|惊风|瘰疬|瘿气|疝气|"
            r"月经|带下|遗精|小便|水肿|无脉症|乳痈|乳少|口眼|面瘫|暴喑|喉痹|鼻衄|"
            r"干呕|反胃|痔疾|痢疾|丹毒|脚气|中暑|消渴|肩背痛|腕痛|上臂痛|项强)",
            normalized,
        )
        if disease_marker and disease_marker.start() >= 6:
            location = normalized[: disease_marker.start()].strip(" ；;。,:：，,")
            indication = normalized[disease_marker.start() :].strip(" ；;。,:：，,")
        else:
            location = normalized if self._looks_like_location_text(normalized) else None
            indication = None if location else normalized

        return location or None, indication or None

    def _strip_acupoint_property_prefix(self, text: str) -> str:
        """Strip repeated acupoint-property labels before location text begins."""
        property_pattern = re.compile(
            r"^(?:"
            r"井穴|荥穴|荣穴|输穴|俞穴|原穴|经穴|合穴|络穴|郄穴|募穴|下合穴|交会穴|"
            r"八会穴(?:之脉会)?|八脉交会穴|肺之募穴|胃之下合穴|大肠之下合穴|小肠之下合穴|"
            r"脾之大络|足三阴经交会穴|通于[\u4e00-\u9fa5]+|通[\u4e00-\u9fa5]{1,4}脉|原穴之脉会"
            r")(?:[；;、，,\s]+|$)"
        )
        cleaned = text.strip()
        while True:
            updated = property_pattern.sub("", cleaned).strip()
            if updated == cleaned:
                break
            cleaned = updated
        return cleaned

    def _looks_like_location_text(self, text: str) -> bool:
        """Return whether the fragment looks more like a location than an indication."""
        return bool(
            re.search(
                r"(在|当|于|上肢|前臂|腕|掌|手|足|头部|面部|胸部|腹部|背部|肩|颈|"
                r"耳后|耳区|眉梢|乳突|肘|膝|踝|趾|指|横纹|凹陷|肌|骨|肉际|关节|"
                r"旁开|上方|下方|中央|中点|后缘|前缘|交点处|之间|处)",
                text,
            )
        )

    def _extract_meridian_from_text(self, text: str) -> str | None:
        """Infer the meridian name from a nearby heading when present."""
        match = re.search(
            r"(手太阴肺经|手阳明大肠经|足阳明胃经|足太阴脾经|手少阴心经|手太阳小肠经|"
            r"足太阳膀胱经|足少阴肾经|手厥阴心包经|手少阳三焦经|足少阳胆经|足厥阴肝经|"
            r"督脉|任脉)",
            text,
        )
        return match.group(1) if match else None

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
