"""Cleanup helpers for acupuncture theory/general-review cards."""
from __future__ import annotations

import re

_KNOWN_THEORY_TITLES = (
    "针灸治疗作用",
    "针灸治疗原则",
    "针灸处方",
    "补虚泻实原则",
    "治病求本原则",
    "三因制宜原则",
    "近部选穴",
    "远部选穴",
    "辨证选穴",
    "对证选穴",
    "特定穴的临床应用",
    "五输穴",
    "原穴",
    "络穴",
    "募穴",
    "下合穴",
    "八会穴",
    "八脉交会穴",
    "交会穴",
    "腧穴定位法",
    "骨度分寸定位法",
    "手指同身寸定位法",
    "自然标志定位法",
    "针刺注意事项",
    "毫针刺法",
    "灸法",
    "拔罐法",
    "耳针法",
    "头针法",
    "电针法",
    "治疗特点",
    "临床治法特点",
)
_BLOCKED_EXACT = (
    "背部穴",
    "经络输穴",
    "临床应用",
    "绿色疗法",
    "发挥自身调节作用",
    "穿透力强等特点",
    "面颊及耳前后部位脸穴",
    "也体现了近部选穴的原则",
    "在针灸临床上补虚泻实原则",
    "证选穴原则",
)
_BLOCKED_SUBSTRINGS = (
    "针灸学",
    "图",
    "第",
    "页",
    "定位】",
    "主治】",
    "操作】",
    "解剖】",
)


def _clean_text(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip(" ；;。,:：、[]【】")
    return cleaned or None


def _looks_like_valid_concept_name(name: str | None) -> bool:
    if not name:
        return False
    cleaned = re.sub(r"\s+", "", name)
    if not 2 <= len(cleaned) <= 12:
        return False
    if re.search(r"[0-9A-Za-z]", cleaned):
        return False
    if cleaned in _BLOCKED_EXACT:
        return False
    if any(token in cleaned for token in _BLOCKED_SUBSTRINGS):
        return False
    return True


def clean_theory_card_payload(
    payload: dict[str, str | None],
    *,
    source_text: str | None = None,
) -> dict[str, str | None]:
    """Normalize theory card fields and recover a stable concept name."""
    concept_name = _clean_text(payload.get("concept_name"))

    if source_text:
        compact = re.sub(r"\s+", " ", source_text)
        if not _looks_like_valid_concept_name(concept_name):
            for term in _KNOWN_THEORY_TITLES:
                if term in compact:
                    concept_name = term
                    break

    cleaned = {
        "concept_name": concept_name,
        "category": _clean_text(payload.get("category")),
        "core_points": _clean_text(payload.get("core_points")),
        "exam_focus": _clean_text(payload.get("exam_focus")),
    }
    return cleaned


def is_valid_theory_card_payload(payload: dict[str, str | None]) -> bool:
    """Reject noisy theory cards and require useful content."""
    return _looks_like_valid_concept_name(payload.get("concept_name")) and any(
        payload.get(field) for field in ("core_points", "exam_focus", "category")
    )
