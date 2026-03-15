"""Shared subject registry and helpers."""
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SubjectDefinition:
    """Configuration for a supported study subject."""

    key: str
    display_name: str
    category: str
    title_field: str
    default_title: str
    extractor_method: str
    entity_label: str

    def extract(self, llm_service: Any, text: str) -> dict[str, Any]:
        """Extract structured content for the subject."""
        extractor = getattr(llm_service, self.extractor_method)
        return extractor(text)

    def build_record(
        self,
        knowledge_card_id: int,
        card_data: dict[str, Any],
    ) -> Any:
        """Create the subject-specific record for persistence."""
        if self.key == "acupuncture":
            from tcm_study_app.models.acupuncture_card import AcupunctureCard

            return AcupunctureCard(
                knowledge_card_id=knowledge_card_id,
                acupoint_name=card_data.get("acupoint_name") or self.default_title,
                meridian=card_data.get("meridian"),
                location=card_data.get("location"),
                indication=card_data.get("indication"),
                technique=card_data.get("technique"),
                caution=card_data.get("caution"),
            )

        if self.key == "warm_disease":
            from tcm_study_app.models.warm_disease_card import WarmDiseaseCard

            return WarmDiseaseCard(
                knowledge_card_id=knowledge_card_id,
                pattern_name=card_data.get("pattern_name") or self.default_title,
                stage=card_data.get("stage"),
                syndrome=card_data.get("syndrome"),
                treatment=card_data.get("treatment"),
                formula=card_data.get("formula"),
                differentiation=card_data.get("differentiation"),
            )

        from tcm_study_app.models.formula_card import FormulaCard

        return FormulaCard(
            knowledge_card_id=knowledge_card_id,
            formula_name=card_data.get("formula_name") or self.default_title,
            composition=card_data.get("composition"),
            effect=card_data.get("effect"),
            indication=card_data.get("indication"),
            pathogenesis=card_data.get("pathogenesis"),
            usage_notes=card_data.get("usage_notes"),
            memory_tip=card_data.get("memory_tip"),
        )


SUBJECTS: dict[str, SubjectDefinition] = {
    "formula": SubjectDefinition(
        key="formula",
        display_name="方剂学",
        category="formula",
        title_field="formula_name",
        default_title="未知方剂",
        extractor_method="extract_formula_card",
        entity_label="方剂",
    ),
    "acupuncture": SubjectDefinition(
        key="acupuncture",
        display_name="针灸学",
        category="acupuncture",
        title_field="acupoint_name",
        default_title="未知穴位",
        extractor_method="extract_acupuncture_card",
        entity_label="穴位",
    ),
    "warm_disease": SubjectDefinition(
        key="warm_disease",
        display_name="温病学",
        category="warm_disease",
        title_field="pattern_name",
        default_title="未知证候",
        extractor_method="extract_warm_disease_card",
        entity_label="证候",
    ),
}

SUBJECT_ALIASES = {
    "formula": "formula",
    "方剂学": "formula",
    "fangjixue": "formula",
    "acupuncture": "acupuncture",
    "针灸学": "acupuncture",
    "针灸": "acupuncture",
    "warm_disease": "warm_disease",
    "warm disease": "warm_disease",
    "温病学": "warm_disease",
    "温病": "warm_disease",
}


def normalize_subject_key(subject: str | None) -> str:
    """Normalize free-form subject input to a supported key."""
    normalized = (subject or SUBJECTS["formula"].display_name).strip().lower()
    return SUBJECT_ALIASES.get(normalized, "formula")


def get_subject_definition(subject: str | None) -> SubjectDefinition:
    """Resolve a subject string into a registered subject definition."""
    return SUBJECTS[normalize_subject_key(subject)]


def list_subject_definitions() -> list[SubjectDefinition]:
    """Return supported subjects in stable display order."""
    return [SUBJECTS["warm_disease"], SUBJECTS["acupuncture"]]
