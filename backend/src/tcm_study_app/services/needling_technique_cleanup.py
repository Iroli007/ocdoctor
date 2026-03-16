"""Cleanup helpers for needling-technique cards."""
from __future__ import annotations

import re


def clean_needling_technique_payload(payload: dict, source_text: str | None = None) -> dict:
    """Normalize one technique payload."""
    cleaned = {
        "technique_name": _clean(payload.get("technique_name")),
        "section_title": _clean(payload.get("section_title")),
        "definition_or_scope": _clean(payload.get("definition_or_scope")),
        "key_points": _clean(payload.get("key_points")),
        "indications": _clean(payload.get("indications")),
        "contraindications": _clean(payload.get("contraindications")),
        "notes": _clean(payload.get("notes")),
    }
    if not cleaned["technique_name"] and source_text:
        match = re.search(
            r"([\u4e00-\u9fa5]{2,12}(?:针法|灸法|拔罐法|耳针法|头针法|电针法|毫针法))",
            source_text,
        )
        cleaned["technique_name"] = match.group(1) if match else "未知技术"
    return cleaned


def is_valid_needling_technique_payload(payload: dict) -> bool:
    """Return whether a technique payload is usable."""
    if not payload.get("technique_name") or payload.get("technique_name") == "未知技术":
        return False
    return bool(payload.get("definition_or_scope") or payload.get("key_points") or payload.get("indications"))


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", str(value)).strip(" ；;。")
    return cleaned or None
