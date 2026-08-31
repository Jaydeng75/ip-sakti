from fastapi.testclient import TestClient

from app import ENGLISH, app, settings, split_text, validate_route


def test_split_text_preserves_content_and_limit():
    text = "First sentence. Second sentence is a little longer. Third sentence."
    chunks = split_text(text, 28)
    assert all(len(chunk) <= 28 for chunk in chunks)
    assert " ".join(chunks) == text


def test_supported_translation_routes():
    validate_route(ENGLISH, "hin_Deva")
    validate_route("tam_Taml", ENGLISH)
    validate_route("ben_Beng", "mar_Deva")


def test_identity_translation_does_not_load_a_model():
    with TestClient(app) as client:
        response = client.post(
            "/translate",
            json={"texts": ["Authoritative English text."], "source_language": ENGLISH, "target_language": ENGLISH},
        )
    assert response.status_code == 200
    assert response.json()["translations"] == ["Authoritative English text."]
    assert response.json()["machine_translated"] is False


def test_translation_service_token_is_enforced(monkeypatch):
    monkeypatch.setattr(settings, "service_token", "internal-secret")
    payload = {
        "texts": ["Authoritative English text."],
        "source_language": ENGLISH,
        "target_language": ENGLISH,
    }
    with TestClient(app) as client:
        denied = client.post("/translate", json=payload)
        accepted = client.post(
            "/translate",
            json=payload,
            headers={"X-Service-Token": "internal-secret"},
        )
    assert denied.status_code == 401
    assert accepted.status_code == 200
