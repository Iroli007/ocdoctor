"""Tests for acupuncture source classification."""
from tcm_study_app.services.acupuncture_source_classifier import (
    classify_acupuncture_source,
    detect_acupuncture_source_style,
    is_clinical_acupuncture_source,
)


def test_classify_acupuncture_source_prefers_clinical_book_and_book_part():
    meta = classify_acupuncture_source("04_第三章_经络腧穴各论.pdf", text="表3-1 手太阴肺经腧穴 序号 穴名 定位 主治 刺灸")
    assert meta.book_key == "clinical_acupuncture"
    assert meta.book_part == "上篇"
    assert meta.source_style == "table"


def test_classify_acupuncture_source_marks_standard_book():
    meta = classify_acupuncture_source("015_第二节_手阳明大肠经及其腧穴.pdf", text="1.商阳 【定位】在食指末节桡侧")
    assert meta.book_key == "standard_acupuncture"
    assert meta.book_part is None
    assert meta.source_style == "prose"


def test_is_clinical_acupuncture_source_uses_filename_shape():
    assert is_clinical_acupuncture_source("19_第十八章_五官病症.pdf") is True
    assert is_clinical_acupuncture_source("080_第七章_针灸治疗各论·五官科病证_part01.pdf") is False


def test_detect_acupuncture_source_style_recognizes_diagram_text():
    assert detect_acupuncture_source_style("图3-11 手少阳三焦经穴图示 角孙 耳门 丝竹空") == "diagram"
