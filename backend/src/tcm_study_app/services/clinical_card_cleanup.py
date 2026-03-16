"""Cleanup helpers for acupuncture clinical treatment cards."""
import re
from typing import Any

_TITLE_MAX_LENGTH = 16
_TITLE_BLOCKED_EXACT = {
    "共同症",
    "伴随症",
    "全身兼症",
    "特征症",
    "其他病",
    "针对病",
    "按病症",
    "依病症",
    "风寒证",
    "风热证",
    "风湿证",
    "肝阳上亢证",
    "肾虚证",
    "血虚证",
    "痰浊证",
    "血瘀证",
    "气滞证",
    "寒凝证",
}
_TITLE_BLOCKED_PREFIXES = (
    "本病",
    "必要时",
    "用于临床",
    "血管情况",
    "分钟",
    "特殊的",
    "或胀痛",
    "配穴",
    "治法",
    "方义",
    "检查",
    "病位",
    "患者",
    "主要表现",
    "主要改善",
    "改善症状",
    "治疗目的是",
    "治疗方案",
    "治疗策略",
    "应以治疗",
    "可根据",
    "还需与",
    "明确",
    "部分患者",
    "将来",
    "模仿",
    "骤然发生",
)
_TITLE_BLOCKED_SUBSTRINGS = (
    "病因辨证",
    "辨证",
    "常伴",
    "内镜",
    "上位神经中枢",
    "鉴别",
    "解决思路",
    "预后",
    "原发病",
    "耳针法",
    "针刺",
    "消毒",
    "活动对本病",
    "查明病",
    "病菌",
    "进入血液",
    "明显缓解",
    "根据不同病",
    "治疗期间",
    "操作首先",
    "明显压痛",
    "压痛轻微",
    "主要症状",
    "全身性疾病",
    "中医学无此病",
    "基本病",
    "治疗本病",
    "类似症",
    "皮肤病",
    "眼病",
    "疾病",
    "日赤肿痛",
    "红肿热痛",
)
_TITLE_VERB_PREFIX_PATTERN = re.compile(
    r"^(?:要|应|宜|可|需|先|后|再|将|按|依|从|以|用|取|作|行|予|令|使|做|因|防)"
)
_TITLE_THERAPY_PREFIX_PATTERN = re.compile(
    r"^(?:清|温|补|泻|调|疏|舒|通|止|安|宁|消|散|扶|固|平|养|理|利|活|祛|化|镇|宣|熄|醒)"
)
_DISEASE_EXACT_TERMS = (
    "戒断综合征",
    "戒毒综合征",
    "戒烟综合征",
    "痹证",
    "痿证",
    "中风",
    "眩晕",
    "不寐",
    "闭经",
    "带下",
    "遗尿",
    "泄泻",
    "耳鸣",
    "耳聋",
    "鼻衄",
    "哮喘",
    "痛经",
    "黄褐斑",
    "痤疮",
    "斑秃",
    "脱发",
    "丹毒",
    "肠痈",
    "面瘫",
)
_DISEASE_SUFFIXES = (
    "病",
    "症",
    "痹",
    "痛",
    "瘫",
    "聋",
    "哮",
    "痫",
)
_DISEASE_BODY_PATTERN = (
    rf"(?:{'|'.join(map(re.escape, _DISEASE_EXACT_TERMS))}|"
    rf"[\u4e00-\u9fa5]{{1,18}}(?:{'|'.join(map(re.escape, _DISEASE_SUFFIXES))}))"
)
_DISEASE_PATTERN = re.compile(
    _DISEASE_BODY_PATTERN
)
_ACUPOINT_CUE_PATTERN = re.compile(
    r"(穴|阿是|夹脊|阑尾穴|腰痛点|百会|水沟|神门|内关|合谷|太冲|足三里|三阴交|风池|迎香|印堂|列缺)"
)
_TREATMENT_CUE_PATTERN = re.compile(
    r"(疏|清|补|泻|调|和|通|止|安|散|益|温|化|固|宣|养|平|祛|理|利|熄|醒|宁|解)"
)
_COMMON_CLEANUPS = (
    (r"\s+", " "),
    (r"(?<!\d)\d{2,4}\s*针灸学", ""),
    (r"第[一二三四五六七八九十百]+章[^\s]{0,18}", ""),
    (r"第[一二三四五六七八九十百]+节[^\s]{0,18}", ""),
    (r"[（(]\d+[)）]", ""),
    (r"^\d+[\.、．]\s*", ""),
    (r"^[一二三四五六七八九十百]+[、\.．]\s*", ""),
)


