import copy
import json
import logging
import re
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError

from config import settings

logger = logging.getLogger("ip-sakti.reasoning")


class GroundedAdvisory(BaseModel):
    finding: str = Field(min_length=10, max_length=500)
    explanation: str = Field(min_length=20, max_length=2_400)
    weak_points: list[str] = Field(default_factory=list, max_length=6)
    missing_evidence: list[str] = Field(default_factory=list, max_length=6)
    recommended_actions: list[str] = Field(default_factory=list, max_length=6)
    source_ids: list[str] = Field(min_length=1, max_length=8)


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "finding": {"type": "string"},
        "explanation": {"type": "string"},
        "weak_points": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
        "missing_evidence": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
        "recommended_actions": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
        "source_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 8},
    },
    "required": [
        "finding",
        "explanation",
        "weak_points",
        "missing_evidence",
        "recommended_actions",
        "source_ids",
    ],
    "additionalProperties": False,
}

FORBIDDEN_CONCLUSIONS = (
    "definitely patentable",
    "guaranteed patent",
    "clinically proven",
    "guaranteed efficacy",
    "no legal risk",
    "legal approval is guaranteed",
)


class ReasoningProviderError(RuntimeError):
    pass


def _case_context(case: Any) -> dict[str, Any]:
    metadata = case.metadata_json or {}
    material_metadata = {
        key: metadata.get(key)
        for key in (
            "manufacturing_process",
            "quantitative_composition",
            "standardization",
            "extraction_ratio",
            "dose",
            "release_profile",
            "process_parameters",
            "proposed_claim",
            "classical_reference",
            "brand",
        )
        if metadata.get(key)
    }
    return {
        "title": case.title,
        "description": case.description,
        "ingredients": case.ingredients or [],
        "product_form": case.product_form,
        "intended_use": case.intended_use,
        "target_markets": case.target_markets or [],
        "classical_formulation": case.classical_formulation,
        "biological_sourcing": case.biological_sourcing,
        "technical_fields": material_metadata,
    }


def _analysis_context(analysis: dict[str, Any] | None, intent: str | None) -> dict[str, Any]:
    if not analysis:
        return {}
    specific = analysis.get("case_specific_analysis", {})
    patents = specific.get("patent_landscape", {})
    studies = specific.get("scientific_studies", {})
    traditional = specific.get("traditional_knowledge", {})
    technical = specific.get("technical_advisory", {})
    classification = analysis.get("classification", {})
    context: dict[str, Any] = {
        "classification": {
            "label": classification.get("label"),
            "pathway": classification.get("pathway"),
            "status": classification.get("status"),
            "candidate_pathways": classification.get("candidate_pathways", [])[:4],
            "decision_factors": classification.get("decision_factors", [])[:6],
        },
        "decision_brief": analysis.get("decision_brief", {}),
    }
    if intent == "SCIENTIFIC_EVIDENCE":
        context["scientific_screen"] = {
            "status": studies.get("status"),
            "match_counts": studies.get("match_counts", {}),
            "full_text_appraised_count": studies.get("full_text_appraised_count"),
            "abstract_only_count": studies.get("abstract_only_count"),
            "notice": studies.get("notice"),
        }
    elif intent == "PATENT":
        context["patent_screen"] = {
            "status": patents.get("status"),
            "provider": patents.get("provider"),
            "family_count": patents.get("family_count"),
            "coverage_note": patents.get("coverage_note"),
            "limitation": patents.get("limitation"),
            "candidate_titles": [record.get("title") for record in patents.get("records", [])[:5]],
        }
        context["technical_advisory"] = {
            "inventive_step": technical.get("inventive_step", {}),
            "strength_actions": technical.get("strength_actions", [])[:5],
            "feature_assessments": [
                {
                    key: feature.get(key)
                    for key in ("feature", "submitted_value", "status_label", "why", "advisory")
                }
                for feature in technical.get("feature_assessments", [])[:5]
            ],
        }
    elif intent == "TRADITIONAL_KNOWLEDGE":
        context["traditional_knowledge_screen"] = {
            "risk": traditional.get("risk"),
            "findings": traditional.get("findings", [])[:6],
            "integration_mode": traditional.get("integration_mode"),
            "limitation": traditional.get("limitation"),
        }
    else:
        relevant_key = "abs" if intent == "ABS" else "regulatory" if intent == "REGULATORY" else None
        cards = analysis.get("risk_cards", [])
        if relevant_key:
            cards = [card for card in cards if relevant_key in str(card.get("key", "")).lower()]
        context["screening_findings"] = [
            {
                "title": card.get("title"),
                "level": card.get("level"),
                "primary_finding": card.get("primary_finding"),
                "missing_evidence": card.get("missing_evidence", [])[:3],
                "fix": card.get("fix"),
            }
            for card in cards[:5]
        ]
    return context


