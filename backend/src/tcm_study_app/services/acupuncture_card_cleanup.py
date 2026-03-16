"""Cleanup helpers for acupuncture acupoint cards."""
from __future__ import annotations

import re

_BLOCKED_NAME_EXACT = {
    "经络",
    "定位",
    "主治",
    "刺灸法",
    "操作",
    "注意事项",
    "主要病候",
    "主治概要",
    "中",
    "关",
    "天",
    "巨",
    "心",
    "次",
    "醒",
    "足阳明",
    "手太阴",
    "小儿禁刺",
    "小儿吐乳",
    "肋间",
}
_BLOCKED_NAME_SUBSTRINGS = (
    "病",
    "症",
    "主治",
    "定位",
    "操作",
    "刺灸",
    "概要",
    "总论",
    "作用",
    "原则",
    "方法",
    "歌赋",
    "治疗",
    "第三章",
    "经脉",
    "循行",
    "部位",
    "各论",
    "腧穴",
    "喻穴",
    "禁刺",
    "吐乳",
)
_OCR_NAME_CORRECTIONS = {
    "瘦脉": "瘈脉",
    "澳脉": "瘈脉",
    "预息": "颅息",
    "耳和": "耳和髎",
    "四澳": "四渎",
}
_FALLBACK_NAME_PATTERN = re.compile(
    r"(?:^|[。；;\s])(?:\d+\.)?\s*([\u4e00-\u9fa5]{1,8})(?:\*|\s)*\([^)]*[A-Za-z]{1,3}\s*\d+[^)]*\)"
)
_FALLBACK_NUMBERED_NAME_PATTERN = re.compile(
    r"(?:^|[。；;\s])(?:\d+[\.、]\s*|[一二三四五六七八九十]+\s*[\.、]\s*)"
    r"([\u4e00-\u9fa5]{2,5})(?=(?:\*|【|［|[，。,；;]|\s|$))"
)
_KNOWN_LABELS = ("定位", "主治", "操作", "刺灸法", "注意", "禁忌", "解剖", "经络", "归经")


def _clean_text(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip(" ；;。,:：、")
    return cleaned or None


def _clean_field_prefix(value: str | None) -> str | None:
    cleaned = _clean_text(value)
    if not cleaned:
        return None
    labels = "|".join(map(re.escape, _KNOWN_LABELS))
    cleaned = re.sub(rf"^(?:{labels})[：:]?\s*", "", cleaned)
    return cleaned.strip(" ；;。,:：、") or None


def _normalize_known_name(name: str | None) -> str | None:
    if not name:
        return None
    cleaned = re.sub(r"\s+", "", name)
    return _OCR_NAME_CORRECTIONS.get(cleaned, cleaned)


def _looks_like_valid_name(name: str | None) -> bool:
    if not name:
        return False
    cleaned = _normalize_known_name(name) or ""
    if not 2 <= len(cleaned) <= 5:
        return False
    if cleaned in _BLOCKED_NAME_EXACT:
        return False
    if cleaned.endswith(("各", "其", "的")):
        return False
    return not any(token in cleaned for token in _BLOCKED_NAME_SUBSTRINGS)


def clean_acupuncture_card_payload(
    payload: dict[str, str | None],
    *,
    source_text: str | None = None,
) -> dict[str, str | None]:
    """Normalize acupoint card fields and recover the point name when possible."""
    acupoint_name = _clean_field_prefix(payload.get("acupoint_name"))
    acupoint_name = _normalize_known_name(acupoint_name)
    if not _looks_like_valid_name(acupoint_name) and source_text:
        normalized_source = re.sub(r"\s+", " ", source_text)
        for pattern in (_FALLBACK_NAME_PATTERN, _FALLBACK_NUMBERED_NAME_PATTERN):
            match = pattern.search(normalized_source)
            if not match:
                continue
            candidate = _normalize_known_name(_clean_field_prefix(match.group(1)))
            if _looks_like_valid_name(candidate):
                acupoint_name = candidate
                break
        if not _looks_like_valid_name(acupoint_name):
            for wrong, correct in _OCR_NAME_CORRECTIONS.items():
                if wrong in normalized_source:
                    acupoint_name = correct
                    break

    cleaned = {
        "acupoint_name": acupoint_name,
        "meridian": _clean_field_prefix(payload.get("meridian")),
        "location": _clean_field_prefix(payload.get("location")),
        "indication": _clean_field_prefix(payload.get("indication")),
        "technique": _clean_field_prefix(payload.get("technique")),
        "caution": _clean_field_prefix(payload.get("caution")),
    }
    return cleaned


def is_valid_acupuncture_card_payload(payload: dict[str, str | None]) -> bool:
    """Reject obvious OCR tails and cards missing all useful detail."""
    return _looks_like_valid_name(payload.get("acupoint_name")) and any(
        payload.get(field) for field in ("location", "indication", "technique", "meridian")
    )
