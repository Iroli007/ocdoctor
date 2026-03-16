"""API flow tests for the knowledge-library app."""
from tcm_study_app.services.document_library import DocumentLibrary


def _create_collection(client, title: str, subject: str) -> dict:
    response = client.post(
        "/api/collections",
        json={
            "title": title,
            "subject": subject,
            "description": f"{title} 说明",
            "user_id": 1,
        },
    )
    assert response.status_code == 200
    return response.json()


def _import_text(client, collection_id: int, text: str) -> int:
    response = client.post(
        "/api/import/text",
        json={"collection_id": collection_id, "text": text},
    )
    assert response.status_code == 200
    return response.json()["document_id"]


def test_subject_registry_endpoint(client):
    """The frontend should only see the current target subjects."""
    response = client.get("/api/subjects")
    assert response.status_code == 200
    payload = response.json()
    assert [item["key"] for item in payload] == ["warm_disease", "acupuncture"]


def test_import_pdf_lists_document_and_chunks(client, monkeypatch):
    """PDF import should create a parsed document library entry."""
    collection = _create_collection(client, "温病学·PDF 导入", "温病学")

    monkeypatch.setattr(
        DocumentLibrary,
        "_extract_pdf_pages",
        lambda self, content: [
            "卫分证\n阶段：卫分\n证候：发热，微恶风寒，咽痛\n治法：辛凉解表\n方药：银翘散",
            "气分热盛证\n阶段：气分\n证候：壮热，大汗，大渴，脉洪大\n治法：清气泄热\n方药：白虎汤",
        ],
    )

    response = client.post(
        "/api/import/pdf",
        data={"collection_id": str(collection["id"])},
        files={"file": ("warm.pdf", b"%PDF-1.4 mock", "application/pdf")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["page_count"] == 2
    assert payload["chunk_count"] >= 2

    documents_response = client.get(f"/api/documents?collection_id={collection['id']}")
    assert documents_response.status_code == 200
    documents = documents_response.json()
    assert documents[0]["file_name"] == "warm.pdf"
    assert documents[0]["page_count"] == 2


def test_import_ocr_pages_preserves_page_numbers(client):
    """OCR page uploads should store page-aware chunks for scanned PDFs."""
    collection = _create_collection(client, "针灸学·OCR 导入", "针灸学")

    response = client.post(
        "/api/import/ocr-pages",
        json={
            "collection_id": collection["id"],
            "file_name": "scan-part-01.pdf",
            "pages": [
                {"page_number": 11, "text": "绪论\n针灸学发展简史\n针灸学的对外传播"},
                {"page_number": 12, "text": "经络学说的形成\n经络学说的临床意义"},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["page_count"] == 12
    assert payload["chunk_count"] >= 2

    documents_response = client.get(f"/api/documents?collection_id={collection['id']}")
    assert documents_response.status_code == 200
    assert documents_response.json()[0]["file_name"] == "scan-part-01.pdf"

    detail_response = client.get(f"/api/documents/{payload['document_id']}")
    assert detail_response.status_code == 200
    chunk_pages = [chunk["page_number"] for chunk in detail_response.json()["chunks"]]
    assert 11 in chunk_pages
    assert 12 in chunk_pages


def test_delete_document_removes_generated_cards(client):
    """Deleting a document should also remove cards generated from that document."""
    collection = _create_collection(client, "针灸学·删除文档", "针灸学")
    document_id = _import_text(
        client,
        collection["id"],
        """
合谷穴
经络：手阳明大肠经
定位：手背第一、二掌骨间，当第二掌骨桡侧中点处
主治：头痛、牙痛、面口病证
刺灸法：直刺0.5-1寸
注意：孕妇慎用强刺激
        """.strip(),
    )

    generate_response = client.post(
        "/api/cards/generate",
        json={"document_id": document_id, "template_key": "acupoint_foundation"},
    )
    assert generate_response.status_code == 200
    assert client.get(f"/api/cards?collection_id={collection['id']}").json()

    delete_response = client.delete(f"/api/documents/{document_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "deleted"

    documents_response = client.get(f"/api/documents?collection_id={collection['id']}")
    assert documents_response.status_code == 200
    assert documents_response.json() == []

    cards_response = client.get(f"/api/cards?collection_id={collection['id']}")
    assert cards_response.status_code == 200
    assert cards_response.json() == []


def test_import_pdf_rejects_oversized_upload(client):
    """Oversized PDFs should fail with a clear HTTP-friendly message."""
    collection = _create_collection(client, "温病学·超大 PDF", "温病学")
    oversized_pdf = b"x" * (4 * 1024 * 1024 + 1)

    response = client.post(
        "/api/import/pdf",
        data={"collection_id": str(collection["id"])},
        files={"file": ("large.pdf", oversized_pdf, "application/pdf")},
    )

    assert response.status_code == 413
    assert "4 MB" in response.json()["detail"]


def test_template_generation_returns_cards_with_citations(client):
    """Cards should be generated from document chunks and keep source citations."""
    collection = _create_collection(client, "针灸学·模板卡片", "针灸学")
    document_id = _import_text(
        client,
        collection["id"],
        """
合谷穴
经络：手阳明大肠经
定位：手背第一、二掌骨间，当第二掌骨桡侧中点处
主治：头痛、牙痛、面口病证
刺灸法：直刺0.5-1寸
注意：孕妇慎用强刺激

足三里
经络：足阳明胃经
定位：犊鼻下3寸，距胫骨前缘一横指
主治：胃痛、呕吐、腹胀、虚劳诸证
刺灸法：直刺1-2寸
注意：局部皮肤破损时避开操作
        """.strip(),
    )

    response = client.post(
        "/api/cards/generate",
        json={
            "document_id": document_id,
            "template_key": "acupoint_foundation",
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "generated"
    assert len(payload["cards"]) >= 2
    assert payload["cards"][0]["subject_key"] == "acupuncture"
    assert payload["cards"][0]["citations"]
    assert payload["cards"][0]["source_document_name"] == "手动粘贴文本"


def test_card_importance_persists(client):
    """Card importance should persist independently for each user."""
    collection = _create_collection(client, "温病学·卡片重要度", "温病学")
    document_id = _import_text(
        client,
        collection["id"],
        """
卫分证
阶段：卫分
证候：发热，微恶风寒，咽痛，口微渴
治法：辛凉解表
方药：银翘散
辨证要点：病位较浅，以表热为主
        """.strip(),
    )

    generate_response = client.post(
        "/api/cards/generate",
        json={
            "document_id": document_id,
            "template_key": "pattern_treatment",
        },
    )
    assert generate_response.status_code == 200
    card_id = generate_response.json()["cards"][0]["id"]

    first_update = client.post(
        f"/api/cards/{card_id}/importance?user_id=1",
        json={"importance_level": 4},
    )
    assert first_update.status_code == 200
    assert first_update.json()["importance_level"] == 4

    second_user_view = client.get(f"/api/cards/{card_id}?user_id=2")
    assert second_user_view.status_code == 200
    assert second_user_view.json()["importance_level"] == 0

    second_update = client.post(
        f"/api/cards/{card_id}/importance?user_id=2",
        json={"importance_level": 2},
    )
    assert second_update.status_code == 200
    assert second_update.json()["importance_level"] == 2

    user_one_cards = client.get(f"/api/cards?collection_id={collection['id']}&user_id=1")
    assert user_one_cards.status_code == 200
    assert user_one_cards.json()[0]["importance_level"] == 4

    user_two_cards = client.get(f"/api/cards?collection_id={collection['id']}&user_id=2")
    assert user_two_cards.status_code == 200
    assert user_two_cards.json()[0]["importance_level"] == 2


def test_users_endpoint_returns_fixed_accounts(client):
    """The frontend should be able to load the two fixed accounts."""
    response = client.get("/api/users")
    assert response.status_code == 200
    assert response.json() == [
        {"id": 1, "name": "从清晨到向晚"},
        {"id": 2, "name": "刘正"},
    ]


def test_ocr_textbook_chunk_can_generate_acupuncture_cards(client):
    """Textbook-style OCR chunks should still yield acupuncture cards."""
    collection = _create_collection(client, "针灸学·OCR 教材卡", "针灸学")
    import_response = client.post(
        "/api/import/ocr-pages",
        json={
            "collection_id": collection["id"],
            "file_name": "015_第二节_手阳明大肠经及其腧穴.pdf",
            "pages": [
                {
                    "page_number": 34,
                    "text": (
                        "四、本经腧穴(20穴) "
                        "1.商阳*(Shangyang, LI1)井穴 "
                        "【定位】在手指，食指末节桡侧，指甲根角侧上方0.1寸。 "
                        "【主治】齿痛、咽喉肿痛、热病、昏迷。 "
                        "【操作】浅刺0.1寸，或点刺出血。 "
                        "4.合谷*(Hegu, LI4)原穴 "
                        "【定位】在手背，第2掌骨桡侧的中点处。 "
                        "【主治】头痛、目赤肿痛、齿痛、鼻衄。 "
                        "【操作】直刺0.5～1寸，孕妇不宜针。"
                    ),
                }
            ],
        },
    )
    assert import_response.status_code == 200
    document_id = import_response.json()["document_id"]

    response = client.post(
        "/api/cards/generate",
        json={
            "document_id": document_id,
            "template_key": "acupoint_foundation",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["cards"]) >= 2

    cards_by_name = {
        card["normalized_content"]["acupoint_name"]: card["normalized_content"]
        for card in payload["cards"]
    }
    assert cards_by_name["商阳"]["meridian"] == "手阳明大肠经"
    assert cards_by_name["商阳"]["location"] == "在手指，食指末节桡侧，指甲根角侧上方0.1寸"
    assert cards_by_name["商阳"]["indication"] == "齿痛、咽喉肿痛、热病、昏迷"
    assert cards_by_name["商阳"]["technique"] == "浅刺0.1寸，或点刺出血"
    assert "合谷" not in cards_by_name["商阳"]["location"]

    assert cards_by_name["合谷"]["location"] == "在手背，第2掌骨桡侧的中点处"
    assert cards_by_name["合谷"]["indication"] == "头痛、目赤肿痛、齿痛、鼻衄"
    assert cards_by_name["合谷"]["technique"] == "直刺0.5～1寸，孕妇不宜针"


def test_acupuncture_field_cleanup_removes_figure_and_song_noise(client):
    """Technique fields should stop before figure captions or textbook songs."""
    collection = _create_collection(client, "针灸学·字段清洗", "针灸学")
    document_id = _import_text(
        client,
        collection["id"],
        """
11.少商*(Shaoshang, LU11)井穴
【定位】在手指，拇指末节桡侧，指甲根角侧上方0.1寸（指寸）（图3-4)。
【主治】①咽喉肿痛、鼻衄、高热等肺系实热病证；②昏迷、癫狂等急症。
【操作】浅刺0.1寸，或点刺出血。图3-4 手太阴肺经经穴歌 LU十一是肺经，起于中府少商停。第二节 手阳明大肠经及其腧穴
        """.strip(),
    )

    response = client.post(
        "/api/cards/generate",
        json={
            "document_id": document_id,
            "template_key": "acupoint_foundation",
        },
    )

    assert response.status_code == 200
    card = response.json()["cards"][0]["normalized_content"]
    assert card["acupoint_name"] == "少商"
    assert card["location"] == "在手指，拇指末节桡侧，指甲根角侧上方0.1寸（指寸）（图3-4)"
    assert card["indication"] == "①咽喉肿痛、鼻衄、高热等肺系实热病证；②昏迷、癫狂等急症"
    assert card["technique"] == "浅刺0.1寸，或点刺出血"


def test_templates_endpoint_and_export_flow(client):
    """Collections should export generated cards and templates should be discoverable."""
    collection = _create_collection(client, "温病学·导出样例", "温病学")
    document_id = _import_text(
        client,
        collection["id"],
        """
卫分证
阶段：卫分
证候：发热，微恶风寒，咽痛，口微渴
治法：辛凉解表
方药：银翘散
辨证要点：病位较浅，以表热为主
        """.strip(),
    )
    generate_response = client.post(
        "/api/cards/generate",
        json={
            "document_id": document_id,
            "template_key": "pattern_treatment",
        },
    )
    assert generate_response.status_code == 200

    templates_response = client.get("/api/templates?subject=warm_disease")
    assert templates_response.status_code == 200
    templates = templates_response.json()
    assert templates[0]["key"] == "pattern_treatment"

    export_response = client.get(f"/api/collections/{collection['id']}/export")
    assert export_response.status_code == 200
    export_payload = export_response.json()
    assert export_payload["filename"].endswith(".md")
    assert "卫分证" in export_payload["content"]
    assert "引用" in export_payload["content"]


def test_clinical_acupuncture_template_generates_disease_cards(client):
    """Clinical acupuncture textbooks should generate disease-treatment cards."""
    collection = _create_collection(client, "针灸学·临床治疗卡", "针灸学")
    document_id = _import_text(
        client,
        collection["id"],
        """
第十章 疼症
颈椎病
治法：疏经通络，调和气血。
处方：风池、颈夹脊、肩井、合谷。
加减：上肢麻木者加曲池、外关。
        """.strip(),
    )

    response = client.post(
        "/api/cards/generate",
        json={
            "document_id": document_id,
            "template_key": "clinical_treatment",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    card = payload["cards"][0]
    assert card["title"] == "颈椎病"
    assert card["normalized_content"]["disease_name"] == "颈椎病"
    assert card["normalized_content"]["treatment_principle"] == "疏经通络，调和气血"
    assert card["normalized_content"]["acupoint_prescription"] == "风池、颈夹脊、肩井、合谷"
    assert card["normalized_content"]["notes"] == "上肢麻木者加曲池、外关"


def test_clinical_acupuncture_template_skips_duplicate_titles_across_documents(client):
    """Same-title clinical cards should not duplicate across documents in one collection."""
    collection = _create_collection(client, "针灸学·跨文档去重", "针灸学")
    first_document_id = _import_text(
        client,
        collection["id"],
        """
第十章 疼症
颈椎病
治法：疏经通络，调和气血。
处方：风池、颈夹脊、肩井、合谷。
        """.strip(),
    )
    second_document_id = _import_text(
        client,
        collection["id"],
        """
第十一章 其他病症
颈椎病
治法：调和气血，通络止痛。
处方：风池、夹脊、肩井。
        """.strip(),
    )

    first_response = client.post(
        "/api/cards/generate",
        json={
            "document_id": first_document_id,
            "template_key": "clinical_treatment",
        },
    )
    assert first_response.status_code == 200

    second_response = client.post(
        "/api/cards/generate",
        json={
            "document_id": second_document_id,
            "template_key": "clinical_treatment",
        },
    )
    assert second_response.status_code == 200

    cards_response = client.get(f"/api/cards?collection_id={collection['id']}")
    assert cards_response.status_code == 200
    titles = [card["title"] for card in cards_response.json()]
    assert titles.count("颈椎病") == 1


def test_missing_collection_returns_http_friendly_404(client):
    """Import endpoints should return an explicit 404 when collections are missing."""
    response = client.post(
        "/api/import/text",
        json={"collection_id": 999, "text": "随便一段内容"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Collection 999 not found"


def test_root_serves_html_for_browser_requests(client):
    """Browsers should receive the focused knowledge-library frontend."""
    response = client.get("/", headers={"accept": "text/html"})
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "ocdoctor" in response.text.lower()
