import re
from typing import Any

from services.evidence import evidence_citation

FACT_FIELDS = [
    ("ingredients", "Ingredient identity", "List botanical/common names and plant parts", "patent, TK, science"),
    ("quantitative_composition", "Quantitative composition", "Give the amount of every active per unit", "patent, regulatory, science"),
    ("standardization", "Extract standardization", "Give marker compounds and acceptance ranges", "patent, quality"),
    ("extraction_ratio", "Extraction ratio and solvent", "Give DER, solvent system and extract type", "patent, comparability"),
    ("dose", "Proposed dose", "Give unit dose, frequency and duration", "regulatory, science"),
    ("release_profile", "Release profile", "Give test method, timepoints and acceptance limits", "patent, performance"),
    ("manufacturing_process", "Manufacturing process", "Give the ordered unit operations", "patent, trade secret"),
    ("process_parameters", "Critical process parameters", "Give temperatures, times, pH, pressures and ranges", "patent, reproducibility"),
    ("intended_use", "Exact proposed claim", "State the population, outcome and claim wording", "regulatory, science"),
    ("biological_sourcing", "Resource provenance", "Give species, location, supplier, access date and party facts", "ABS"),
    ("classical_reference", "Classical source reference", "Give text, chapter, formulation and page/verse", "TK, patent"),
]
WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9-]{2,}")
STOPWORDS = {
    "and", "the", "for", "from", "with", "extract", "tablet", "capsule", "product",
    "composition", "process", "daily", "standardized", "formulation", "using", "per",
}


def _metadata(case: Any) -> dict[str, Any]:
    return case.metadata_json or {}


def _value(case: Any, key: str) -> str:
    metadata = _metadata(case)
    direct = {
        "ingredients": "; ".join(case.ingredients or []),
        "intended_use": case.intended_use or "",
        "biological_sourcing": case.biological_sourcing or "",
    }
    return str(direct.get(key, metadata.get(key, ""))).strip()


def build_input_completeness(case: Any) -> dict[str, Any]:
    supplied = []
    missing = []
    for key, label, request, blocks in FACT_FIELDS:
        item = {"key": key, "label": label, "request": request, "blocks": blocks}
        if _value(case, key):
            supplied.append({**item, "value": _value(case, key)})
        else:
            missing.append(item)
    score = round(100 * len(supplied) / len(FACT_FIELDS))
    return {
        "score": score,
        "supplied_count": len(supplied),
        "required_count": len(FACT_FIELDS),
        "supplied": supplied,
        "missing": missing,
        "status": "decision_ready" if score >= 85 else "material_gaps" if score < 60 else "review_ready",
    }


def build_technical_features(case: Any) -> list[dict[str, Any]]:
    features = []
    for key, label, request, blocks in FACT_FIELDS:
        value = _value(case, key)
        features.append(
            {
                "id": key,
                "feature": label,
                "submitted_value": value or "Not supplied",
                "status": "submitted" if value else "missing",
                "evidence_required": request,
                "decision_areas": blocks,
            }
        )
    return features


def _tokens(value: str) -> set[str]:
    return {token.lower() for token in WORD_RE.findall(value) if token.lower() not in STOPWORDS}


def build_novelty_chart(features: list[dict[str, Any]], patent_landscape: dict[str, Any]) -> list[dict[str, Any]]:
    records = patent_landscape.get("records", [])
    chart = []
    for feature in features:
        value = feature["submitted_value"]
        if feature["status"] == "missing":
            chart.append(
                {
                    **feature,
                    "status": "not_assessable",
                    "reason": "This feature was not supplied, so an element-level comparison would be speculative.",
                    "claim_overlaps": [],
                }
            )
            continue
        feature_tokens = _tokens(value)
        overlaps = []
        for record in records:
            for claim in record.get("claims", []):
                claim_tokens = _tokens(claim.get("text", ""))
                matched = sorted(feature_tokens & claim_tokens)
                minimum = 1
                if len(matched) >= minimum:
                    overlaps.append(
                        {
                            "publication_number": record.get("publication_number"),
                            "family_id": record.get("family_id"),
                            "claim": claim.get("claim"),
                            "matched_terms": matched,
                            "claim_excerpt": claim.get("text", "")[:600],
                            "url": record.get("url"),
                            "source": record.get("source"),
                        }
                    )
        if overlaps:
            status = "overlap_found"
            reason = "One or more retrieved claims contain terms from this submitted feature; legal element mapping is still required."
        elif patent_landscape.get("status") == "live":
            status = "no_overlap_in_retrieved_set"
            reason = "No lexical overlap was found in the retrieved claim sample. This is not a novelty or FTO clearance."
        else:
            status = "search_not_completed"
            reason = patent_landscape.get("limitation", "A live claim-level search was not completed.")
        chart.append({**feature, "status": status, "reason": reason, "claim_overlaps": overlaps[:5]})
    return chart


