"""Structure-aware OCR parsing for 《临床针灸学》."""
from __future__ import annotations

from dataclasses import dataclass
import re


PARSER_VERSION = "clinical-acupuncture-v1"
SOURCE_BOOK_KEY = "clinical_acupuncture"
SOURCE_BOOK_LABEL = "临床针灸学"


@dataclass(frozen=True)
class SectionClassification:
    """Document or page-level section classification result."""

    source_book_key: str
    book_section: str | None
    confidence: str
    reason: str


@dataclass(frozen=True)
class PageAnalysis:
    """A classified OCR page."""

    page_number: int
    raw_text: str
    page_kind: str
    book_section: str | None
    quality_flags: tuple[str, ...]


@dataclass(frozen=True)
class BlockCandidate:
    """One OCR block candidate."""

    page_number: int
    block_type: str
    text: str
    sequence_no: int


@dataclass(frozen=True)
class ParsedUnitCandidate:
    """One parsed-document unit candidate."""

    page_number_start: int
    page_number_end: int
    book_section: str | None
    unit_type: str
    source_heading: str | None
    source_text: str
    sequence_no: int
    validation_state: str = "valid"


class ClinicalAcupunctureSectionClassifier:
    """Classify 《临床针灸学》 source sections from file name and content."""

    _SECTION_PATTERNS = {
        "meridian_acupoints": (
            r"经络",
            r"腧穴",
            r"经穴",
            r"定位",
            r"主治",
            r"刺灸",
            r"手太阴",
            r"足阳明",
            r"表3-",
        ),
        "needling_techniques": (
            r"毫针",
            r"灸法",
            r"拔罐",
            r"耳针",
            r"头针",
            r"电针",
            r"操作方法",
            r"适应证",
            r"禁忌",
            r"刺法",
            r"定义",
            r"概念",
            r"原则",
            r"特点",
            r"临床应用",
            r"考试要点",
            r"特定穴",
        ),
        "treatment": (
            r"病症",
            r"病证",
            r"治法",
            r"处方",
            r"主穴",
            r"配穴",
            r"加减",
            r"按语",
            r"治疗方案",
        ),
    }

    def classify_document(self, file_name: str | None, text: str | None = None) -> SectionClassification:
        """Classify one imported source document."""
        file_section = self._guess_section(file_name or "")
        text_section = self._guess_section(text or "")
        if text_section:
            confidence = "high" if file_section in {None, text_section} else "medium"
            reason = "content" if file_section in {None, text_section} else "content_overrode_filename"
            return SectionClassification(
                source_book_key=SOURCE_BOOK_KEY,
                book_section=text_section,
                confidence=confidence,
                reason=reason,
            )
        if file_section:
            return SectionClassification(
                source_book_key=SOURCE_BOOK_KEY,
                book_section=file_section,
                confidence="medium",
                reason="filename",
            )
        return SectionClassification(
            source_book_key=SOURCE_BOOK_KEY,
            book_section=None,
            confidence="low",
            reason="unclassified",
        )

    def classify_page(
        self,
        page_number: int,
        text: str,
        *,
        fallback_section: str | None = None,
    ) -> PageAnalysis:
        """Classify one OCR page."""
        compact = re.sub(r"\s+", " ", text).strip()
        quality_flags: list[str] = []
        if len(compact) < 20:
            quality_flags.append("low_text_density")
        if len(re.findall(r"[A-Za-z0-9]{6,}", compact)) >= 3:
            quality_flags.append("ocr_noise")

        page_kind = self._classify_page_kind(compact)
        page_section = self._guess_section(compact) or fallback_section
        if page_section is None:
            quality_flags.append("needs_review")

        return PageAnalysis(
            page_number=page_number,
            raw_text=text.strip(),
            page_kind=page_kind,
            book_section=page_section,
            quality_flags=tuple(quality_flags),
        )

    def _guess_section(self, text: str) -> str | None:
        normalized = re.sub(r"\s+", " ", str(text or "")).strip()
        if not normalized:
            return None

        scores = {
            section: sum(1 for pattern in patterns if re.search(pattern, normalized))
            for section, patterns in self._SECTION_PATTERNS.items()
        }
        if scores["needling_techniques"] and not re.search(r"(处方|主穴|配穴|基本处方)", normalized):
            scores["needling_techniques"] += 2
        best_section, score = max(scores.items(), key=lambda item: item[1])
        return best_section if score > 0 else None

    def _classify_page_kind(self, text: str) -> str:
        if not text:
            return "noise"
        if "目录" in text and len(re.findall(r"第[一二三四五六七八九十]+", text)) >= 2:
            return "toc"
        has_table = any(token in text for token in ("序号", "穴名", "定位", "主治", "刺灸", "备注", "续表"))
        has_table_rows = len(
            re.findall(r"(?<!\d)(?:[1-9]|1\d|2\d|3\d|4\d|5\d)\s+[\u4e00-\u9fa5]{2,5}\s+", text)
        ) >= 2
        has_heading = bool(re.search(r"(第[一二三四五六七八九十百]+[章节]|[一二三四五六七八九十]+、|（[一二三四五六七八九十]+）)", text))
        if has_table and has_table_rows and has_heading:
            return "mixed"
        if has_table and has_table_rows:
            return "table"
        if any(token in text for token in ("版权", "参考文献", "编写说明", "前言")):
            return "noise"
        return "prose"


