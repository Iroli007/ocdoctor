"""API flow tests for the multi-subject study app."""


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


def _generate_cards(client, document_id: int) -> None:
    response = client.post("/api/cards/generate", json={"document_id": document_id})
    assert response.status_code == 200


def _seed_warm_disease_collection(client) -> dict:
    collection = _create_collection(client, "温病学·期末训练", "温病学")
    texts = [
        "卫分证。阶段：卫分。证候：发热，微恶风寒，咽痛，口微渴。治法：辛凉解表。方药：银翘散。",
        "气分热盛证。阶段：气分。证候：壮热，大汗，大渴，脉洪大。治法：清气泄热。方药：白虎汤。",
        "营分证。阶段：营分。证候：身热夜甚，心烦不寐，舌绛。治法：清营透热。方药：清营汤。",
        "血分证。阶段：血分。证候：身热，斑疹，吐衄，舌深绛。治法：凉血散血。方药：犀角地黄汤。",
    ]
    for text in texts:
        document_id = _import_text(client, collection["id"], text)
        _generate_cards(client, document_id)
    return collection


def test_subject_registry_endpoint(client):
    """The frontend can discover supported subjects from the backend."""
    response = client.get("/api/subjects")
    assert response.status_code == 200
    payload = response.json()
    assert [item["key"] for item in payload] == [
        "formula",
        "acupuncture",
        "warm_disease",
    ]


def test_formula_collection_import_and_card_generation(client):
    """Formula collections keep formula-specific detail while using shared APIs."""
    collection = _create_collection(client, "方剂学·解表剂", "方剂学")
    assert collection["subject_key"] == "formula"

    document_id = _import_text(
        client,
        collection["id"],
        "桂枝汤。组成：桂枝、芍药、生姜、大枣、甘草。功效：解肌发表，调和营卫。主治：外感风寒表虚证。",
    )

    response = client.post("/api/cards/generate", json={"document_id": document_id})
    assert response.status_code == 200
    card = response.json()["cards"][0]
    assert card["subject_key"] == "formula"
    assert card["formula_card"]["formula_name"] == "桂枝汤"
    assert card["normalized_content"]["effect"] == "解肌发表，调和营卫"


def test_acupuncture_collection_uses_subject_adapter(client):
    """Acupuncture collections should generate acupuncture detail instead of formula detail."""
    collection = _create_collection(client, "针灸学·手阳明", "针灸学")

    document_id = _import_text(
        client,
        collection["id"],
        "合谷穴。经络：手阳明大肠经。定位：手背第一、二掌骨间。主治：头痛、牙痛。刺灸法：直刺0.5-1寸。",
    )

    response = client.post("/api/cards/generate", json={"document_id": document_id})
    assert response.status_code == 200
    card = response.json()["cards"][0]
    assert card["subject_key"] == "acupuncture"
    assert card["acupuncture_card"]["acupoint_name"] == "合谷穴"
    assert card["formula_card"] is None


def test_missing_collection_returns_http_friendly_404(client):
    """Import endpoints should return an explicit 404 when collections are missing."""
    response = client.post(
        "/api/import/text",
        json={"collection_id": 999, "text": "随便一段内容"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Collection 999 not found"


def test_root_serves_html_for_browser_requests(client):
    """Browsers should receive the practical frontend page at root."""
    response = client.get("/", headers={"accept": "text/html"})
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "期末冲刺训练台" in response.text


def test_collection_delete_removes_collection(client):
    """Collections should be deletable through the API."""
    collection = _create_collection(client, "待删除集合", "方剂学")
    response = client.delete(f"/api/collections/{collection['id']}")
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"

    list_response = client.get("/api/collections")
    titles = [item["title"] for item in list_response.json()]
    assert "待删除集合" not in titles


def test_generate_paper_returns_structured_exam_sections(client):
    """Practice-paper endpoint should return grouped exam sections."""
    collection = _seed_warm_disease_collection(client)

    response = client.post(
        "/api/quizzes/generate-paper",
        json={
            "collection_id": collection["id"],
            "mode": "final_mock",
            "difficulty": "medium",
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["subject_key"] == "warm_disease"
    assert payload["paper_title"].startswith("广州中医药大学《温病学》")
    assert [section["title"] for section in payload["sections"]] == [
        "一、选择题",
        "二、名词解释",
        "三、简答题",
        "四、论述 / 病例分析题",
    ]
    assert any(
        question["type"] == "case_analysis"
        for section in payload["sections"]
        for question in section["questions"]
    )