def _sentence(text: str, patterns: list[str], fallback: str) -> str:
    for sentence in re.split(r"(?<=[.!?])\s+", " ".join(text.split())):
        if any(re.search(pattern, sentence, re.IGNORECASE) for pattern in patterns):
            return sentence[:500]
    return fallback


def _uploaded_tk_records(case: Any, matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records = []
    ingredient_tokens = _tokens(" ".join(case.ingredients or []))
    indicators = [r"ayurved", r"traditional", r"classical", r"formul", r"samhita", r"nighantu", r"pharmacopoe"]
    for match in matches:
        content = " ".join(match.get("content", "").split())
        if not content:
            continue
        matched_ingredients = sorted(ingredient_tokens & _tokens(content))
        if not matched_ingredients and not any(re.search(item, content, re.IGNORECASE) for item in indicators):
            continue
        citation = evidence_citation(case.id, match)
        records.append(
            {
                "source_title": match.get("filename"),
                "formulation": _sentence(content, [r"formul", r"prepar", r"compris", r"contain"], "No formulation sentence was identified in this passage."),
                "exact_passage": content[:900],
                "locator": citation.get("locator"),
                "content_sha256": citation.get("content_sha256"),
                "matched_ingredients": matched_ingredients,
                "citation": citation,
                "source_status": "uploaded_case_document",
            }
        )
    return records[:8]


def _uploaded_study_records(case: Any, matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records = []
    indicators = [r"participant", r"patient", r"randomi[sz]", r"placebo", r"trial", r"endpoint", r"mg\b", r"confidence interval"]
    for match in matches:
        content = " ".join(match.get("content", "").split())
        if not content or not any(re.search(item, content, re.IGNORECASE) for item in indicators):
            continue
        citation = evidence_citation(case.id, match)
        records.append(
            {
                "pmid": None,
                "title": match.get("filename"),
                "journal": "User-supplied case document",
                "publication_date": "Not verified",
                "url": citation.get("url"),
                "population": _sentence(content, [r"participant", r"patient", r"subject", r"volunteer", r"n\s*="], "Not reported in this passage."),
                "dose": _sentence(content, [r"\d+(?:\.\d+)?\s*(?:mg|g|ml|µg|mcg)", r"once daily", r"twice daily"], "Not reported in this passage."),
                "endpoints": _sentence(content, [r"primary outcome", r"endpoint", r"score", r"measured", r"significant"], "No endpoint sentence was extracted from this passage."),
                "limitations": _sentence(content, [r"limitation", r"small sample", r"short duration", r"bias", r"not significant"], "Limitations were not stated in this passage; full-text appraisal is required."),
                "abstract_excerpt": content[:700],
                "locator": citation.get("locator"),
                "citation": citation,
                "source_status": "uploaded_case_document_unappraised",
            }
        )
    return records[:8]


def _specific_recommendations(case: Any, completeness: dict[str, Any], patents: dict[str, Any], studies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    metadata = _metadata(case)
    recommendations = []

    def add(title: str, basis: str, action: str, output: str) -> None:
        recommendations.append({"title": title, "basis": basis, "action": action, "decision_output": output})

    if metadata.get("release_profile"):
        add(
            "Test the submitted release boundary",
            f"Submitted release profile: {metadata['release_profile']}",
            "Run a discriminating dissolution/release study against the nearest conventional format and predefine timepoint acceptance ranges.",
            "A feature-by-feature technical-effect table that can support or reject a delivery claim.",
        )
    if metadata.get("extraction_ratio") or metadata.get("standardization"):
        basis = "; ".join(item for item in [metadata.get("extraction_ratio"), metadata.get("standardization")] if item)
        add(
            "Lock the extract fingerprint",
            f"Submitted extraction facts: {basis}",
            "Define marker ranges, solvent residuals and orthogonal fingerprint acceptance criteria, then compare at least three batches.",
            "A reproducible compositional boundary for patent, quality and equivalence review.",
        )
    if metadata.get("quantitative_composition") or metadata.get("dose"):
        basis = "; ".join(item for item in [metadata.get("quantitative_composition"), metadata.get("dose")] if item)
        add(
            "Align evidence to actual exposure",
            f"Submitted exposure: {basis}",
            "Map each cited study's ingredient identity, extract, daily exposure and duration against this product; reject indirect matches explicitly.",
            "An exposure-normalized evidence matrix, not a generic ingredient bibliography.",
        )
    if patents.get("records"):
        first = patents["records"][0]
        add(
            "Draft against a retrieved patent family",
            f"Retrieved publication {first.get('publication_number')} / family {first.get('family_id') or 'not reported'}: {first.get('title')}",
            "Have patent counsel map every proposed independent-claim element to the retrieved family and its cited documents.",
            "Counsel-reviewed novelty and FTO charts with family/legal-status checks.",
        )
    if studies:
        first = studies[0]
        add(
            "Appraise the closest retrieved study",
            f"Closest retrieved record: {first.get('title')} ({first.get('pmid') or first.get('locator') or 'case document'})",
            "Verify the full text, risk of bias, population, exact dose, endpoint validity, effect size and applicability before supporting a claim.",
            "A signed evidence-to-claim appraisal with excluded-evidence reasons.",
        )
    for item in completeness["missing"][:4]:
        add(
            f"Resolve missing {item['label'].lower()}",
            "No value was supplied for this decision-critical field.",
            item["request"],
            f"Unlocks a more specific {item['blocks']} assessment.",
        )
    return recommendations[:8]


def build_case_specific_analysis(case: Any, evidence_matches: list[dict[str, Any]], external_research: dict[str, Any]) -> dict[str, Any]:
    completeness = build_input_completeness(case)
    features = build_technical_features(case)
    patents = external_research.get("patents", {})
    tk_records = _uploaded_tk_records(case, evidence_matches)
    uploaded_studies = _uploaded_study_records(case, evidence_matches)
    live_studies = external_research.get("science", {}).get("records", [])
    studies = [*uploaded_studies, *live_studies]
    full_text_appraised_count = sum(
        record.get("source_status") == "pmc_full_text_appraised" for record in live_studies
    )
    abstract_only_count = sum(
        record.get("source_status") == "pubmed_abstract_only" for record in live_studies
    )
    tk_query = " ".join([*(case.ingredients or []), _value(case, "classical_reference"), case.intended_use or ""]).strip()
    return {
        "input_completeness": completeness,
        "technical_features": features,
        "patent_landscape": patents,
        "novelty_claim_chart": build_novelty_chart(features, patents),
        "traditional_knowledge": {
            "status": "exact_passages_retrieved" if tk_records else "no_exact_passage_retrieved",
            "records": tk_records,
            "query": tk_query,
            "search_url": "https://www.tkdl.res.in/tkdl/langdefault/common/Global_Search.asp?GL=Eng",
            "authorized_search_required": True,
            "limitation": "Use the TKDL Global Search handoff for manual verification. Only an exact returned formulation and locator may support a finding; no absence-of-prior-art conclusion is made when a record cannot be retrieved.",
        },
        "scientific_studies": {
            **external_research.get("science", {}),
            "records": studies,
            "uploaded_record_count": len(uploaded_studies),
            "live_record_count": len(live_studies),
            "full_text_appraised_count": full_text_appraised_count,
            "abstract_only_count": abstract_only_count,
            "notice": (
                "Traditional use is not equivalent to clinically established efficacy. "
                f"PMC full text was structurally appraised for {full_text_appraised_count} live record(s); "
                "remaining records are abstract- or uploaded-passage-level. Automated appraisal is not "
                "a substitute for RoB 2, ROBINS-I or qualified expert review."
            ),
        },
        "specific_recommendations": _specific_recommendations(case, completeness, patents, studies),
        "data_requests": [
            {"field": item["key"], "question": item["request"], "blocks": item["blocks"]}
            for item in completeness["missing"]
        ],
    }


def build_specific_design_around(case: Any, specific: dict[str, Any], recommended_route: list[str], citations: list[dict[str, Any]]) -> dict[str, Any]:
    metadata = _metadata(case)
    alternatives = []

    def add(identifier: str, dimension: str, fact: str, change: str, rationale: str, evidence: list[str], risks: list[str]) -> None:
        alternatives.append(
            {
                "id": identifier,
                "dimension": dimension,
                "basis": fact,
                "proposed_change": change,
                "rationale": rationale,
                "evidence_required": evidence,
                "residual_risks": risks,
                "claim_type": "inference",
                "requires_human_review": True,
                "citations": citations,
            }
        )

    if metadata.get("release_profile"):
        add(
            "release-boundary", "Measured release architecture", f"Submitted fact: {metadata['release_profile']}",
            "Define a narrower, testable release window and retain it only if comparative testing shows a material technical effect.",
            "The design direction is tied to the submitted profile instead of assuming that any modified release is novel.",
            ["Validated release method", "Comparator profile", "Predefined acceptance window", "Closest-claim chart"],
            ["Overlap with retrieved controlled-release claims", "Expected optimization", "Scale-up drift"],
        )
    if metadata.get("extraction_ratio") or metadata.get("standardization"):
        fact = "; ".join(item for item in [metadata.get("extraction_ratio"), metadata.get("standardization")] if item)
        add(
            "fingerprint-boundary", "Extract fingerprint boundary", f"Submitted fact: {fact}",
            "Test whether a tighter marker/fingerprint range produces a reproducible advantage; claim only the proven range and effect.",
            "This changes an ingredient-level idea into a measurable compositional hypothesis.",
            ["Orthogonal chemical fingerprint", "Marker-range batches", "Comparative activity/stability data"],
            ["Routine standardization", "Marker not causally linked to effect", "Prior disclosure of same range"],
        )
    if metadata.get("process_parameters") or metadata.get("manufacturing_process"):
        fact = "; ".join(item for item in [metadata.get("manufacturing_process"), metadata.get("process_parameters")] if item)
        add(
            "process-window", "Critical process window", f"Submitted fact: {fact}",
            "Identify the parameters that actually change yield, fingerprint, release or stability and bound only those critical ranges.",
            "A parameter-effect relationship is more specific than reciting the current manufacturing steps.",
            ["Design-of-experiments protocol", "Critical parameter ranges", "Three-batch reproducibility", "Trade-secret decision log"],
            ["Routine optimization", "Non-critical parameter", "Disclosure weakens secrecy"],
        )
    if metadata.get("quantitative_composition") or metadata.get("dose"):
        fact = "; ".join(item for item in [metadata.get("quantitative_composition"), metadata.get("dose")] if item)
        add(
            "exposure-claim", "Exposure-aligned claim", f"Submitted fact: {fact}",
            "Narrow the population, dose, duration and outcome to the exposure actually supported by product-specific evidence.",
            "This prevents generic ingredient studies from being treated as proof for the submitted formulation.",
            ["Dose-equivalence table", "Population and endpoint rationale", "Safety margin", "Market-specific label review"],
            ["Reduced commercial breadth", "Study extract mismatch", "Jurisdiction-specific classification"],
        )
    if len(alternatives) < 4:
        for request in specific.get("data_requests", []):
            if len(alternatives) >= 4:
                break
            add(
                f"missing-{request['field']}", "Unresolved design input", "No submitted technical fact is available.",
                request["question"], "The system will not invent a design-around without a measurable starting feature.",
                [request["question"]], [f"Assessment remains blocked for {request['blocks']}"],
            )
    return {
        "recommended_route": recommended_route,
        "alternatives": alternatives,
        "reviewer_inputs": {
            "patent_claim_chart": [item["reason"] for item in specific.get("novelty_claim_chart", []) if item["status"] != "not_assessable"][:4],
            "missing_decision_facts": [item["question"] for item in specific.get("data_requests", [])[:6]],
        },
        "notice": "Each design direction is linked to a submitted fact and a falsifiable test plan. It is not a patentability, safety or regulatory conclusion.",
    }
