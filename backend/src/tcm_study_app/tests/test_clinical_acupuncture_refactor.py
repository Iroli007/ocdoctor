"""Regression tests for the clinical acupuncture import refactor."""


def _create_collection(client, title: str) -> dict:
    response = client.post(
        "/api/collections",
        json={
            "title": title,
            "subject": "针灸学",
            "description": f"{title} 说明",
            "user_id": 1,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_import_ocr_pages_returns_structured_breakdown(client):
    """OCR import should persist section-aware structure metadata."""
    collection = _create_collection(client, "针灸学·结构化导入")

    response = client.post(
        "/api/import/ocr-pages",
        json={
            "collection_id": collection["id"],
            "file_name": "表3-3_手太阴肺经腧穴.pdf",
            "pages": [
                {
                    "page_number": 1,
                    "text": (
                        "表3-3 手太阴肺经腧穴 序号 穴名 穴性 定位 主治 刺灸 备注 "
                        "4 侠白 上臂内侧，肱二头肌桡侧缘处 干呕，肺系病证 直刺0.5～1寸 "
                        "5 尺泽 合穴 肘横纹上，肱二头肌腱桡侧缘凹陷中 肺系实热，中暑 直刺0.8～1.2寸"
                    ),
                }
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["book_section"] == "meridian_acupoints"
    assert payload["parsed_unit_count"] >= 2
    assert payload["page_kind_breakdown"]["table"] == 1
    assert payload["unit_breakdown"]["acupoint_entry"] >= 2

    detail = client.get(f"/api/documents/{payload['document_id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["book_section"] == "meridian_acupoints"
    assert body["ocr_pages"][0]["page_kind"] == "table"
    assert body["parsed_units"][0]["unit_type"] == "acupoint_entry"


def test_acupoint_knowledge_cards_generate_from_parsed_units(client):
    """Acupoint cards should be generated from parsed units rather than raw chunks."""
    collection = _create_collection(client, "针灸学·腧穴卡")
    import_response = client.post(
        "/api/import/text",
        json={
            "collection_id": collection["id"],
            "text": (
                "合谷穴\n"
                "经络：手阳明大肠经\n"
                "定位：手背第一、二掌骨间，当第二掌骨桡侧中点处\n"
                "主治：头痛、牙痛、面口病证\n"
                "刺灸法：直刺0.5-1寸\n"
                "注意：孕妇慎用强刺激"
            ),
        },
    )
    assert import_response.status_code == 200

    response = client.post(
        "/api/cards/generate",
        json={
            "document_id": import_response.json()["document_id"],
            "template_key": "acupoint_knowledge",
        },
    )

    assert response.status_code == 200
    card = response.json()["cards"][0]
    assert card["template_key"] == "acupoint_knowledge"
    assert card["title"] == "合谷"
    assert card["normalized_content"]["meridian"] == "手阳明大肠经"
    assert card["acupoint_knowledge_card"]["location"].startswith("手背第一")


def test_needling_technique_cards_generate_from_technique_section(client):
    """Technique pages should generate technique cards instead of acupoint cards."""
    collection = _create_collection(client, "针灸学·刺灸技术卡")
    import_response = client.post(
        "/api/import/text",
        json={
            "collection_id": collection["id"],
            "text": (
                "毫针刺法\n"
                "定义：毫针刺法是以毫针进行针刺操作的方法。\n"
                "操作方法：先定位取穴，再行进针、行针、出针。\n"
                "适应证：适用于常见经络病证。\n"
                "禁忌：饥饿、过劳者慎用。"
            ),
        },
    )
    assert import_response.status_code == 200

    detail = client.get(f"/api/documents/{import_response.json()['document_id']}")
    assert detail.status_code == 200
    assert detail.json()["book_section"] == "needling_techniques"

    response = client.post(
        "/api/cards/generate",
        json={
            "document_id": import_response.json()["document_id"],
            "template_key": "needling_technique",
        },
    )
    assert response.status_code == 200
    card = response.json()["cards"][0]
    assert card["template_key"] == "needling_technique"
    assert card["title"] == "毫针刺法"
    assert card["needling_technique_card"]["contraindications"]


def test_condition_treatment_cards_generate_from_treatment_section(client):
    """Treatment chapters should generate condition-treatment cards."""
    collection = _create_collection(client, "针灸学·病证治疗卡")
    import_response = client.post(
        "/api/import/text",
        json={
            "collection_id": collection["id"],
            "text": (
                "第十章 疼症\n"
                "颈椎病\n"
                "治法：疏经通络，调和气血。\n"
                "处方：风池、颈夹脊、肩井、合谷。\n"
                "加减：上肢麻木者加曲池、外关。"
            ),
        },
    )
    assert import_response.status_code == 200

    detail = client.get(f"/api/documents/{import_response.json()['document_id']}")
    assert detail.status_code == 200
    assert detail.json()["book_section"] == "treatment"
    assert detail.json()["parsed_units"][0]["unit_type"] == "condition_entry"

    response = client.post(
        "/api/cards/generate",
        json={
            "document_id": import_response.json()["document_id"],
            "template_key": "condition_treatment",
        },
    )
    assert response.status_code == 200
    card = response.json()["cards"][0]
    assert card["template_key"] == "condition_treatment"
    assert card["title"] == "颈椎病"
    assert "风池" in card["condition_treatment_card"]["acupoint_prescription"]