def _clean_common_text(text: str | None) -> str:
    """Normalize whitespace and strip textbook/page noise."""
    cleaned = (text or "").replace("\r", "\n").strip()
    for pattern, replacement in _COMMON_CLEANUPS:
        cleaned = re.sub(pattern, replacement, cleaned)
    return cleaned.strip(" ，。；;：:、")


def _clean_field_prefix(value: str, labels: tuple[str, ...]) -> str:
    """Remove duplicated field labels from extracted values."""
    escaped = "|".join(re.escape(label) for label in labels)
    return re.sub(rf"^(?:{escaped})[：:]?\s*", "", value).strip()


def _extract_labeled_segment(text: str | None, labels: tuple[str, ...]) -> str | None:
    """Extract one labeled segment from raw source text."""
    if not text:
        return None
    escaped = "|".join(re.escape(label) for label in labels)
    next_markers = (
        "治法|治则|治疗原则|辨证论治|处方|取穴|主穴|配穴|选穴|基本处方|"
        "操作|方义|加减|按语|经验|其他治疗"
    )
    pattern = re.compile(
        rf"(?:【(?:{escaped})】|(?:{escaped})(?:[：:]|\s{{0,2}}))\s*(.+?)(?=(?:【(?:{next_markers})】|(?:{next_markers})(?:[：:]|\s{{0,2}})|$))",
        re.DOTALL,
    )
    match = pattern.search(_clean_common_text(text))
    if not match:
        return None
    return match.group(1).strip(" ，。；;：:")


def clean_clinical_field(field_key: str, value: str | None) -> str | None:
    """Clean noisy OCR leftovers from a clinical card field."""
    if not value:
        return None

    cleaned = _clean_common_text(value)
    if field_key == "treatment_principle":
        cleaned = _clean_field_prefix(cleaned, ("治法", "治则", "治疗原则", "辨证论治"))
        cleaned = re.split(
            r"(?:处方|取穴|主穴|配穴|选穴|基本处方|加减|按语|其他治疗)[：:]",
            cleaned,
            maxsplit=1,
        )[0]
        if not _TREATMENT_CUE_PATTERN.search(cleaned):
            return None

    if field_key == "acupoint_prescription":
        cleaned = _clean_field_prefix(cleaned, ("处方", "取穴", "主穴", "配穴", "选穴", "基本处方"))
        cleaned = re.split(
            r"(?:加减|操作|按语|其他治疗|耳针法|皮肤针法|刺络拔罐法|火针法|穴位注射法)[：: ]",
            cleaned,
            maxsplit=1,
        )[0]
        if not _ACUPOINT_CUE_PATTERN.search(cleaned):
            return None

    if field_key == "notes":
        cleaned = _clean_field_prefix(cleaned, ("操作", "方义", "加减", "按语", "经验"))
        cleaned = re.split(
            r"(?:其他治疗|耳针法|皮肤针法|刺络拔罐法|火针法|穴位注射法)[：: ]",
            cleaned,
            maxsplit=1,
        )[0]

    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ，。；;：:")
    return cleaned or None


def _clean_title_text(title: str | None) -> str:
    """Normalize a candidate disease title before validation."""
    cleaned = _clean_common_text(title)
    cleaned = re.sub(r"^(?:本病相当于西医学的|中医称本病|中医称|本病为|本病|例如|如)", "", cleaned)
    cleaned = re.sub(r"^(?:按辨证与辨病|按辨病与辨证|按辨证|按病症|依病症|配穴)", "", cleaned)
    cleaned = re.sub(r"^(?:共同症|伴随症|全身兼症|特征症)", "", cleaned)
    cleaned = re.sub(r"(?:的病因辨证|病因辨证|病因病)$", "", cleaned)
    cleaned = re.split(r"[，。；：:（(]", cleaned, maxsplit=1)[0]
    return cleaned.strip()


def is_valid_clinical_title(title: str | None) -> bool:
    """Return whether a cleaned title still looks like a disease heading."""
    cleaned = _clean_title_text(title)
    if not cleaned or len(cleaned) > _TITLE_MAX_LENGTH:
        return False
    if cleaned in _TITLE_BLOCKED_EXACT:
        return False
    if any(cleaned.startswith(prefix) for prefix in _TITLE_BLOCKED_PREFIXES):
        return False
    if any(fragment in cleaned for fragment in _TITLE_BLOCKED_SUBSTRINGS):
        return False
    if "等" in cleaned:
        return False
    if _TITLE_VERB_PREFIX_PATTERN.search(cleaned):
        return False
    if _TITLE_THERAPY_PREFIX_PATTERN.search(cleaned):
        return False
    if re.search(r"[A-Za-z0-9]", cleaned):
        return False
    if "的" in cleaned or "是" in cleaned:
        return False
    return bool(_DISEASE_PATTERN.fullmatch(cleaned))


