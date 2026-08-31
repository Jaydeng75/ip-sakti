import os
import uuid

os.environ.setdefault("IPSAKTI_DEMO_MODE", "true")
os.environ.setdefault("IPSAKTI_SECRET_KEY", "test-secret-key-with-more-than-thirty-two-characters")

from fastapi.testclient import TestClient

from main import app


def auth_headers(client: TestClient, label: str = "analyst") -> dict[str, str]:
    email = f"{label}-{uuid.uuid4().hex}@example.com"
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "display_name": "Test Analyst",
            "password": "correct-horse-battery-staple",
        },
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def sample_case() -> dict:
    return {
        "title": "Standardized Ashwagandha Delivery Platform",
        "description": "A novel standardized botanical extract in a controlled-release capsule intended to support stress management.",
        "ingredients": ["Withania somnifera", "plant-based capsule"],
        "product_form": "Controlled-release capsule",
        "intended_use": "Supports stress management without a disease-treatment claim",
        "target_markets": ["India", "European Union", "United States"],
        "classical_formulation": False,
        "biological_sourcing": "Cultivated Withania sourced from Rajasthan through an Indian supplier",
        "metadata_json": {"manufacturing_process": "Standardized extraction and controlled-release coating"},
    }


def test_authenticated_case_analysis_and_grounded_answer():
    with TestClient(app) as client:
        headers = auth_headers(client)
        created = client.post("/api/v1/cases", json=sample_case(), headers=headers)
        assert created.status_code == 201, created.text
        case_id = created.json()["id"]

        analyzed = client.post(f"/api/v1/cases/{case_id}/analyze", headers=headers)
        assert analyzed.status_code == 200, analyzed.text
        result = analyzed.json()["result"]
        assert (
            result["scientific_evidence"]["notice"]
            == "Traditional use is not equivalent to clinically established efficacy."
        )
        assert len(result["risk_cards"]) == 5
        assert set(result["challenges"]) == {
            "patent_examiner",
            "regulatory_reviewer",
            "abs_reviewer",
            "scientific_evidence_reviewer",
        }

        answer = client.post(
            f"/api/v1/cases/{case_id}/ask",
            json={"question": "What traditional knowledge and patent issues apply in India?"},
            headers=headers,
        )
        assert answer.status_code == 200, answer.text
        body = answer.json()
        assert body["claim_type"] == "interpretation"
        assert body["citations"]
        assert all(item["url"].startswith("https://") for item in body["citations"])
        assert body["requires_human_review"] is True


def test_safe_abstention_and_case_ownership():
    with TestClient(app) as client:
        first = auth_headers(client, "owner")
        second = auth_headers(client, "other")
        case_id = client.post("/api/v1/cases", json=sample_case(), headers=first).json()["id"]

        forbidden_as_not_found = client.get(f"/api/v1/cases/{case_id}", headers=second)
        assert forbidden_as_not_found.status_code == 404

        abstention = client.post(
            f"/api/v1/cases/{case_id}/ask",
            json={"question": "zxqv orbital metallurgy"},
            headers=first,
        )
        assert abstention.status_code == 200
        assert abstention.json()["claim_type"] == "unsupported"
        assert abstention.json()["confidence"] < 0.2


def test_non_english_question_abstains_when_translation_is_disabled():
    with TestClient(app) as client:
        headers = auth_headers(client, "multilingual")
        case_id = client.post("/api/v1/cases", json=sample_case(), headers=headers).json()["id"]
        response = client.post(
            f"/api/v1/cases/{case_id}/ask",
            json={
                "question": "भारत में पेटेंट संबंधी जोखिम क्या हैं?",
                "input_language": "Hindi",
                "language": "Hindi",
            },
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["claim_type"] == "unsupported"
        assert body["citations"] == []
        assert body["input_translation"]["status"] == "disabled"
        assert body["authoritative_answer"] == body["answer"]


def test_upload_rejects_unsupported_type():
    with TestClient(app) as client:
        headers = auth_headers(client, "upload")
        case_id = client.post("/api/v1/cases", json=sample_case(), headers=headers).json()["id"]
        response = client.post(
            f"/api/v1/cases/{case_id}/documents",
            files={"file": ("malware.exe", b"MZ", "application/octet-stream")},
            headers=headers,
        )
        assert response.status_code == 415
