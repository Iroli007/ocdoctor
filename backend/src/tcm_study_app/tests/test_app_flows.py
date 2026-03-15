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