def _reasoning_context(
    case: Any,
    question: str,
    deterministic_result: dict[str, Any],
    analysis: dict[str, Any] | None,
) -> dict[str, Any]:
    citations = [
        {
            "id": citation.get("id"),
            "title": citation.get("title"),
            "authority": citation.get("authority"),
            "jurisdiction": citation.get("jurisdiction"),
            "effective_date": citation.get("effective_date"),
            "support_status": citation.get("support_status"),
            "locator": citation.get("locator"),
            "excerpt": str(citation.get("excerpt") or "")[:1_200],
        }
        for citation in deterministic_result.get("citations", [])[:8]
    ]
    return {
        "question": question,
        "case": _case_context(case),
        "verified_analysis": _analysis_context(analysis, deterministic_result.get("intent")),
        "evidence_controlled_conclusion": deterministic_result.get("answer"),
        "intent": deterministic_result.get("intent"),
        "claim_type": deterministic_result.get("claim_type"),
        "confidence_label": deterministic_result.get("confidence_label"),
        "evidence_summary": deterministic_result.get("evidence_summary"),
        "allowed_sources": citations,
        "allowed_source_ids": [str(citation["id"]) for citation in citations if citation.get("id")],
    }


def _response_schema(allowed_source_ids: list[str]) -> dict[str, Any]:
    """Constrain generated citations to IDs already selected by retrieval."""
    schema = copy.deepcopy(RESPONSE_SCHEMA)
    schema["properties"]["source_ids"]["items"]["enum"] = allowed_source_ids
    return schema


def _numbers(value: Any) -> set[str]:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return {match.replace(",", "") for match in re.findall(r"(?<![\w-])\d[\d,]*(?:\.\d+)?%?", serialized)}


def _validate_advisory(advisory: GroundedAdvisory, context: dict[str, Any]) -> None:
    allowed_source_ids = {
        str(source["id"])
        for source in context.get("allowed_sources", [])
        if source.get("id")
    }
    supplied_source_ids = set(advisory.source_ids)
    if not supplied_source_ids or not supplied_source_ids.issubset(allowed_source_ids):
        raise ReasoningProviderError("The reasoning response referenced an unverified source.")

    generated_prose = {
        "finding": advisory.finding,
        "explanation": advisory.explanation,
        "weak_points": advisory.weak_points,
        "missing_evidence": advisory.missing_evidence,
        "recommended_actions": advisory.recommended_actions,
    }
    unsupported_numbers = _numbers(generated_prose) - _numbers(context)
    if unsupported_numbers:
        raise ReasoningProviderError("The reasoning response introduced an unsupported numeric value.")

    normalized = json.dumps(generated_prose, ensure_ascii=False).lower()
    if any(conclusion in normalized for conclusion in FORBIDDEN_CONCLUSIONS):
        raise ReasoningProviderError("The reasoning response asserted a prohibited conclusion.")