class OCRBlockBuilder:
    """Build coarse OCR blocks from page text."""

    def build_blocks(self, page: PageAnalysis) -> list[BlockCandidate]:
        """Split one page into OCR blocks."""
        text = self._strip_noise(page.raw_text)
        if not text:
            return []

        blocks: list[BlockCandidate] = []
        sequence_no = 1

        if page.page_kind in {"table", "mixed"}:
            table_region = self._extract_table_region(text)
            if table_region:
                blocks.append(
                    BlockCandidate(
                        page_number=page.page_number,
                        block_type="table_region",
                        text=table_region,
                        sequence_no=sequence_no,
                    )
                )
                sequence_no += 1
                text = text.replace(table_region, " ")

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            lines = [part.strip() for part in re.split(r"\s{2,}", text) if part.strip()]

        paragraph_buffer: list[str] = []
        for line in lines:
            if self._looks_like_heading(line):
                if paragraph_buffer:
                    blocks.append(
                        BlockCandidate(
                            page_number=page.page_number,
                            block_type="paragraph",
                            text=" ".join(paragraph_buffer).strip(),
                            sequence_no=sequence_no,
                        )
                    )
                    sequence_no += 1
                    paragraph_buffer = []
                blocks.append(
                    BlockCandidate(
                        page_number=page.page_number,
                        block_type="heading",
                        text=line,
                        sequence_no=sequence_no,
                    )
                )
                sequence_no += 1
                continue
            paragraph_buffer.append(line)

        if paragraph_buffer:
            blocks.append(
                BlockCandidate(
                    page_number=page.page_number,
                    block_type="paragraph",
                    text=" ".join(paragraph_buffer).strip(),
                    sequence_no=sequence_no,
                )
            )

        return blocks

    def _strip_noise(self, text: str) -> str:
        normalized = str(text or "").replace("\r", "\n")
        cleaned_lines: list[str] = []
        for raw_line in normalized.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if re.fullmatch(r"\d{1,4}", line):
                continue
            if re.match(r"^图\s*\d", line):
                continue
            if any(token in line for token in ("经穴歌", "口诀", "版权页")):
                line = re.split(r"(?:图\s*\d|经穴歌|口诀|版权页)", line, maxsplit=1)[0].strip()
                if not line:
                    continue
            cleaned_lines.append(line)
        return "\n".join(cleaned_lines).strip()

    def _looks_like_heading(self, line: str) -> bool:
        if any(
            token in line
            for token in (
                "：",
                ":",
                "定位",
                "主治",
                "经络",
                "归经",
                "操作",
                "刺灸法",
                "注意",
                "禁忌",
                "治法",
                "处方",
                "主穴",
                "配穴",
                "加减",
                "定义",
                "概念",
            )
        ):
            return False
        return bool(
            re.match(r"^(第[一二三四五六七八九十百]+[章节]|第[一二三四五六七八九十百]+节|[一二三四五六七八九十]+、|（[一二三四五六七八九十]+）)", line)
            or (len(line) <= 18 and not any(token in line for token in ("定位", "主治", "处方", "治法")))
        )

    def _extract_table_region(self, text: str) -> str | None:
        compact = re.sub(r"\s+", " ", text).strip()
        if "序号" not in compact and "穴名" not in compact:
            return None
        return compact