def extract_clinical_disease_name(source_text: str | None, preferred_title: str | None = None) -> str | None:
    """Find the best disease-like title from raw OCR text."""
    candidates: list[str] = []
    text = source_text or ""
    compact_text = _clean_common_text(text)

    for raw_line in text.splitlines()[:8]:
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"^(?:[（(]?[一二三四五六七八九十百]+[)）]?[、\.．]?|[（(]?\d+[)）]?[、\.．]?)\s*", "", line)
        if is_valid_clinical_title(line):
            candidates.append(line)

    contextual_patterns = (
        rf"本病相当于西医学的({_DISEASE_BODY_PATTERN})",
        rf"中医称(?:本病)?为?({_DISEASE_BODY_PATTERN})",
    )
    for pattern in contextual_patterns:
        for match in re.finditer(pattern, text):
            candidates.append(match.group(match.lastindex or 0))

    heading_patterns = (
        rf"(?:^|\n)\s*(?:第[一二三四五六七八九十百]+[章节][^\n]{{0,12}}\n)?(?:[一二三四五六七八九十百]+[、\.．]|\d+[、\.．])\s*({_DISEASE_BODY_PATTERN})(?=\s)",
        rf"(?:^|\n)\s*(?:第[一二三四五六七八九十百]+[章节][^\n]{{0,12}}\n)?(?:[一二三四五六七八九十百]+[、\.．]|\d+[、\.．])?\s*({_DISEASE_BODY_PATTERN})(?=\s*(?:治法|治则|治疗原则|辨证论治|处方|取穴|主穴|配穴|加减|$))",
        rf"(?:^|[。；])\s*({_DISEASE_BODY_PATTERN})(?=\s*(?:治法|治则|治疗原则|辨证论治|处方|取穴|主穴|配穴|加减))",
        rf"(?:^|\s)(?:第[一二三四五六七八九十百]+[章节]\s*[^\s]{{0,8}}\s+)?(?:[一二三四五六七八九十百]+[、\.．]|\d+[、\.．])?\s*({_DISEASE_BODY_PATTERN})(?=\s*(?:治法|治则|治疗原则|辨证论治|处方|取穴|主穴|配穴|加减))",
    )
    for pattern in heading_patterns:
        for match in re.finditer(pattern, text):
            candidates.append(match.group(match.lastindex or 0))
        for match in re.finditer(pattern, compact_text):
            candidates.append(match.group(match.lastindex or 0))

    if preferred_title:
        candidates.insert(0, preferred_title)

    seen: set[str] = set()
    for candidate in candidates:
        cleaned = _clean_title_text(candidate)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        if is_valid_clinical_title(cleaned):
            return cleaned
    return None


def clean_clinical_card_payload(
    payload: dict[str, Any] | None,
    *,
    source_text: str | None = None,
) -> dict[str, Any]:
    """Normalize a clinical card payload for generation or display."""
    cleaned_payload = dict(payload or {})
    disease_name = extract_clinical_disease_name(
        source_text,
        preferred_title=cleaned_payload.get("disease_name"),
    )
    cleaned_payload["disease_name"] = disease_name or _clean_title_text(
        cleaned_payload.get("disease_name")
    )
    treatment_source = _extract_labeled_segment(
        source_text,
        ("治法", "治则", "治疗原则", "辨证论治"),
    )
    acupoint_source = _extract_labeled_segment(
        source_text,
        ("处方", "取穴", "主穴", "配穴", "选穴", "基本处方"),
    )
    notes_source = _extract_labeled_segment(
        source_text,
        ("操作", "方义", "加减", "按语", "经验"),
    )
    cleaned_payload["treatment_principle"] = clean_clinical_field(
        "treatment_principle",
        treatment_source or cleaned_payload.get("treatment_principle"),
    )
    cleaned_payload["acupoint_prescription"] = clean_clinical_field(
        "acupoint_prescription",
        acupoint_source or cleaned_payload.get("acupoint_prescription"),
    )
    cleaned_payload["notes"] = clean_clinical_field(
        "notes",
        notes_source or cleaned_payload.get("notes"),
    )
    return cleaned_payload


def is_valid_clinical_card_payload(payload: dict[str, Any] | None) -> bool:
    """Return whether a cleaned clinical payload is worth showing."""
    cleaned = payload or {}
    if not is_valid_clinical_title(cleaned.get("disease_name")):
        return False
    if not cleaned.get("treatment_principle") or not cleaned.get("acupoint_prescription"):
        return False
    return True


def normalize_clinical_title_key(title: str | None) -> str:
    """Normalize a cleaned title for lightweight dedupe."""
    cleaned = _clean_title_text(title)
    cleaned = re.sub(r"\s+", "", cleaned)
    cleaned = re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9]", "", cleaned)
    return cleaned.lower()
