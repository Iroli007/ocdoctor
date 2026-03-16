"""API flow tests for the knowledge-library app."""
from types import SimpleNamespace

import tcm_study_app.main as main_module
from tcm_study_app.models import KnowledgeCard
from tcm_study_app.services.card_generator import CardGenerator
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


def test_acupuncture_card_listing_keeps_only_clinical_book_sources(client):
    """Acupuncture card APIs should now hide the older non-clinical textbook cards."""
    collection = _create_collection(client, "针灸学·来源过滤", "针灸学")

    clinical_import = client.post(
        "/api/import/ocr-pages",
        json={
            "collection_id": collection["id"],
            "file_name": "04_第三章_经络腧穴各论.pdf",
            "pages": [
                {
                    "page_number": 1,
                    "text": (
                        "表3-3 手太阴肺经腧穴 序号 穴名 定位 主治 刺灸 "
                        "4 侠白 上臂内侧，肱二头肌桡侧缘处 干呕，肺系病证 直刺0.5～1寸 "
                        "5 尺泽 肘横纹上，肱二头肌腱桡侧缘凹陷中 肺系实热，中暑 直刺0.8～1.2寸"
                    ),
                }
            ],
        },
    )
    assert clinical_import.status_code == 200

    standard_import = client.post(
        "/api/import/ocr-pages",
        json={
            "collection_id": collection["id"],
            "file_name": "015_第二节_手阳明大肠经及其腧穴.pdf",
            "pages": [
                {
                    "page_number": 1,
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
    assert standard_import.status_code == 200

    session = main_module.SessionLocal()
    try:
        session.add(
            KnowledgeCard(
                collection_id=collection["id"],
                source_document_id=clinical_import.json()["document_id"],
                title="侠白",
                category="acupoint_foundation",
                raw_excerpt="4 侠白 上臂内侧，肱二头肌桡侧缘处",
                normalized_content_json='{"template_key":"acupoint_foundation","template_label":"穴位基础卡","acupoint_name":"侠白","meridian":"手太阴肺经","location":"上臂内侧，肱二头肌桡侧缘处","indication":"干呕，肺系病证","technique":"直刺0.5～1寸"}',
            )
        )
        session.add(
            KnowledgeCard(
                collection_id=collection["id"],
                source_document_id=standard_import.json()["document_id"],
                title="商阳",
                category="acupoint_foundation",
                raw_excerpt="1.商阳*(Shangyang, LI1)井穴",
                normalized_content_json='{"template_key":"acupoint_foundation","template_label":"穴位基础卡","acupoint_name":"商阳","meridian":"手阳明大肠经","location":"在手指，食指末节桡侧，指甲根角侧上方0.1寸","indication":"齿痛、咽喉肿痛","technique":"浅刺0.1寸"}',
            )
        )
        session.commit()
    finally:
        session.close()

    cards_response = client.get(
        f"/api/cards?collection_id={collection['id']}&user_id=1&template_key=acupoint_foundation"
    )
    assert cards_response.status_code == 200
    titles = [item["title"] for item in cards_response.json()]
    assert "侠白" in titles
    assert "商阳" not in titles


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


def test_acupuncture_theory_template_generation_returns_cards(client):
    """Theory review template should generate cards for high-frequency general chapters."""
    collection = _create_collection(client, "针灸学·总论高频卡", "针灸学")
    document_id = _import_text(
        client,
        collection["id"],
        """
针灸治疗原则
定义：针灸治疗应遵循补虚泻实、清热温寒、治病求本等原则。
特点：既要辨病，又要辨证，还要结合经络循行与腧穴特性。
临床应用：期末常考配穴原则、补泻原则和局部与远部取穴结合。

特定穴的临床应用
概念：特定穴是十四经穴中具有特殊治疗作用和分类意义的一组腧穴。
内容：包括五输穴、原穴、络穴、募穴、下合穴、八会穴、郄穴、八脉交会穴、交会穴等。
考试要点：常考各种特定穴的分类、主治特点及配伍应用。
        """.strip(),
    )

    response = client.post(
        "/api/cards/generate",
        json={
            "document_id": document_id,
            "template_key": "theory_review",
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "generated"
    assert len(payload["cards"]) >= 2
    assert payload["cards"][0]["template_key"] == "theory_review"
    assert payload["cards"][0]["normalized_content"]["concept_name"]
    assert payload["cards"][0]["normalized_content"]["core_points"]


def test_theory_review_filters_noisy_titles_in_card_reads(client):
    """Theory review cards should clean noisy OCR titles before returning to the frontend."""
    collection = _create_collection(client, "针灸学·总论清洗", "针灸学")
    document_id = _import_text(
        client,
        collection["id"],
        """
针灸治疗原则
定义：针灸治疗应遵循补虚泻实、清热温寒、治病求本等原则。
内容：期末常考配穴原则、补泻原则和局部与远部取穴结合。
        """.strip(),
    )

    response = client.post(
        "/api/cards/generate",
        json={"document_id": document_id, "template_key": "theory_review"},
    )
    assert response.status_code == 200
    card_id = response.json()["cards"][0]["id"]

    detail = client.get(f"/api/cards/{card_id}")
    assert detail.status_code == 200
    assert detail.json()["title"] == "针灸治疗原则"


def test_card_importance_persists(client):
    """Card importance should persist for the single fixed user."""
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

    user_one_cards = client.get(f"/api/cards?collection_id={collection['id']}&user_id=1")
    assert user_one_cards.status_code == 200
    assert user_one_cards.json()[0]["importance_level"] == 4


def test_random_card_batch_endpoint_respects_exclusions(client):
    """Buffered draw endpoint should return unique cards and skip excluded ones."""
    collection = _create_collection(client, "针灸学·随机卡池", "针灸学")
    document_id = _import_text(
        client,
        collection["id"],
        """
合谷穴
经络：手阳明大肠经
定位：手背第一、二掌骨间，当第二掌骨桡侧中点处
主治：头痛、牙痛、面口病证
刺灸法：直刺0.5-1寸

足三里
经络：足阳明胃经
定位：犊鼻下3寸，距胫骨前缘一横指
主治：胃痛、呕吐、腹胀、虚劳诸证
刺灸法：直刺1-2寸
        """.strip(),
    )
    generate_response = client.post(
        "/api/cards/generate",
        json={"document_id": document_id, "template_key": "acupoint_foundation"},
    )
    assert generate_response.status_code == 200
    generated_cards = generate_response.json()["cards"]
    excluded_id = generated_cards[0]["id"]

    batch_response = client.get(
        f"/api/cards/random-batch?collection_id={collection['id']}&user_id=1&template_key=acupoint_foundation&limit=2&exclude_card_ids={excluded_id}"
    )
    assert batch_response.status_code == 200
    payload = batch_response.json()
    assert len(payload) == 1
    assert payload[0]["id"] != excluded_id


def test_users_endpoint_returns_fixed_accounts(client):
    """The frontend should only see the single fixed local account."""
    response = client.get("/api/users")
    assert response.status_code == 200
    assert response.json() == [{"id": 1, "name": "从清晨到向晚"}]


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


def test_ocr_acupoint_table_chunk_can_generate_missing_lung_points(client):
    """Table-style OCR pages should still yield acupoint cards for named rows."""
    collection = _create_collection(client, "针灸学·表格页肺经", "针灸学")
    import_response = client.post(
        "/api/import/ocr-pages",
        json={
            "collection_id": collection["id"],
            "file_name": "表3-3_手太阴肺经腧穴.pdf",
            "pages": [
                {
                    "page_number": 1,
                    "text": (
                        "表3-3 手太阴肺经腧穴 序号 穴名 穴性 定位 主治 刺灸 备注 "
                        "4 侠白 上臂内侧，肱二头肌桡侧缘处 干呕，肺系病证，上臂痛 直刺0.5～1寸 "
                        "5 尺泽 合穴 肘横纹上，肱二头肌腱桡侧缘凹陷中 肺系实热；急性吐泻，中暑，小儿惊风等急症 直刺0.8～1.2寸 急证热证时可用刺血疗法 "
                        "9 太渊 输穴 原穴 八会穴之脉会 掌侧腕横纹桡侧，桡动脉的桡侧凹陷处 无脉症 直刺0.3～0.5寸 针刺时避开桡动脉 "
                        "10 鱼际 荥穴 手掌桡侧，当第1掌骨桡侧中点赤白肉际处 肺系热性病证；掌中热，小儿疳积 直刺0.5～0.8寸"
                    ),
                }
            ],
        },
    )
    assert import_response.status_code == 200

    response = client.post(
        "/api/cards/generate",
        json={
            "document_id": import_response.json()["document_id"],
            "template_key": "acupoint_foundation",
        },
    )

    assert response.status_code == 200
    cards_by_name = {
        card["normalized_content"]["acupoint_name"]: card["normalized_content"]
        for card in response.json()["cards"]
    }
    assert {"侠白", "尺泽", "太渊", "鱼际"} <= set(cards_by_name)
    assert cards_by_name["尺泽"]["location"] == "肘横纹上，肱二头肌腱桡侧缘凹陷中"
    assert "中暑" in cards_by_name["尺泽"]["indication"]
    assert cards_by_name["太渊"]["technique"] == "直刺0.3～0.5寸"
    assert cards_by_name["太渊"]["caution"] == "针刺时避开桡动脉"


def test_ocr_acupoint_table_chunk_can_generate_missing_triple_burner_points(client):
    """Acupoint tables should recover row-based points on later continuation pages."""
    collection = _create_collection(client, "针灸学·表格页三焦经", "针灸学")
    import_response = client.post(
        "/api/import/ocr-pages",
        json={
            "collection_id": collection["id"],
            "file_name": "表3-10_手少阳三焦经腧穴.pdf",
            "pages": [
                {
                    "page_number": 1,
                    "text": (
                        "表3-10 手少阳三焦经腧穴 序号 穴名 穴性 定位 主治 刺灸 备注 "
                        "1 关冲 井穴 无名指尺侧，指甲角旁0.1寸 急救，中暑，昏厥 浅刺0.1寸 可点刺出血 "
                        "5 外关 络穴 八脉交会穴 通阳维脉 前臂背侧，当阳池与肘尖的连线上，腕背横纹上2寸，尺骨与桡骨之间 热病，偏头痛，瘰疬，胸胁痛 直刺0.5～1寸 "
                        "16 天牖 在颈部，横平下颌角，胸锁乳突肌的后缘凹陷中 头痛，目眩，瘿气，项强，肩背痛 直刺0.5～1寸 "
                        "23 丝竹空 在面部，眉梢凹陷中 目赤肿痛，眼睑瞤动，齿痛，癫狂痫 平刺0.5～1寸"
                    ),
                }
            ],
        },
    )
    assert import_response.status_code == 200

    response = client.post(
        "/api/cards/generate",
        json={
            "document_id": import_response.json()["document_id"],
            "template_key": "acupoint_review",
        },
    )

    assert response.status_code == 200
    cards_by_name = {
        card["normalized_content"]["acupoint_name"]: card["normalized_content"]
        for card in response.json()["cards"]
    }
    assert {"关冲", "外关", "天牖", "丝竹空"} <= set(cards_by_name)
    assert cards_by_name["关冲"]["meridian"] == "手少阳三焦经"
    assert cards_by_name["外关"]["location"].startswith("前臂背侧")
    assert "偏头痛" in cards_by_name["外关"]["indication"]
    assert cards_by_name["丝竹空"]["location"] == "在面部，眉梢凹陷中"


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


def test_clinical_acupuncture_template_ignores_continuation_noise(client):
    """Continuation pages without a disease heading should not become cards."""
    collection = _create_collection(client, "针灸学·临床续页过滤", "针灸学")
    document_id = _import_text(
        client,
        collection["id"],
        """
2.其他治疗
（1）耳针法 肝、肾、脾、肺、内分泌。
【按语】 黄褐斑的发生可受多种因素影响，要积极治疗原发病。
        """.strip(),
    )

    response = client.post(
        "/api/cards/generate",
        json={
            "document_id": document_id,
            "template_key": "clinical_treatment",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "No cards could be generated from this document"


def test_clinical_title_quality_gate_blocks_obvious_noise():
    """Clinical treatment cards should reject non-disease headings."""
    generator = CardGenerator(db=None)

    assert not generator._passes_subject_quality_gate(  # noqa: SLF001
        "acupuncture",
        "clinical_treatment",
        "共同症",
        {
            "treatment_principle": "调和气血",
            "acupoint_prescription": "合谷、太冲",
        },
    )
    assert not generator._passes_subject_quality_gate(  # noqa: SLF001
        "acupuncture",
        "clinical_treatment",
        "配穴风热动风证",
        {
            "treatment_principle": "疏风清热",
            "acupoint_prescription": "风池、合谷",
        },
    )
    assert generator._passes_subject_quality_gate(  # noqa: SLF001
        "acupuncture",
        "clinical_treatment",
        "三叉神经痛",
        {
            "treatment_principle": "通络止痛",
            "acupoint_prescription": "下关、合谷、太冲",
        },
    )
    assert generator._passes_subject_quality_gate(  # noqa: SLF001
        "acupuncture",
        "clinical_treatment",
        "痹证",
        {
            "treatment_principle": "祛风散寒，通络止痛",
            "acupoint_prescription": "阿是穴、风池、合谷",
        },
    )
    assert generator._passes_subject_quality_gate(  # noqa: SLF001
        "acupuncture",
        "clinical_treatment",
        "戒毒综合征",
        {
            "treatment_principle": "安神定志，疏调气血",
            "acupoint_prescription": "百会、水沟、神门、内关",
        },
    )


def test_clinical_treatment_units_can_span_multiple_chunks():
    """A numbered heading should carry forward until later treatment chunks appear."""
    generator = CardGenerator(db=None)
    chunks = [
        SimpleNamespace(
            id=1,
            page_number=1,
            content="""
一、头痛
头痛是患者自觉头部疼痛的一类病症。
（二）诊断要点
偏头痛反复发作。
            """.strip(),
        ),
        SimpleNamespace(
            id=2,
            page_number=2,
            content="""
（六）治疗策略
本病治疗重在通络止痛。
            """.strip(),
        ),
        SimpleNamespace(
            id=3,
            page_number=2,
            content="""
（七）治疗方案
治法：调和气血，通络止痛。
主穴：百会、风池、太阳、合谷。
加减：外感头痛加大椎、曲池。
            """.strip(),
        ),
    ]

    units = generator._build_clinical_treatment_units(chunks)  # noqa: SLF001

    assert units
    assert "头痛" in units[-1].content
    assert "主穴" in units[-1].content


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
