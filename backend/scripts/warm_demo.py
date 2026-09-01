"""Warm pinned neural models and persist a provider-backed demo analysis."""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import settings  # noqa: E402


def api_request(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    token: str | None = None,
) -> Any:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    response = client.request(method, path, headers=headers)
    response.raise_for_status()
    return response.json()


def warm_neural_models(client: httpx.Client) -> dict[str, Any]:
    if settings.embedding_provider.lower() != "http" or settings.reranker_provider.lower() != "http":
        raise RuntimeError("The backend is not configured for HTTP neural embedding and reranking providers.")
    headers = {"Content-Type": "application/json"}
    if settings.embedding_api_key:
        headers["Authorization"] = f"Bearer {settings.embedding_api_key}"
    base = settings.embedding_url.rstrip("/")
    embedding = client.post(
        f"{base}/embeddings",
        headers=headers,
        json={
            "model": settings.embedding_model,
            "input": ["query: standardized botanical controlled-release evidence"],
            "encoding_format": "float",
        },
    )
    embedding.raise_for_status()
    embedding_body = embedding.json()
    vectors = embedding_body.get("data", [])
    if len(vectors) != 1 or len(vectors[0].get("embedding", [])) != settings.embedding_dimensions:
        raise RuntimeError("Neural embedding warm-up returned an unexpected vector shape.")

    reranker_headers = {"Content-Type": "application/json"}
    if settings.reranker_api_key:
        reranker_headers["Authorization"] = f"Bearer {settings.reranker_api_key}"
    reranker_base = (settings.reranker_url or settings.embedding_url).rstrip("/")
    reranked = client.post(
        f"{reranker_base}/rerank",
        headers=reranker_headers,
        json={
            "model": settings.reranker_model,
            "query": "controlled-release botanical evidence",
            "texts": [
                "A botanical capsule with a measured twelve-hour release profile.",
                "An unrelated document about vehicle registration.",
            ],
        },
    )
    reranked.raise_for_status()
    reranker_body = reranked.json()
    if len(reranker_body.get("results", [])) != 2:
        raise RuntimeError("Neural reranker warm-up returned an unexpected result set.")
    return {
        "embedding_model": embedding_body.get("model"),
        "embedding_dimensions": settings.embedding_dimensions,
        "reranker_model": reranker_body.get("model"),
    }


def is_demo_ready(analysis: dict[str, Any], corpus_version: str) -> bool:
    result = analysis.get("result", {})
    studies = result.get("case_specific_analysis", {}).get("scientific_studies", {})
    retrieval = result.get("evidence_retrieval", {})
    patents = result.get("case_specific_analysis", {}).get("patent_landscape", {})
    return all(
        [
            analysis.get("corpus_version") == corpus_version,
            retrieval.get("embedding_provider") == "http",
            retrieval.get("reranker") == settings.reranker_model,
            studies.get("full_text_appraised_count", 0) > 0,
            patents.get("status") not in {None, "unavailable", "credential_required"},
        ]
    )


def wait_for_reindex(
    client: httpx.Client,
    api_base: str,
    case_id: int,
    job_id: int,
    token: str,
) -> None:
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        jobs = api_request(client, "GET", f"{api_base}/cases/{case_id}/reindex-jobs", token=token)
        job = next((item for item in jobs if item["id"] == job_id), None)
        if job and job["status"] == "completed":
            return
        if job and job["status"] == "failed":
            raise RuntimeError(job.get("error") or "Demo evidence reindex failed.")
        time.sleep(2)
    raise TimeoutError("Timed out while warming demo evidence embeddings.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", type=int, help="Demo case ID; defaults to the most recently updated substantive case.")
    parser.add_argument("--force", action="store_true", help="Create a fresh analysis even if the persisted run is current.")
    parser.add_argument(
        "--api-base",
        default=os.getenv("IPSAKTI_DEMO_API_BASE", "http://localhost:8000/api/v1"),
    )
    args = parser.parse_args()
    api_base = args.api_base.rstrip("/")
    service_base = api_base.removesuffix(settings.api_prefix)

    with httpx.Client(timeout=300) as client:
        models = warm_neural_models(client)
        health = api_request(client, "GET", f"{service_base}/health/ready")
        auth = api_request(client, "POST", f"{api_base}/auth/demo")
        token = auth["access_token"]
        cases = api_request(client, "GET", f"{api_base}/cases", token=token)
        substantive = [case for case in cases if not case["title"].startswith("IndicTrans2")]
        target = next((case for case in substantive if case["id"] == args.case_id), None)
        if args.case_id is None and substantive:
            target = substantive[0]
        if target is None:
            raise RuntimeError("The requested demo case was not found.")

        documents = api_request(client, "GET", f"{api_base}/cases/{target['id']}/documents", token=token)
        needs_reindex = any(
            document.get("embedding_provider") != "http"
            or document.get("embedding_model") != settings.embedding_model
            or document.get("embedding_revision") != settings.embedding_revision
            for document in documents
        )
        if needs_reindex:
            job = api_request(client, "POST", f"{api_base}/cases/{target['id']}/reindex", token=token)
            wait_for_reindex(client, api_base, target["id"], job["id"], token)

        try:
            analysis = api_request(
                client,
                "GET",
                f"{api_base}/cases/{target['id']}/analysis/latest",
                token=token,
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 404:
                raise
            analysis = {}
        if not needs_reindex and (args.force or not is_demo_ready(analysis, health["corpus_version"])):
            analysis = api_request(
                client,
                "POST",
                f"{api_base}/cases/{target['id']}/analyze",
                token=token,
            )

        result = analysis.get("result", {})
        studies = result.get("case_specific_analysis", {}).get("scientific_studies", {})
        patents = result.get("case_specific_analysis", {}).get("patent_landscape", {})
        retrieval = result.get("evidence_retrieval", {})
        if not is_demo_ready(analysis, health["corpus_version"]):
            raise RuntimeError("The persisted analysis did not meet the demo-readiness gates.")
        print(
            json.dumps(
                {
                    "status": "demo_ready",
                    "case_id": target["id"],
                    "case_title": target["title"],
                    "analysis_id": analysis["id"],
                    "corpus_version": analysis["corpus_version"],
                    "embedding_provider": retrieval.get("embedding_provider"),
                    "embedding_model": retrieval.get("embedding_model"),
                    "reranker": retrieval.get("reranker"),
                    "pmc_full_text_appraised": studies.get("full_text_appraised_count", 0),
                    "pubmed_abstract_only": studies.get("abstract_only_count", 0),
                    "patent_provider": patents.get("provider"),
                    "patent_status": patents.get("status"),
                    "patent_records_cached": len(patents.get("records", [])),
                    "neural_models_warmed": models,
                    "persisted_for_offline_demo": True,
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
