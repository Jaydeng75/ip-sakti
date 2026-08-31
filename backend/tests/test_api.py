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
        assert result["claim_evidence_graph"]["summary"]["claim_count"] >= 5
        assert len(result["design_around"]["alternatives"]) == 4
        assert result["evidence_retrieval"]["prefetch_limit"] >= 8
        assert result["evidence_retrieval"]["reranker"]

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


def test_uploaded_evidence_is_indexed_retrieved_cited_and_exported():
    with TestClient(app) as client:
        headers = auth_headers(client, "rag")
        case_id = client.post("/api/v1/cases", json=sample_case(), headers=headers).json()["id"]
        evidence_text = (
            "Controlled-release botanical study\n\n"
            "The ZYTHORA-47 assay compared the standardized extract with a non-standardized comparator. "
            "The supplied material reports batch identity testing and a twelve-week stability observation. "
            "This user-supplied statement has not been independently appraised."
        )
        uploaded = client.post(
            f"/api/v1/cases/{case_id}/documents",
            files={"file": ("study-notes.txt", evidence_text.encode(), "text/plain")},
            headers=headers,
        )
        assert uploaded.status_code == 201, uploaded.text
        document = uploaded.json()
        assert document["status"] == "indexed"
        assert document["chunk_count"] >= 1
        assert document["embedding_model"]

        analyzed = client.post(f"/api/v1/cases/{case_id}/analyze", headers=headers)
        assert analyzed.status_code == 200, analyzed.text
        retrieval = analyzed.json()["result"]["evidence_retrieval"]
        assert retrieval["indexed_document_count"] == 1
        assert retrieval["chunk_count"] >= 1

        answer = client.post(
            f"/api/v1/cases/{case_id}/ask",
            json={"question": "What does the ZYTHORA-47 assay say about batch identity?"},
            headers=headers,
        )
        assert answer.status_code == 200, answer.text
        case_sources = [item for item in answer.json()["citations"] if item["source_type"] == "case_document"]
        assert case_sources
        assert case_sources[0]["locator"]
        assert case_sources[0]["content_sha256"] == document["sha256"]

        content = client.get(
            f"/api/v1/cases/{case_id}/documents/{document['id']}/content",
            headers=headers,
        )
        assert content.status_code == 200
        assert content.content == evidence_text.encode()

        pdf = client.get(f"/api/v1/cases/{case_id}/report?format=pdf", headers=headers)
        assert pdf.status_code == 200, pdf.text
        assert pdf.headers["content-type"].startswith("application/pdf")
        assert pdf.content.startswith(b"%PDF")
        assert len(pdf.content) > 2_000

        reindex = client.post(f"/api/v1/cases/{case_id}/reindex", headers=headers)
        assert reindex.status_code == 202, reindex.text
        jobs = client.get(f"/api/v1/cases/{case_id}/reindex-jobs", headers=headers)
        assert jobs.status_code == 200
        assert jobs.json()[0]["status"] == "completed"
