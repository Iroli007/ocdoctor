"""Clinical acupuncture card cleanup tests."""
from tcm_study_app.services.clinical_card_cleanup import (
    clean_clinical_card_payload,
    is_valid_clinical_card_payload,
)


def test_clean_clinical_card_payload_prefers_real_disease_heading():
    """Noise sentences should collapse back to the actual disease title."""
    cleaned = clean_clinical_card_payload(
        {
            "disease_name": "要积极治疗原发病",
            "treatment_principle": "化察消痣。以局部阿是穴为主",
            "acupoint_prescription": "阿是穴",
            "notes": "黄褐斑的发生可受多种因素影响，要积极治疗原发病。",
        },
        source_text="""
黄褐斑
治法：化瘀消斑。以局部阿是穴为主。
处方：阿是穴。
按语：黄褐斑的发生可受多种因素影响，要积极治疗原发病。
        """,
    )

    assert cleaned["disease_name"] == "黄褐斑"
    assert cleaned["treatment_principle"] == "化瘀消斑。以局部阿是穴为主"
    assert cleaned["acupoint_prescription"] == "阿是穴"


def test_is_valid_clinical_card_payload_rejects_descriptive_sentence_title():
    """Descriptive continuation sentences should not pass as clinical cards."""
    cleaned = clean_clinical_card_payload(
        {
            "disease_name": "应当在针刺镇痛",
            "treatment_principle": "疏肝健脾，益肾养神。以督脉、任脉及背俞穴为主",
            "acupoint_prescription": "百会关元肾俞足三里三阴交太冲",
            "notes": None,
        },
        source_text="疏肝健脾，益肾养神。以督脉、任脉及背俞穴为主。处方：百会、关元、肾俞、足三里、三阴交、太冲。",
    )

    assert not is_valid_clinical_card_payload(cleaned)