class MeridianAcupointParser:
    """Parse meridian/acupoint OCR units."""

    _MERIDIAN_PATTERN = re.compile(
        r"(手太阴肺经|手阳明大肠经|足阳明胃经|足太阴脾经|手少阴心经|手太阳小肠经|"
        r"足太阳膀胱经|足少阴肾经|手厥阴心包经|手少阳三焦经|足少阳胆经|足厥阴肝经|"
        r"督脉|任脉)"
    )

    def parse(self, pages: list[PageAnalysis], blocks: list[BlockCandidate]) -> list[ParsedUnitCandidate]:
        """Build one unit per acupoint entry."""
        units: list[ParsedUnitCandidate] = []
        sequence_no = 1
        current_meridian: str | None = None
        pending_heading: str | None = None

        for block in blocks:
            if block.block_type == "heading":
                meridian_match = self._MERIDIAN_PATTERN.search(block.text)
                if meridian_match:
                    current_meridian = meridian_match.group(1)
                    pending_heading = None
                    continue
                pending_heading = block.text.strip()
                continue
            if block.block_type == "table_region":
                table_units = self._parse_table_block(block, current_meridian)
                for unit in table_units:
                    units.append(
                        ParsedUnitCandidate(
                            page_number_start=block.page_number,
                            page_number_end=block.page_number,
                            book_section="meridian_acupoints",
                            unit_type="acupoint_entry",
                            source_heading=unit.source_heading,
                            source_text=unit.source_text,
                            sequence_no=sequence_no,
                        )
                )
                    sequence_no += 1
                continue

            if pending_heading and any(token in block.text for token in ("定位", "主治", "刺灸法", "操作")):
                payload = f"{pending_heading}\n{block.text}".strip()
                if current_meridian and "经络" not in payload:
                    payload = f"{pending_heading}\n经络：{current_meridian}\n{block.text}".strip()
                units.append(
                    ParsedUnitCandidate(
                        page_number_start=block.page_number,
                        page_number_end=block.page_number,
                        book_section="meridian_acupoints",
                        unit_type="acupoint_entry",
                        source_heading=pending_heading.removesuffix("穴"),
                        source_text=payload,
                        sequence_no=sequence_no,
                    )
                )
                sequence_no += 1
                pending_heading = None
                continue

            paragraph_units = self._parse_paragraph_block(block, current_meridian)
            for unit in paragraph_units:
                units.append(
                    ParsedUnitCandidate(
                        page_number_start=block.page_number,
                        page_number_end=block.page_number,
                        book_section="meridian_acupoints",
                        unit_type="acupoint_entry",
                        source_heading=unit.source_heading,
                        source_text=unit.source_text,
                        sequence_no=sequence_no,
                    )
                )
                sequence_no += 1
            pending_heading = None
        return units

    def _parse_table_block(
        self,
        block: BlockCandidate,
        meridian: str | None,
    ) -> list[ParsedUnitCandidate]:
        text = block.text
        header_meridian = self._extract_meridian(text) or meridian
        row_matches = list(
            re.finditer(r"(?<!\d)(?:[1-9]|1\d|2\d|3\d|4\d|5\d)\s+([\u4e00-\u9fa5]{2,5})\s+", text)
        )
        if len(row_matches) < 1:
            return []
        units: list[ParsedUnitCandidate] = []
        for index, match in enumerate(row_matches):
            row_name = match.group(1)
            start = match.start()
            end = row_matches[index + 1].start() if index + 1 < len(row_matches) else len(text)
            row_text = text[start:end].strip(" ；;。")
            header = row_name
            row_text = self._build_table_row_payload(row_name, row_text, header_meridian)
            units.append(
                ParsedUnitCandidate(
                    page_number_start=block.page_number,
                    page_number_end=block.page_number,
                    book_section="meridian_acupoints",
                    unit_type="acupoint_entry",
                    source_heading=header,
                    source_text=row_text,
                    sequence_no=0,
                )
            )
        return units

    def _build_table_row_payload(self, row_name: str, row_text: str, meridian: str | None) -> str:
        body = re.sub(
            rf"^(?:(?:[1-9]|1\d|2\d|3\d|4\d|5\d)\s+)?{re.escape(row_name)}\s*",
            "",
            row_text,
        ).strip()
        properties = re.findall(
            r"(井穴|荥穴|荣穴|输穴|俞穴|原穴|经穴|合穴|络穴|郄穴|募穴|下合穴|交会穴|八会穴|八脉交会穴)",
            body,
        )
        while True:
            updated = re.sub(
                r"^(?:井穴|荥穴|荣穴|输穴|俞穴|原穴|经穴|合穴|络穴|郄穴|募穴|下合穴|交会穴|八会穴|八脉交会穴|通[\u4e00-\u9fa5]{1,6}脉)(?:[；;、，,\s]+|$)",
                "",
                body,
            ).strip()
            if updated == body:
                break
            body = updated
        location, indication, technique, caution = self._split_table_body(body)
        parts = [row_name]
        if meridian:
            parts.append(f"【经络】{meridian}")
        if properties:
            parts.append(f"【穴性】{'、'.join(dict.fromkeys(properties))}")
        if location:
            parts.append(f"【定位】{location}")
        if indication:
            parts.append(f"【主治】{indication}")
        if technique:
            parts.append(f"【操作】{technique}")
        if caution:
            parts.append(f"【注意】{caution}")
        return " ".join(parts)

    def _split_table_body(self, body: str) -> tuple[str | None, str | None, str | None, str | None]:
        technique_match = re.search(
            r"(浅刺|直刺|斜刺|平刺|横刺|点刺|可点刺出血|可灸|艾炷灸|温针灸)[^。；;]{0,40}",
            body,
        )
        technique = None
        caution = None
        prefix = body
        if technique_match:
            prefix = body[: technique_match.start()].strip(" ；;。")
            tail = body[technique_match.start() :].strip(" ；;。")
            extra_technique = re.search(r"(可点刺出血|可灸|艾炷灸|温针灸)$", tail)
            if extra_technique and extra_technique.start() > 0:
                tail = tail[: extra_technique.end()]
            caution_match = re.search(r"(孕妇[^。；;]*|针刺[^。；;]*避开[^。；;]*|慎用[^。；;]*)$", tail)
            if caution_match:
                caution = caution_match.group(1).strip(" ；;。")
                tail = tail[: caution_match.start()].strip(" ；;。")
            technique = tail or None

        disease_marker = re.search(
            r"(肺系|头痛|目赤|齿痛|咽喉|中暑|急救|急性|偏头痛|瘰疬|胸胁痛|目眩|瘿气|项强|肩背痛|目赤肿痛|癫狂痫|无脉症|干呕)",
            prefix,
        )
        if disease_marker and disease_marker.start() >= 4:
            location = prefix[: disease_marker.start()].strip(" ；;。,:：，,")
            indication = prefix[disease_marker.start() :].strip(" ；;。,:：，,")
        else:
            location = prefix.strip(" ；;。,:：，,")
            indication = None

        if location and not self._looks_like_location(location):
            indication = prefix.strip(" ；;。,:：，,")
            location = None
        return location or None, indication or None, technique, caution

    def _looks_like_location(self, text: str) -> bool:
        return bool(
            re.search(
                r"(在|当|于|上肢|前臂|腕|掌|手|足|头部|面部|胸部|腹部|背部|肩|颈|肘|膝|踝|横纹|凹陷|肌|骨|肉际|关节|上方|下方|中点|之间|处)",
                text,
            )
        )

    def _extract_meridian(self, text: str) -> str | None:
        match = self._MERIDIAN_PATTERN.search(text)
        return match.group(1) if match else None

    def _parse_paragraph_block(
        self,
        block: BlockCandidate,
        meridian: str | None,
    ) -> list[ParsedUnitCandidate]:
        compact = re.sub(r"\s+", " ", block.text).strip()
        starts = list(
            re.finditer(
                r"(?:^|[。；;\s])\d+\.\s*([\u4e00-\u9fa5]{1,8})(?:\*|\s)*\([^)]*[A-Za-z]{1,3}\s*\d+[^)]*\)",
                compact,
            )
        )
        if not starts:
            labeled_blocks = self._parse_labeled_entries(block, meridian)
            if labeled_blocks:
                return labeled_blocks
            return []
        units: list[ParsedUnitCandidate] = []
        for index, match in enumerate(starts):
            start = match.start()
            if compact[start].isspace():
                start += 1
            end = starts[index + 1].start() if index + 1 < len(starts) else len(compact)
            part = compact[start:end].strip()
            heading = match.group(1)
            if meridian and "经络" not in part:
                part = f"{part} 【经络】{meridian}"
            units.append(
                ParsedUnitCandidate(
                    page_number_start=block.page_number,
                    page_number_end=block.page_number,
                    book_section="meridian_acupoints",
                    unit_type="acupoint_entry",
                    source_heading=heading,
                    source_text=part,
                    sequence_no=0,
                )
            )
        return units

    def _parse_labeled_entries(
        self,
        block: BlockCandidate,
        meridian: str | None,
    ) -> list[ParsedUnitCandidate]:
        text = block.text.strip()
        if not text or "定位" not in text:
            return []
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", text) if part.strip()]
        if not paragraphs:
            paragraphs = [text]
        units: list[ParsedUnitCandidate] = []
        for paragraph in paragraphs:
            lines = [line.strip() for line in paragraph.splitlines() if line.strip()]
            if not lines:
                continue
            header = lines[0]
            if header.endswith("穴"):
                header = header[:-1]
            if not re.fullmatch(r"[\u4e00-\u9fa5]{2,5}", header):
                continue
            payload = paragraph
            if meridian and "经络" not in paragraph:
                payload = f"{header}\n经络：{meridian}\n" + "\n".join(lines[1:])
            units.append(
                ParsedUnitCandidate(
                    page_number_start=block.page_number,
                    page_number_end=block.page_number,
                    book_section="meridian_acupoints",
                    unit_type="acupoint_entry",
                    source_heading=header,
                    source_text=payload.strip(),
                    sequence_no=0,
                )
            )
        return units


