"""Helpers for classifying acupuncture OCR sources and styles."""
from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class AcupunctureSourceMeta:
    """Derived metadata for an acupuncture source document or chunk."""

    book_key: str
    book_label: str
    book_part: str | None
    source_style: str


_CLINICAL_BOOK_LABEL = "临床针灸学"
_STANDARD_BOOK_LABEL = "针灸学"


def classify_acupuncture_source(
    file_name: str | None,
    *,
    text: str | None = None,
) -> AcupunctureSourceMeta:
    """Classify one acupuncture document into source book, part, and content style."""
    normalized_name = str(file_name or "")
    book_key = _infer_book_key(normalized_name)
    book_label = _CLINICAL_BOOK_LABEL if book_key == "clinical_acupuncture" else _STANDARD_BOOK_LABEL
    book_part = _infer_book_part(normalized_name) if book_key == "clinical_acupuncture" else None
    source_style = detect_acupuncture_source_style(text or normalized_name)
    return AcupunctureSourceMeta(
        book_key=book_key,
        book_label=book_label,
        book_part=book_part,
        source_style=source_style,
    )


def is_clinical_acupuncture_source(file_name: str | None) -> bool:
    """Return whether a source document belongs to 《临床针灸学》."""
    return _infer_book_key(str(file_name or "")) == "clinical_acupuncture"


def detect_acupuncture_source_style(text: str | None) -> str:
    """Classify the extraction style for one source snippet."""
    normalized = re.sub(r"\s+", " ", str(text or "")).strip()
    if not normalized:
        return "prose"
    table_head_markers = ("表3-", "续表", "序号", "穴名", "刺灸")
    row_count = len(
        re.findall(r"(?<!\d)(?:[1-9]|1\d|2\d|3\d|4\d|5\d)\s+[\u4e00-\u9fa5]{2,5}\s+", normalized)
    )
    if any(token in normalized for token in table_head_markers) and (
        "穴名" in normalized or "序号" in normalized or row_count >= 2
    ):
        return "table"
    if "图" in normalized and any(token in normalized for token in ("穴图", "经穴图", "图3-", "图示")):
        return "diagram"
    return "prose"


def _infer_book_key(file_name: str) -> str:
    """Heuristically distinguish 《临床针灸学》 from the other acupuncture textbook."""
    if re.match(r"^\d{3}_", file_name):
        return "standard_acupuncture"
    if re.match(r"^\d{2}_", file_name):
        return "clinical_acupuncture"
    if "临床针灸学" in file_name:
        return "clinical_acupuncture"
    return "standard_acupuncture"


def _infer_book_part(file_name: str) -> str | None:
    """Map clinical chapter files into 上篇 / 中篇 / 下篇."""
    prefix_match = re.match(r"^(?P<prefix>\d{2})_", file_name)
    if prefix_match:
        index = int(prefix_match.group("prefix"))
        if 1 <= index <= 4:
            return "上篇"
        if 5 <= index <= 8:
            return "中篇"
        if index >= 9:
            return "下篇"

    chapter_match = re.search(r"第(?P<chapter>[一二三四五六七八九十]+)章", file_name)
    if chapter_match:
        chapter_map = {
            "一": 1,
            "二": 2,
            "三": 3,
            "四": 4,
            "五": 5,
            "六": 6,
            "七": 7,
            "八": 8,
            "九": 9,
            "十": 10,
        }
        chapter_number = chapter_map.get(chapter_match.group("chapter"))
        if chapter_number is not None:
            if 1 <= chapter_number <= 4:
                return "上篇"
            if 5 <= chapter_number <= 8:
                return "中篇"
            if chapter_number >= 9:
                return "下篇"
    return None
