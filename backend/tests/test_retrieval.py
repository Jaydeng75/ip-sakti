import httpx
import pytest

from services.retrieval import RerankerClient, RetrievalProviderError


def test_neural_reranker_fails_closed_when_fallback_is_disabled(monkeypatch):
    from services import retrieval

    monkeypatch.setattr(retrieval.settings, "reranker_provider", "http")
    monkeypatch.setattr(retrieval.settings, "reranker_allow_fallback", False)
    monkeypatch.setattr(
        RerankerClient,
        "_http_scores",
        lambda *_: (_ for _ in ()).throw(httpx.ConnectError("offline")),
    )

    with pytest.raises(RetrievalProviderError, match="Reranker provider is unavailable"):
        RerankerClient().score("botanical evidence", ["controlled-release capsule"])


def test_neural_reranker_labels_explicit_outage_fallback(monkeypatch):
    from services import retrieval

    monkeypatch.setattr(retrieval.settings, "reranker_provider", "http")
    monkeypatch.setattr(retrieval.settings, "reranker_allow_fallback", True)
    monkeypatch.setattr(
        RerankerClient,
        "_http_scores",
        lambda *_: (_ for _ in ()).throw(httpx.ConnectError("offline")),
    )

    scores, provider = RerankerClient().score("botanical evidence", ["botanical evidence"])

    assert scores[0] > 0
    assert provider == "heuristic-coverage-v1"
