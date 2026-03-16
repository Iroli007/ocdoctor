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
            key="acupoint_foundation",
            subject_key="acupuncture",
            label="穴位基础卡",
            description="适合从教材中抽取归经、定位、主治和操作要点。",
            fields=(
                "acupoint_name",
                "meridian",
                "location",
                "indication",
                "technique",
                "caution",
            ),
            minimum_fields=4,
        ),
        CardTemplate(
            key="acupoint_review",
            subject_key="acupuncture",
            label="穴位复习卡",
            description="更轻量，适合期末前快速回顾常用穴位。",
            fields=("acupoint_name", "meridian", "location", "indication"),
            minimum_fields=3,
        ),
        CardTemplate(
            key="clinical_treatment",
            subject_key="acupuncture",
            label="病证治疗卡",
            description="适合从临床针灸教材中抽取病证、治法和处方要点。",
            fields=(
                "disease_name",
                "treatment_principle",
                "acupoint_prescription",
                "notes",
            ),
            minimum_fields=3,
        ),
        CardTemplate(
            key="theory_review",
            subject_key="acupuncture",
            label="总论高频卡",
            description="适合从腧穴总论、刺灸法总论、治疗总论中抽取定义、原则和考试高频要点。",
            fields=(
                "concept_name",
                "category",
                "core_points",
                "exam_focus",
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


def list_templates_for_subject(subject_key: str) -> list[CardTemplate]:
    """Return supported templates for a subject."""
    return CARD_TEMPLATES.get(subject_key, [])


def get_card_template(template_key: str, subject_key: str) -> CardTemplate:
    """Resolve a template for the given subject."""
    for template in list_templates_for_subject(subject_key):
        if template.key == template_key:
            return template
    raise ValueError(f"Template {template_key} is not supported for subject {subject_key}")