class NeedlingTechniqueParser:
    """Parse technique-topic OCR units."""

    def parse(self, blocks: list[BlockCandidate]) -> list[ParsedUnitCandidate]:
        """Build one unit per technique topic."""
        units: list[ParsedUnitCandidate] = []
        current_heading: str | None = None
        current_parts: list[str] = []
        start_page: int | None = None
        sequence_no = 1

        for block in blocks:
            if block.block_type == "heading":
                if current_heading and current_parts and start_page is not None:
                    units.append(
                        ParsedUnitCandidate(
                            page_number_start=start_page,
                            page_number_end=block.page_number,
                            book_section="needling_techniques",
                            unit_type="technique_topic",
                            source_heading=current_heading,
                            source_text="\n".join(current_parts).strip(),
                            sequence_no=sequence_no,
                        )
                    )
                    sequence_no += 1
                current_heading = block.text
                current_parts = [block.text]
                start_page = block.page_number
                continue
            if current_heading is None:
                if self._looks_like_technique_topic(block.text):
                    current_heading = self._extract_technique_heading(block.text)
                    current_parts = [block.text]
                    start_page = block.page_number
                continue
            current_parts.append(block.text)

        if current_heading and current_parts and start_page is not None:
            units.append(
                ParsedUnitCandidate(
                    page_number_start=start_page,
                    page_number_end=blocks[-1].page_number if blocks else start_page,
                    book_section="needling_techniques",
                    unit_type="technique_topic",
                    source_heading=current_heading,
                    source_text="\n".join(current_parts).strip(),
                    sequence_no=sequence_no,
                )
            )
        return [unit for unit in units if self._looks_like_technique_topic(unit.source_text)]

    def _looks_like_technique_topic(self, text: str) -> bool:
        return any(
            token in text
            for token in (
                "毫针",
                "灸法",
                "拔罐",
                "耳针",
                "头针",
                "电针",
                "适应证",
                "禁忌",
                "定义",
                "概念",
                "原则",
                "特点",
                "临床应用",
                "考试要点",
                "特定穴",
                "定位法",
            )
        )

    def _extract_technique_heading(self, text: str) -> str:
        match = re.search(
            r"([\u4e00-\u9fa5]{2,16}(?:针法|灸法|拔罐法|耳针法|头针法|电针法|毫针法|原则|作用|特点|应用|定位法|处方|特定穴))",
            text,
        )
        return match.group(1) if match else text[:20]


