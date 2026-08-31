from typing import Any


def build_claim_evidence_graph(
    classification: dict[str, Any],
    risks: list[dict[str, Any]],
    challenges: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    claims: list[dict[str, Any]] = [
        {
            "id": "claim-classification",
            "text": classification["label"],
            "claim_type": "interpretation",
            "status": "supported" if classification.get("citations") else "unsupported",
            "confidence": classification.get("confidence", 0.0),
        }
    ]
    evidence_by_id: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []

    def attach(claim_id: str, citations: list[dict[str, Any]], relation: str) -> None:
        for citation in citations:
            evidence_id = f"evidence-{citation['id']}"
            evidence_by_id[evidence_id] = {
                "id": evidence_id,
                "citation_id": citation["id"],
                "title": citation["title"],
                "source_type": citation.get("source_type", "official"),
                "support_status": citation["support_status"],
                "jurisdiction": citation["jurisdiction"],
                "effective_date": citation["effective_date"],
                "locator": citation.get("locator"),
                "content_sha256": citation.get("content_sha256"),
            }
            edges.append(
                {
                    "id": f"edge-{claim_id}-{citation['id']}-{len(edges)}",
                    "source": evidence_id,
                    "target": claim_id,
                    "relation": relation,
                }
            )

    attach("claim-classification", classification.get("citations", []), "supports")
    for risk in risks:
        claim_id = f"claim-risk-{risk['key']}"
        citations = risk.get("citations", [])
        claims.append(
            {
                "id": claim_id,
                "text": risk["summary"],
                "claim_type": risk.get("claim_type", "inference"),
                "status": "qualified" if citations else "unsupported",
                "confidence": round(min(0.9, max(0.1, risk["score"] / 100)), 2),
            }
        )
        attach(claim_id, citations, "qualifies")

    for reviewer, findings in challenges.items():
        for index, finding in enumerate(findings):
            claim_id = f"claim-{reviewer}-{index + 1}"
            citations = finding.get("citations", [])
            claims.append(
                {
                    "id": claim_id,
                    "text": finding["objection"],
                    "claim_type": "interpretation",
                    "status": "qualified" if citations else "unsupported",
                    "confidence": 0.62 if citations else 0.2,
                }
            )
            attach(claim_id, citations, "supports-review")

    supported = sum(claim["status"] != "unsupported" for claim in claims)
    return {
        "claims": claims,
        "evidence": list(evidence_by_id.values()),
        "edges": edges,
        "summary": {
            "claim_count": len(claims),
            "evidence_count": len(evidence_by_id),
            "supported_or_qualified": supported,
            "unsupported": len(claims) - supported,
            "coverage": round(supported / max(1, len(claims)), 3),
        },
        "notice": "A citation link records traceability, not independent verification or legal correctness.",
    }


def build_design_around(
    case: Any,
    ip_strategy: dict[str, Any],
    challenges: dict[str, list[dict[str, Any]]],
    citations: list[dict[str, Any]],
) -> dict[str, Any]:
    process = case.metadata_json.get("manufacturing_process", "the manufacturing process")
    product_form = case.product_form or "the delivery format"
    alternatives = [
        {
            "id": "delivery-architecture",
            "dimension": "Delivery architecture",
            "proposed_change": f"Define measurable release, stability or bioavailability parameters that distinguish {product_form} from conventional delivery.",
            "rationale": "A technically demonstrated delivery contribution may be more defensible than a known botanical ingredient or traditional use.",
            "evidence_required": ["Comparative release profile", "Protocol and raw data", "Closest-prior-art claim chart"],
            "residual_risks": ["Obvious optimization", "Insufficient unexpected technical effect"],
        },
        {
            "id": "process-window",
            "dimension": "Controlled process window",
            "proposed_change": f"Convert {process} into a bounded, reproducible process window with critical parameters and acceptance criteria.",
            "rationale": "A reproducible process can support patent claims or protected know-how without claiming traditional knowledge itself.",
            "evidence_required": ["Critical-process-parameter study", "Batch reproducibility", "Trade-secret access controls"],
            "residual_risks": ["Routine optimization", "Disclosure may weaken secrecy"],
        },
        {
            "id": "claim-narrowing",
            "dimension": "Claim and indication scope",
            "proposed_change": "Narrow the proposed claim to the population, dose, duration and measurable outcome actually supported by evidence.",
            "rationale": "Tighter claims reduce regulatory ambiguity and prevent traditional-use statements from being presented as clinical proof.",
            "evidence_required": ["Claim-to-evidence matrix", "Safety justification", "Market-specific label review"],
            "residual_risks": ["Reduced commercial breadth", "Different classification across markets"],
        },
        {
            "id": "portfolio",
            "dimension": "Layered rights portfolio",
            "proposed_change": "Pair narrowly tested technical claims with trademark protection, controlled know-how and documented resource provenance.",
            "rationale": "A portfolio remains useful when broad composition claims are constrained by prior art or traditional knowledge.",
            "evidence_required": ["Brand clearance", "Confidentiality controls", "Resource provenance ledger"],
            "residual_risks": ["Territorial clearance", "ABS obligations remain fact-specific"],
        },
    ]
    for alternative in alternatives:
        alternative.update(
            {
                "claim_type": "inference",
                "requires_human_review": True,
                "citations": citations,
            }
        )
    return {
        "recommended_route": ip_strategy.get("recommended_strategy", []),
        "alternatives": alternatives,
        "reviewer_inputs": {
            reviewer: [finding["objection"] for finding in findings]
            for reviewer, findings in challenges.items()
        },
        "notice": "These are counterfactual design directions, not patentability, safety or regulatory conclusions.",
    }
