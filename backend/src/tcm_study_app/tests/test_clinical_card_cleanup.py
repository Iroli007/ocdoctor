"""Clinical acupuncture card cleanup tests."""
from tcm_study_app.services.clinical_card_cleanup import (
    clean_clinical_card_payload,
    extract_clinical_disease_name,
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


def test_is_valid_clinical_card_payload_rejects_evaluative_sentence_title():
    """Evaluation sentences should not survive as disease titles."""
    cleaned = clean_clinical_card_payload(
        {
            "disease_name": "针灸能有效缓解颈部疼痛",
            "treatment_principle": "调和气血，通络止痛",
            "acupoint_prescription": "颈夹脊、风池、后溪",
            "notes": None,
        },
        source_text="针灸能有效缓解颈部疼痛，适合颈椎病患者长期随访。",
    )

    assert not is_valid_clinical_card_payload(cleaned)


def test_is_valid_clinical_card_payload_rejects_explanatory_tail_titles():
    """Explanatory and complication phrases should not survive in the card pool."""
    for title in (
        "针灸对由器质性病",
        "有明显精神心理症",
        "最终实现减少或控制顺痛",
        "尤其对功能性病",
        "早期约半数患者无明显症",
    ):
        cleaned = clean_clinical_card_payload(
            {
                "disease_name": title,
                "treatment_principle": "调和气血，通络止痛",
                "acupoint_prescription": "合谷、太冲、足三里",
                "notes": None,
            },
            source_text=title,
        )
        assert not is_valid_clinical_card_payload(cleaned)


def test_extract_clinical_disease_name_accepts_numbered_heading_without_labels():
    """Clinical sections should recognize numbered disease headings before treatment labels appear."""
    title = extract_clinical_disease_name(
        """
一、头痛
头痛是患者自觉头部疼痛的一类病症。
（二）诊断要点
偏头痛反复发作。
        """
    )

    assert title == "头痛"


def test_clean_clinical_card_payload_recovers_disease_from_later_heading():
    """Continuation-like noise should recover to a later valid disease heading when present."""
    cleaned = clean_clinical_card_payload(
        {
            "disease_name": "排除其他病",
            "treatment_principle": "理气活血，行滞催产",
            "acupoint_prescription": "至阴",
            "notes": None,
        },
        source_text="""
治疗前要做相应的检查，排除其他病因。
滞产
滞产是指妊娠足月，临产时胎儿不能顺利娩出。
治法：理气活血，行滞催产。
主穴：至阴。
        """,
    )

    assert cleaned["disease_name"] == "滞产"


def test_clean_clinical_card_payload_recovers_from_symptom_title():
    """Symptom-like titles should recover to a known disease when the source heading is available."""
    cleaned = clean_clinical_card_payload(
        {
            "disease_name": "喉中哮",
            "treatment_principle": "祛邪肃肺，化痰平喘",
            "acupoint_prescription": "列缺、尺泽、肺俞、中府、定喘",
            "notes": None,
        },
        source_text="""
哮喘
主症呼吸急促，喉中哮鸣，甚则张口抬肩。
治法：祛邪肃肺，化痰平喘。
主穴：列缺、尺泽、肺俞、中府、定喘。
        """,
    )

    assert cleaned["disease_name"] == "哮喘"
