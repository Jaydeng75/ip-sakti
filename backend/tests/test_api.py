import os
import uuid

os.environ.setdefault("IPSAKTI_DEMO_MODE", "true")
os.environ.setdefault("IPSAKTI_SECRET_KEY", "test-secret-key-with-more-than-thirty-two-characters")

from fastapi.testclient import TestClient
from sqlalchemy import select

import main
import models
from database import SessionLocal
from main import app
from services.auth_store import AccountAlreadyExists, AuthRecord, subject_for_email


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
        "metadata_json": {
            "manufacturing_process": "Standardized extraction and controlled-release coating",
            "quantitative_composition": "Withania root extract 300 mg per capsule",
            "standardization": "5% total withanolides",
            "extraction_ratio": "10:1, 70:30 ethanol:water",
            "dose": "One capsule twice daily for eight weeks",
            "release_profile": "20-35% at 2 h and at least 85% at 12 h",
            "process_parameters": "Extraction at 50-55 C for four hours",
        },
    }


def test_registration_login_and_logout_lifecycle():
    with TestClient(app) as client:
        email = f"auth-{uuid.uuid4().hex}@example.com"
        password = "correct-horse-battery-staple"
        registration = client.post(
            "/api/v1/auth/register",
            json={"email": email, "display_name": "Auth Analyst", "password": password},
        )
        assert registration.status_code == 201, registration.text
        registration_body = registration.json()
        assert registration_body["user"]["email"] == email
        headers = {"Authorization": f"Bearer {registration_body['access_token']}"}

        assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
        assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
        assert client.get("/api/v1/auth/me", headers=headers).status_code == 401

        duplicate = client.post(
            "/api/v1/auth/register",
            json={"email": email.upper(), "display_name": "Auth Analyst", "password": password},
        )
        assert duplicate.status_code == 409

        login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200, login.text
        assert login.json()["access_token"] != registration_body["access_token"]


def test_persistent_auth_survives_loss_of_local_user_mirror(monkeypatch):
    accounts: dict[str, AuthRecord] = {}
    revoked: set[str] = set()

    def fake_create_account(*, email, display_name, password_hash, role="analyst", is_active=True):
        subject = subject_for_email(email)
        if subject in accounts:
            raise AccountAlreadyExists("An account with this email already exists")
        account = AuthRecord(subject, email.lower(), display_name, password_hash, role, is_active)
        accounts[subject] = account
        return account

    monkeypatch.setattr(main, "persistent_auth_enabled", lambda: True)
    monkeypatch.setattr(main, "create_account", fake_create_account)
    monkeypatch.setattr(main, "get_account_by_email", lambda email: accounts.get(subject_for_email(email)))
    monkeypatch.setattr(main, "get_account_by_subject", lambda subject: accounts.get(subject))
    monkeypatch.setattr(main, "token_is_revoked", lambda jti: jti in revoked)
    monkeypatch.setattr(main, "revoke_token", lambda **values: revoked.add(values["jti"]))

    email = f"persistent-{uuid.uuid4().hex}@example.com"
    password = "correct-horse-battery-staple"
    with TestClient(app) as client:
        registration = client.post(
            "/api/v1/auth/register",
            json={"email": email, "display_name": "Persistent Analyst", "password": password},
        )
        assert registration.status_code == 201, registration.text
        headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}

        with SessionLocal() as db:
            local_user = db.scalar(select(models.User).where(models.User.email == email))
            assert local_user is not None
            db.delete(local_user)
            db.commit()

        restored = client.get("/api/v1/auth/me", headers=headers)
        assert restored.status_code == 200, restored.text
        assert restored.json()["email"] == email

        login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200, login.text
        login_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        assert client.post("/api/v1/auth/logout", headers=login_headers).status_code == 204
        assert client.get("/api/v1/auth/me", headers=login_headers).status_code == 401


def test_authenticated_case_analysis_and_grounded_answer():
    with TestClient(app) as client:
        headers = auth_headers(client)
        created = client.post("/api/v1/cases", json=sample_case(), headers=headers)
        assert created.status_code == 201, created.text
        case_id = created.json()["id"]

        analyzed = client.post(f"/api/v1/cases/{case_id}/analyze", headers=headers)
        assert analyzed.status_code == 200, analyzed.text
        result = analyzed.json()["result"]
        assert result["classification"]["label"] == "Provisional classification: requires route determination"
        assert result["classification"]["candidate_pathways"]
        assert result["decision_brief"]["strongest_protectable_element"]
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
        assert result["case_specific_analysis"]["input_completeness"]["score"] >= 70
        assert any(
            "300 mg" in row["submitted_value"]
            for row in result["case_specific_analysis"]["novelty_claim_chart"]
        )
        assert all(item.get("basis") for item in result["design_around"]["alternatives"])
        assert result["evidence_retrieval"]["prefetch_limit"] >= 8
        assert result["evidence_retrieval"]["reranker"]
        assert result["risk_cards"][1]["positive_signals"]
        assert result["risk_cards"][1]["finding"]
        assert result["risk_cards"][1]["evidence_basis"]
        assert result["risk_cards"][1]["fix"]
        advisory = result["case_specific_analysis"]["technical_advisory"]
        assert len(advisory["strength_actions"]) == 5
        assert any(item["status"] == "strong_if_proven" for item in advisory["feature_assessments"])

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

        scientific = client.post(
            f"/api/v1/cases/{case_id}/ask",
            json={"question": "Does human evidence support this exact dose and formulation?"},
            headers=headers,
        )
        assert scientific.status_code == 200, scientific.text
        science_body = scientific.json()
        assert science_body["intent"] == "SCIENTIFIC_EVIDENCE"
        assert science_body["evidence_summary"] is not None
        assert all(item["source_type"] != "official" for item in science_body["citations"])
        assert "FORMULATION-SPECIFIC EVIDENCE MISSING" in science_body["answer"]

        short_greeting = client.post(
            f"/api/v1/cases/{case_id}/ask",
            json={"question": "hi"},
            headers=headers,
        )
        assert short_greeting.status_code == 200, short_greeting.text
        assert short_greeting.json()["claim_type"] == "unsupported"


def test_analysis_without_uploaded_documents_does_not_require_embedding_provider(monkeypatch):
    def unavailable_provider():
        raise AssertionError("Embedding provider should not be called without evidence chunks")

    monkeypatch.setattr("services.evidence.embedding_client", unavailable_provider)
    with TestClient(app) as client:
        headers = auth_headers(client, "no-evidence-provider")
        case_id = client.post("/api/v1/cases", json=sample_case(), headers=headers).json()["id"]

        analyzed = client.post(f"/api/v1/cases/{case_id}/analyze", headers=headers)

        assert analyzed.status_code == 200, analyzed.text
        assert analyzed.json()["result"]["evidence_retrieval"]["chunk_count"] == 0


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