async def _cloudflare_reasoning(context: dict[str, Any]) -> GroundedAdvisory:
    if not settings.llm_account_id or not settings.llm_api_key:
        raise ReasoningProviderError("Cloudflare Workers AI credentials are not configured.")
    endpoint = (
        "https://api.cloudflare.com/client/v4/accounts/"
        f"{settings.llm_account_id}/ai/run/{settings.llm_model}"
    )
    system_prompt = (
        "You are the guarded explanation layer for IP-SAKTI, an Ayurvedic IP and regulatory decision-support system. "
        "The evidence-controlled conclusion in the supplied JSON is authoritative: do not replace, contradict, broaden or strengthen it. "
        "Use only the supplied case facts, verified analysis and allowed sources. Never recall a law, patent, study, number or legal requirement from memory. "
        "Explain why the conclusion follows for this exact case, identify concrete weak points and missing evidence, and recommend measurable next actions. "
        "Do not determine patentability, legal obligation, regulatory classification or clinical efficacy conclusively. "
        "Every response must cite one or more exact IDs from allowed_sources in source_ids. "
        "Return only the requested JSON. Provide a concise rationale, not private chain-of-thought."
    )
    allowed_source_ids = context.get("allowed_source_ids", [])
    if not allowed_source_ids:
        raise ReasoningProviderError("No verified source IDs were supplied to the reasoning provider.")
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(context, ensure_ascii=False, separators=(",", ":"))},
        ],
        "temperature": 0.1,
        "max_tokens": settings.llm_max_output_tokens,
        "response_format": {
            "type": "json_schema",
            "json_schema": _response_schema(allowed_source_ids),
        },
    }
    headers = {"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            response = await client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        raise ReasoningProviderError("The configured reasoning provider is unavailable.") from exc

    body = response.json()
    if not body.get("success", False):
        raise ReasoningProviderError("The configured reasoning provider rejected the request.")
    raw = body.get("result", {}).get("response")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ReasoningProviderError("The reasoning provider did not return valid JSON.") from exc
    try:
        advisory = GroundedAdvisory.model_validate(raw)
    except ValidationError as exc:
        raise ReasoningProviderError("The reasoning provider returned an invalid advisory structure.") from exc
    _validate_advisory(advisory, context)
    return advisory


def _advisory_text(advisory: GroundedAdvisory) -> str:
    sections = [
        "Additional evidence-grounded reasoning",
        advisory.finding,
        advisory.explanation,
    ]
    for heading, items in (
        ("Weak points", advisory.weak_points),
        ("Missing evidence", advisory.missing_evidence),
        ("Recommended next steps", advisory.recommended_actions),
    ):
        if items:
            sections.append(f"{heading}\n" + "\n".join(f"• {item}" for item in items))
    return "\n\n".join(sections)


def _reasoning_metadata(
    *, status: str, fallback_used: bool, advisory: GroundedAdvisory | None = None
) -> dict[str, Any]:
    return {
        "status": status,
        "provider": settings.llm_provider if settings.llm_enabled else "deterministic",
        "model": settings.llm_model if settings.llm_enabled else None,
        "fallback_used": fallback_used,
        "finding": advisory.finding if advisory else None,
        "weak_points": advisory.weak_points if advisory else [],
        "missing_evidence": advisory.missing_evidence if advisory else [],
        "recommended_actions": advisory.recommended_actions if advisory else [],
        "source_ids": advisory.source_ids if advisory else [],
    }


async def apply_reasoning_layer(
    case: Any,
    question: str,
    deterministic_result: dict[str, Any],
    analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = copy.deepcopy(deterministic_result)
    if not settings.llm_enabled or settings.llm_provider.lower() in {"", "none", "deterministic"}:
        result["reasoning"] = _reasoning_metadata(status="deterministic", fallback_used=False)
        return result
    if result.get("claim_type") == "unsupported" or not result.get("citations"):
        result["reasoning"] = _reasoning_metadata(status="skipped_unsupported", fallback_used=True)
        return result

    context = _reasoning_context(case, question, result, analysis)
    try:
        if settings.llm_provider.lower() != "cloudflare":
            raise ReasoningProviderError("Unsupported reasoning provider.")
        advisory = await _cloudflare_reasoning(context)
    except ReasoningProviderError:
        if not settings.llm_allow_fallback:
            raise
        logger.warning("Guarded LLM reasoning unavailable; deterministic answer retained", exc_info=True)
        result["reasoning"] = _reasoning_metadata(status="deterministic_fallback", fallback_used=True)
        result.setdefault("limitations", []).append(
            "The optional LLM explanation layer was unavailable or failed validation; the evidence-controlled deterministic answer is shown."
        )
        return result

    result["answer"] = f"{result['answer']}\n\n{_advisory_text(advisory)}"
    result.setdefault("methodology", []).append(
        "A guarded LLM explanation was generated only from submitted case facts and the cited evidence; citation IDs and numeric claims were validated before display."
    )
    result["reasoning"] = _reasoning_metadata(
        status="grounded_llm", fallback_used=False, advisory=advisory
    )
    return result