class TreatmentChapterParser:
    """Parse treatment-topic OCR units."""

    def parse(self, blocks: list[BlockCandidate]) -> list[ParsedUnitCandidate]:
        """Build one unit per condition-treatment topic."""
        units: list[ParsedUnitCandidate] = []
        current_heading: str | None = None
        current_parts: list[str] = []
        start_page: int | None = None
        sequence_no = 1

        for block in blocks:
            heading = self._extract_condition_heading(block.text)
            if block.block_type == "heading" and heading:
                if current_heading and current_parts and start_page is not None:
                    units.append(
                        ParsedUnitCandidate(
                            page_number_start=start_page,
                            page_number_end=block.page_number,
                            book_section="treatment",
                            unit_type="condition_entry",
                            source_heading=current_heading,
                            source_text="\n".join(current_parts).strip(),
                            sequence_no=sequence_no,
                        )
                    )
                    sequence_no += 1
                current_heading = heading
                current_parts = [block.text]
                start_page = block.page_number
                continue

            if current_heading is None and heading:
                current_heading = heading
                current_parts = [block.text]
                start_page = block.page_number
                continue

            if current_heading is not None:
                current_parts.append(block.text)

        if current_heading and current_parts and start_page is not None:
            units.append(
                ParsedUnitCandidate(
                    page_number_start=start_page,
                    page_number_end=blocks[-1].page_number if blocks else start_page,
                    book_section="treatment",
                    unit_type="condition_entry",
                    source_heading=current_heading,
                    source_text="\n".join(current_parts).strip(),
                    sequence_no=sequence_no,
                )
            )

        return [unit for unit in units if self._is_valid_treatment_unit(unit.source_text)]

    def _extract_condition_heading(self, text: str) -> str | None:
        compact = re.sub(r"\s+", " ", text).strip()
        match = re.search(
            r"(?:^|[。；\s])(?:第[一二三四五六七八九十百]+[章节]\s*[^\s]{0,12}\s+)?(?:[一二三四五六七八九十百]+[、\.．]|\d+[、\.．])?\s*([\u4e00-\u9fa5]{2,20}(?:病|证|症|综合征|痹|痛|瘫|聋|哮|痫|闭经|带下|遗尿|呕吐|泄泻))",
            compact,
        )
        if not match:
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            if lines:
                candidate = re.sub(r"第[一二三四五六七八九十百]+章\s*", "", lines[0]).strip()
                if re.fullmatch(r"[\u4e00-\u9fa5]{2,20}(?:病|证|症|综合征|痹|痛|瘫|聋|哮|痫|闭经|带下|遗尿|呕吐|泄泻)", candidate):
                    return candidate
        return match.group(1) if match else None

    def _is_valid_treatment_unit(self, text: str) -> bool:
        return bool(
            re.search(r"(治法|治则|治疗原则|辨证论治)", text)
            and re.search(r"(处方|取穴|主穴|配穴|选穴|基本处方)", text)
        )
