import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

from config import settings
from services.retrieval import (
    embedding_client,
    embedding_identity,
    passes_evidence_gate,
    reranker_client,
    tokens,
)

DEFAULT_SET = Path(__file__).resolve().parent / "data" / "evaluation_set.json"


def cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def lexical_score(query: str, passage: str) -> float:
    query_tokens = tokens(query)
    passage_counts = Counter(tokens(passage))
    overlap = sum(min(count, passage_counts.get(term, 0)) for term, count in Counter(query_tokens).items())
    return overlap / max(1.0, math.sqrt(len(query_tokens) * max(1, len(tokens(passage)))))


def rank_documents(question: str, documents: list[dict[str, str]]) -> list[str]:
    document_batch = embedding_client().documents([document["text"] for document in documents])
    query_vector = embedding_client().query(question).vectors[0]
    candidates = []
    for document, vector in zip(documents, document_batch.vectors, strict=True):
        lexical = lexical_score(question, document["text"])
        semantic = max(0.0, cosine(query_vector, vector))
        candidates.append(
            {
                "document": document,
                "hybrid": settings.retrieval_lexical_weight * lexical
                + settings.retrieval_semantic_weight * semantic,
            }
        )
    candidates.sort(key=lambda item: item["hybrid"], reverse=True)
    scores, _ = reranker_client().score(question, [item["document"]["text"] for item in candidates])
    for candidate, score in zip(candidates, scores, strict=True):
        candidate["rerank"] = score
        candidate["final"] = 0.45 * candidate["hybrid"] + 0.55 * score
    candidates.sort(key=lambda item: item["final"], reverse=True)
    return [
        item["document"]["id"]
        for item in candidates
        if passes_evidence_gate(
            lexical_score=lexical_score(question, item["document"]["text"]),
            rerank_score=item["rerank"],
            combined_score=item["final"],
            minimum_score=0.08,
        )
    ]


def evaluate(path: Path = DEFAULT_SET) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    identity = embedding_identity()
    reciprocal_ranks: list[float] = []
    ndcg_scores: list[float] = []
    recall_scores: list[float] = []
    top1_scores: list[float] = []
    abstention_scores: list[float] = []
    results = []
    for item in payload["queries"]:
        ranking = rank_documents(item["question"], payload["documents"])
        relevant = set(item["relevant"])
        if not relevant:
            correct = not ranking
            abstention_scores.append(float(correct))
            results.append({**item, "ranking": ranking[:5], "correct_abstention": correct})
            continue
        hit_ranks = [index + 1 for index, doc_id in enumerate(ranking) if doc_id in relevant]
        first_rank = min(hit_ranks) if hit_ranks else None
        reciprocal_ranks.append(1.0 / first_rank if first_rank else 0.0)
        recall_scores.append(len(relevant.intersection(ranking[:5])) / len(relevant))
        top1_scores.append(float(bool(ranking) and ranking[0] in relevant))
        ideal_dcg = sum(1.0 / math.log2(index + 2) for index in range(min(len(relevant), 5))) or 1.0
        dcg = sum(1.0 / math.log2(index + 2) for index, doc_id in enumerate(ranking[:5]) if doc_id in relevant)
        ndcg_scores.append(dcg / ideal_dcg)
        results.append({**item, "ranking": ranking[:5], "first_relevant_rank": first_rank})
    def mean(values: list[float]) -> float:
        return round(sum(values) / max(1, len(values)), 4)
    return {
        "dataset": payload["name"],
        "status": payload["status"],
        "query_count": len(payload["queries"]),
        "metrics": {
            "top1_accuracy": mean(top1_scores),
            "recall_at_5": mean(recall_scores),
            "mrr": mean(reciprocal_ranks),
            "ndcg_at_5": mean(ndcg_scores),
            "abstention_accuracy": mean(abstention_scores),
        },
        "retrieval": {
            "embedding_provider": identity["provider"],
            "embedding_model": identity["model"],
            "embedding_revision": identity["revision"],
            "reranker_provider": settings.reranker_provider,
            "reranker_model": settings.reranker_model,
        },
        "results": results,
        "warning": "This starter engineering set is not an expert-validated accuracy claim.",
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
