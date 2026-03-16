"""Tests for acupoint card cleanup."""
from tcm_study_app.services.acupuncture_card_cleanup import (
    clean_acupuncture_card_payload,
    is_valid_acupuncture_card_payload,
)


def test_acupuncture_card_cleanup_recovers_name_from_source_text():
    cleaned = clean_acupuncture_card_payload(
        {
            "acupoint_name": "头面五官病侧头",
            "meridian": None,
            "location": "在前臂前区，腕掌侧远端横纹上1寸",
            "indication": "咳嗽、气喘",
            "technique": "直刺0.3-0.5寸",
            "caution": None,
        },
        source_text="9.太渊 (Taiyuan, LU9) 输穴；原穴；八会穴之脉会【定位】在前臂前区，腕掌侧远端横纹上1寸。",
    )

    assert cleaned["acupoint_name"] == "太渊"
    assert is_valid_acupuncture_card_payload(cleaned) is True


def test_acupuncture_card_cleanup_rejects_noisy_heading_cards():
    cleaned = clean_acupuncture_card_payload(
        {
            "acupoint_name": "头面五官病侧头",
            "meridian": None,
            "location": None,
            "indication": "头面五官病侧头、目、耳、咽喉病",
            "technique": None,
            "caution": None,
        }
    )

    assert is_valid_acupuncture_card_payload(cleaned) is False


def test_acupuncture_card_cleanup_rejects_single_character_titles():
    cleaned = clean_acupuncture_card_payload(
        {
            "acupoint_name": "心",
            "meridian": "手少阴心经",
            "location": "在腕横纹尺侧端",
            "indication": "心痛、惊悸",
            "technique": "直刺0.3寸",
            "caution": None,
        }
    )

    assert is_valid_acupuncture_card_payload(cleaned) is False


def test_acupuncture_card_cleanup_recovers_numbered_name_without_pinyin():
    cleaned = clean_acupuncture_card_payload(
        {
            "acupoint_name": "第三章经络喻穴各",
            "meridian": None,
            "location": "鼻唇沟中点旁开。",
            "indication": "鼻塞、口眼歪斜。",
            "technique": "斜刺0.3寸。",
            "caution": None,
        },
        source_text="1. 迎香 【定位】在鼻翼外缘中点旁开0.5寸。【主治】鼻塞。",
    )

    assert cleaned["acupoint_name"] == "迎香"
    assert is_valid_acupuncture_card_payload(cleaned) is True
