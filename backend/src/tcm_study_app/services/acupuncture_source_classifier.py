"""Helpers for classifying 《临床针灸学》 OCR sources."""
from __future__ import annotations

from dataclasses import dataclass
import re

from tcm_study_app.services.clinical_acupuncture_parser import (
    ClinicalAcupunctureSectionClassifier,
    SOURCE_BOOK_LABEL,
)


@dataclass(frozen=True)
class AcupunctureSourceMeta:
    """Derived metadata for one clinical acupuncture source."""

    book_key: str
    book_label: str
    book_part: str | None
    source_style: str


_classifier = ClinicalAcupunctureSectionClassifier()


def classify_acupuncture_source(
    file_name: str | None,
    *,
    text: str | None = None,
) -> AcupunctureSourceMeta:
    """Classify a document into section-aware clinical acupuncture metadata."""
    normalized_name = str(file_name or "")
    is_clinical = _is_clinical_book_name(normalized_name)
    section = _classifier.classify_document(file_name, text=text)
    source_style = detect_acupuncture_source_style(text or file_name)
    return AcupunctureSourceMeta(
        book_key="clinical_acupuncture" if is_clinical else "standard_acupuncture",
        book_label=SOURCE_BOOK_LABEL if is_clinical else "针灸学",
        book_part=_book_part_label(section.book_section) if is_clinical else None,
        source_style=source_style,
    )


def is_clinical_acupuncture_source(file_name: str | None) -> bool:
    """Return whether the source is treated as 《临床针灸学》."""
    return _is_clinical_book_name(str(file_name or ""))


def detect_acupuncture_source_style(text: str | None) -> str:
    """Classify the OCR style for one source snippet."""
    normalized = " ".join(str(text or "").split())
    if not normalized:
        return "prose"
    if any(token in normalized for token in ("序号", "穴名", "定位", "主治", "刺灸")):
        return "table"
    if "图" in normalized and any(token in normalized for token in ("图示", "穴图", "经穴图")):
        return "diagram"
    return "prose"


def _book_part_label(book_section: str | None) -> str | None:
    return {
        "meridian_acupoints": "经络腧穴篇",
        "needling_techniques": "刺灸技术篇",
        "treatment": "针灸治疗篇",
    }.get(book_section)


def _is_clinical_book_name(file_name: str) -> bool:
    normalized = str(file_name or "")
    if "临床针灸学" in normalized:
        return True
    if re.match(r"^\d{3}_", normalized):
        return False
    if re.match(r"^\d{2}_", normalized):
        return True
    if any(token in normalized for token in ("病症", "病证", "针灸治疗", "经络腧穴", "刺灸技术", "表3-")):
        return True
    return False
