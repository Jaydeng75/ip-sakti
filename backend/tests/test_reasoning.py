import asyncio
from types import SimpleNamespace

import pytest

from services import reasoning
from services.reasoning import GroundedAdvisory, ReasoningProviderError, apply_reasoning_layer


def sample_case():
    return SimpleNamespace(
        title="BrahmiQ Bacopa Oral-Mucosal Spray",
        description="A standardized Bacopa oral spray with phospholipid delivery.",
        ingredients=["Bacopa monnieri extract", "Phosphatidylcholine"],
        product_form="Metered-dose oral spray",
        intended_use="Supports memory in healthy adults",
        target_markets=["India", "United Kingdom"],
        classical_formulation=False,
        biological_sourcing="Cultivated Bacopa from a documented Kerala supplier",
        metadata_json={
            "dose": "150 mg per day",
            "standardization": "50% total bacosides",
            "proposed_claim": "Supports memory in healthy adults",
        },
    )


def deterministic_result():
    return {
        "answer": "Current conclusion: not established for the exact product.",
        "claim_type": "interpretation",
        "confidence": 0.52,
        "confidence_label": "Low–Moderate",
        "confidence_basis": "Exact dose and formulation matching are incomplete.",
        "intent": "SCIENTIFIC_EVIDENCE",
        "evidence_summary": {"direct_evidence": 0, "ingredient_level_human_evidence": 3},
        "methodology": ["Scientific evidence pipeline."],
        "citations": [
            {
                "id": "PMID-123",
                "title": "Bacopa trial",
                "authority": "Evidence Journal",
                "jurisdiction": "International scientific literature",
                "effective_date": "2025",
                "support_status": "ingredient_clinical",
                "excerpt": "A 300 mg capsule was studied in adults.",
            }
        ],
        "requires_human_review": True,
        "limitations": ["Decision support only."],
    }


def enable_cloudflare(monkeypatch):
    monkeypatch.setattr(reasoning.settings, "llm_enabled", True)
    monkeypatch.setattr(reasoning.settings, "llm_provider", "cloudflare")
    monkeypatch.setattr(reasoning.settings, "llm_model", "@cf/meta/llama-3.1-8b-instruct-fast")
    monkeypatch.setattr(reasoning.settings, "llm_allow_fallback", True)


def test_grounded_llm_adds_advisory_without_replacing_controlled_conclusion(monkeypatch):
    enable_cloudflare(monkeypatch)

    async def grounded(_context):
        return GroundedAdvisory(
            finding="The exact spray remains unsupported by the retrieved ingredient-level study.",
            explanation="The cited study concerns a capsule rather than the submitted metered-dose oral spray.",
            weak_points=["The delivery route does not match."],
            missing_evidence=["A formulation-matched human study is missing."],
            recommended_actions=["Test the submitted spray against an appropriate comparator."],
            source_ids=["PMID-123"],
        )

    monkeypatch.setattr(reasoning, "_cloudflare_reasoning", grounded)
    result = asyncio.run(
        apply_reasoning_layer(sample_case(), "Does the evidence support this spray?", deterministic_result())
    )

    assert result["answer"].startswith("Current conclusion: not established")
    assert "Additional evidence-grounded reasoning" in result["answer"]
    assert result["reasoning"]["status"] == "grounded_llm"
    assert result["reasoning"]["source_ids"] == ["PMID-123"]
    assert result["claim_type"] == "interpretation"
    assert result["confidence"] == 0.52


def test_reasoning_rejects_unverified_source_id():
    context = reasoning._reasoning_context(sample_case(), "Question", deterministic_result(), None)
    advisory = GroundedAdvisory(
        finding="The evidence does not establish the exact submitted formulation.",
        explanation="The available cited material is ingredient-level evidence only.",
        source_ids=["INVENTED-SOURCE"],
    )

    with pytest.raises(ReasoningProviderError, match="unverified source"):
        reasoning._validate_advisory(advisory, context)


def test_reasoning_rejects_unsupported_number():
    context = reasoning._reasoning_context(sample_case(), "Question", deterministic_result(), None)
    advisory = GroundedAdvisory(
        finding="The evidence does not establish the exact submitted formulation.",
        explanation="The product has an invented 97% efficacy value that is absent from the evidence.",
        source_ids=["PMID-123"],
    )

    with pytest.raises(ReasoningProviderError, match="numeric value"):
        reasoning._validate_advisory(advisory, context)


def test_reasoning_provider_failure_uses_deterministic_fallback(monkeypatch):
    enable_cloudflare(monkeypatch)

    async def unavailable(_context):
        raise ReasoningProviderError("quota exhausted")

    monkeypatch.setattr(reasoning, "_cloudflare_reasoning", unavailable)
    result = asyncio.run(
        apply_reasoning_layer(sample_case(), "Does the evidence support this spray?", deterministic_result())
    )

    assert result["answer"] == deterministic_result()["answer"]
    assert result["reasoning"]["status"] == "deterministic_fallback"
    assert result["reasoning"]["fallback_used"] is True
    assert "optional LLM explanation layer" in result["limitations"][-1]
