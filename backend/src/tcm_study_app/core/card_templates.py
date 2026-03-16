"""Card template definitions for the knowledge library."""
from dataclasses import dataclass


@dataclass(frozen=True)
class CardTemplate:
    """A fixed card template shown in the UI."""

    key: str
    subject_key: str
    label: str
    description: str
    fields: tuple[str, ...]
    minimum_fields: int


CARD_TEMPLATES: dict[str, list[CardTemplate]] = {
    "acupuncture": [
        CardTemplate(
            key="acupoint_knowledge",
            subject_key="acupuncture",
            label="经络腧穴卡",
            description="适合从《临床针灸学》经络腧穴篇抽取穴位与经脉要点。",
            fields=(
                "acupoint_name",
                "meridian",
                "acupoint_property",
                "location",
                "indication",
                "technique",
                "caution",
            ),
            minimum_fields=4,
        ),
        CardTemplate(
            key="needling_technique",
            subject_key="acupuncture",
            label="刺灸技术卡",
            description="适合从刺灸技术篇抽取技术定义、要点、适应证与禁忌。",
            fields=(
                "technique_name",
                "section_title",
                "definition_or_scope",
                "key_points",
                "indications",
                "contraindications",
                "notes",
            ),
            minimum_fields=3,
        ),
        CardTemplate(
            key="condition_treatment",
            subject_key="acupuncture",
            label="病证治疗卡",
            description="适合从针灸治疗篇抽取病证、治法和处方要点。",
            fields=(
                "disease_name",
                "pattern_name",
                "treatment_principle",
                "acupoint_prescription",
                "modifications",
                "notes",
            ),
            minimum_fields=3,
        ),
    ],
    "warm_disease": [
        CardTemplate(
            key="pattern_treatment",
            subject_key="warm_disease",
            label="证候辨治卡",
            description="覆盖证名、阶段、症状、治法、方药和辨证要点。",
            fields=(
                "pattern_name",
                "stage",
                "syndrome",
                "treatment",
                "formula",
                "differentiation",
            ),
            minimum_fields=4,
        ),
        CardTemplate(
            key="pattern_stage_review",
            subject_key="warm_disease",
            label="卫气营血复习卡",
            description="适合按阶段快速回顾证候表现和治法。",
            fields=("pattern_name", "stage", "syndrome", "treatment", "formula"),
            minimum_fields=4,
        ),
    ],
}

TEMPLATE_KEY_ALIASES = {
    "acupoint_foundation": "acupoint_knowledge",
    "acupoint_review": "acupoint_knowledge",
    "theory_review": "needling_technique",
    "clinical_treatment": "condition_treatment",
}


def list_templates_for_subject(subject_key: str) -> list[CardTemplate]:
    """Return supported templates for a subject."""
    return CARD_TEMPLATES.get(subject_key, [])


def get_card_template(template_key: str, subject_key: str) -> CardTemplate:
    """Resolve a template for the given subject."""
    template_key = TEMPLATE_KEY_ALIASES.get(template_key, template_key)
    for template in list_templates_for_subject(subject_key):
        if template.key == template_key:
            return template
    raise ValueError(f"Template {template_key} is not supported for subject {subject_key}")
