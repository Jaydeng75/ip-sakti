import hashlib
import logging
import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache

import httpx

from config import settings

logger = logging.getLogger("ip-sakti.retrieval")
WORD_RE = re.compile(r"[^\W_][\w-]{1,}", re.UNICODE)


def embedding_identity() -> dict[str, str]:
    if settings.embedding_provider.lower() == "deterministic":
        return {"provider": "deterministic", "model": "blake2b-feature-hash", "revision": "v1"}
    return {
        "provider": settings.embedding_provider,
        "model": settings.embedding_model,
        "revision": settings.embedding_revision,
    }


class RetrievalProviderError(RuntimeError):
    pass


def tokens(text: str) -> list[str]:
    return [match.group(0).lower() for match in WORD_RE.finditer(text)]


def normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [float(value / norm) for value in vector]


def passes_evidence_gate(
    *, lexical_score: float, rerank_score: float, combined_score: float, minimum_score: float
) -> bool:
    """Reject dense-only matches unless another retrieval signal supports relevance."""
    if combined_score < minimum_score:
        return False
    if settings.reranker_provider.lower() == "http":
        return rerank_score >= settings.retrieval_minimum_rerank_score
    return (
        lexical_score >= settings.retrieval_minimum_lexical_score
        or rerank_score >= settings.retrieval_minimum_rerank_score
    )


def deterministic_embedding(text: str, dimensions: int | None = None) -> list[float]:
    """Stable fallback for development and outage-mode only; it is not a neural embedding."""
    size = dimensions or settings.embedding_dimensions
    vector = [0.0] * size
    items = tokens(text)
    features = items + [f"{left}:{right}" for left, right in zip(items, items[1:], strict=False)]
    for feature in features:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest[:4], "big") % size
        vector[index] += 1.0 if digest[4] & 1 else -1.0
    return normalize(vector)


@dataclass(frozen=True)
class EmbeddingBatch:
    vectors: list[list[float]]
    provider: str
    model: str
    revision: str
    fallback: bool = False


class EmbeddingClient:
    def _http_embeddings(self, texts: list[str], kind: str) -> list[list[float]]:
        prefix = "query: " if kind == "query" else "passage: "
        payload = {
            "model": settings.embedding_model,
            "input": [f"{prefix}{text}" for text in texts],
            "encoding_format": "float",
        }
        headers = {"Content-Type": "application/json"}
        if settings.embedding_api_key:
            headers["Authorization"] = f"Bearer {settings.embedding_api_key}"
        with httpx.Client(timeout=settings.embedding_timeout_seconds) as client:
            response = client.post(f"{settings.embedding_url.rstrip('/')}/embeddings", json=payload, headers=headers)
            response.raise_for_status()
            body = response.json()
        data = sorted(body.get("data", []), key=lambda item: item.get("index", 0))
        vectors = [normalize([float(value) for value in item["embedding"]]) for item in data]
        if len(vectors) != len(texts):
            raise RetrievalProviderError("Embedding service returned an unexpected number of vectors")
        if any(len(vector) != settings.embedding_dimensions for vector in vectors):
            raise RetrievalProviderError("Embedding dimensions do not match IPSAKTI_EMBEDDING_DIMENSIONS")
        return vectors

    def embed(self, texts: list[str], kind: str) -> EmbeddingBatch:
        if not texts:
            return EmbeddingBatch([], settings.embedding_provider, settings.embedding_model, settings.embedding_revision)
        provider = settings.embedding_provider.lower()
        try:
            if provider == "http":
                vectors = self._http_embeddings(texts, kind)
            elif provider == "deterministic":
                vectors = [deterministic_embedding(text) for text in texts]
                return EmbeddingBatch(vectors, provider, "blake2b-feature-hash", "v1")
            else:
                raise RetrievalProviderError(f"Unsupported embedding provider: {provider}")
            return EmbeddingBatch(vectors, provider, settings.embedding_model, settings.embedding_revision)
        except (httpx.HTTPError, KeyError, TypeError, ValueError, RetrievalProviderError) as exc:
            if not settings.embedding_allow_fallback or provider == "deterministic":
                raise RetrievalProviderError("Embedding provider is unavailable") from exc
            logger.warning("embedding fallback provider=%s error=%s", provider, type(exc).__name__)
            return EmbeddingBatch(
                [deterministic_embedding(text) for text in texts],
                "deterministic-fallback",
                "blake2b-feature-hash",
                "v1",
                True,
            )

    def documents(self, texts: list[str]) -> EmbeddingBatch:
        return self.embed(texts, "document")

    def query(self, text: str) -> EmbeddingBatch:
        return self.embed([text], "query")


class RerankerClient:
    def _http_scores(self, query: str, passages: list[str]) -> list[float]:
        headers = {"Content-Type": "application/json"}
        if settings.reranker_api_key:
            headers["Authorization"] = f"Bearer {settings.reranker_api_key}"
        payload = {"model": settings.reranker_model, "query": query, "texts": passages}
        url = (settings.reranker_url or settings.embedding_url).rstrip("/") + "/rerank"
        with httpx.Client(timeout=settings.reranker_timeout_seconds) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            body = response.json()
        results = body.get("results", body if isinstance(body, list) else [])
        scores = [0.0] * len(passages)
        for result in results:
            index = int(result.get("index", result.get("document_index", -1)))
            if 0 <= index < len(scores):
                scores[index] = float(result.get("relevance_score", result.get("score", 0.0)))
        return scores

    @staticmethod
    def _heuristic_scores(query: str, passages: list[str]) -> list[float]:
        query_counts = Counter(tokens(query))
        query_terms = set(query_counts)
        scores = []
        for passage in passages:
            passage_tokens = tokens(passage)
            passage_counts = Counter(passage_tokens)
            overlap = sum(min(count, passage_counts.get(term, 0)) for term, count in query_counts.items())
            coverage = len(query_terms.intersection(passage_counts)) / max(1, len(query_terms))
            density = overlap / max(1.0, math.sqrt(len(passage_tokens) * max(1, len(query_counts))))
            scores.append(min(1.0, 0.65 * coverage + 0.35 * density))
        return scores

    def score(self, query: str, passages: list[str]) -> tuple[list[float], str]:
        if not passages:
            return [], settings.reranker_provider
        if settings.reranker_provider.lower() == "http":
            try:
                return self._http_scores(query, passages), settings.reranker_model
            except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                if not settings.reranker_allow_fallback:
                    raise RetrievalProviderError("Reranker provider is unavailable") from exc
                logger.warning("reranker fallback error=%s", type(exc).__name__)
        return self._heuristic_scores(query, passages), "heuristic-coverage-v1"


@lru_cache(maxsize=1)
def embedding_client() -> EmbeddingClient:
    return EmbeddingClient()


@lru_cache(maxsize=1)
def reranker_client() -> RerankerClient:
    return RerankerClient()
