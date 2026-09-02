import asyncio

from google.oauth2 import id_token

from config import settings
from services.translation import _service_headers


def test_service_headers_use_internal_token_only_by_default(monkeypatch):
    monkeypatch.setattr(settings, "translation_service_token", "internal-token")
    monkeypatch.setattr(settings, "translation_use_google_identity", False)

    headers = asyncio.run(_service_headers())

    assert headers == {"X-Service-Token": "internal-token"}


def test_service_headers_add_cloud_run_identity_token(monkeypatch):
    monkeypatch.setattr(settings, "translation_service_token", "internal-token")
    monkeypatch.setattr(settings, "translation_use_google_identity", True)
    monkeypatch.setattr(settings, "translation_url", "https://translation.example.run.app/")

    def fake_fetch_id_token(_request, audience):
        assert audience == "https://translation.example.run.app"
        return "google-identity-token"

    monkeypatch.setattr(id_token, "fetch_id_token", fake_fetch_id_token)

    headers = asyncio.run(_service_headers())

    assert headers == {
        "X-Service-Token": "internal-token",
        "Authorization": "Bearer google-identity-token",
    }
