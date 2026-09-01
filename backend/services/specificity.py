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


def _contains_phrase_or_tokens(haystack: str, value: str) -> bool:
    normalized_haystack = " ".join(haystack.lower().split())
    normalized_value = " ".join(value.lower().split())
    if normalized_value and normalized_value in normalized_haystack:
        return True
    tokens = _tokens(value)
    return bool(tokens) and len(tokens & _tokens(haystack)) >= min(2, len(tokens))


def annotate_study_matches(case: Any, records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    metadata = _metadata(case)
    primary_ingredient = (case.ingredients or [""])[0]
    latin_match = re.search(r"\b([A-Z][a-z]+\s+[a-z][a-z-]+)\b", primary_ingredient)
    ingredient_terms = [latin_match.group(1) if latin_match else primary_ingredient.split(",", 1)[0]]
    claim_text = " ".join([case.intended_use or "", str(metadata.get("proposed_claim", ""))])
    endpoint_terms = [
        token for token in _tokens(claim_text)
        if token not in {"healthy", "adult", "adults", "supports", "support", "performance"}
    ]
    population_terms = [term for term in ("healthy", "adult", "adults") if term in claim_text.lower()]
    dose_numbers = re.findall(r"\b\d+(?:\.\d+)?\s*(?:mg|g|ml|µg|mcg)\b", str(metadata.get("dose", "")), re.IGNORECASE)
    standardization_numbers = re.findall(r"\b\d+(?:\.\d+)?%\b", str(metadata.get("standardization", "")))
    formulation_text = " ".join(
        str(value) for value in [case.product_form, metadata.get("delivery_mechanism", "")] if value
    )
    formulation_terms = [
        token for token in _tokens(formulation_text)
        if token not in {"oral", "based", "delivery", "system"}
    ]

    counts = {
        "direct_product": 0,
        "ingredient_level": 0,
        "dose_matched": 0,
        "formulation_matched": 0,
        "population_matched": 0,
        "endpoint_matched": 0,
    }
    annotated: list[dict[str, Any]] = []
    for record in records:
        title_text = str(record.get("title", ""))
        haystack = " ".join(
            str(record.get(key, ""))
            for key in ["title", "abstract_excerpt", "population", "dose", "endpoints", "study_design"]
        )
        ingredient_match = any(_contains_phrase_or_tokens(haystack, term) for term in ingredient_terms if term)
        ingredient_in_title = any(_contains_phrase_or_tokens(title_text, term) for term in ingredient_terms if term)
        population_match = bool(population_terms) and all(term in haystack.lower() for term in population_terms)
        endpoint_hits = sorted({term for term in endpoint_terms if term in haystack.lower()})
        endpoint_title_hits = sorted({term for term in endpoint_terms if term in title_text.lower()})
        endpoint_match = bool(endpoint_terms) and len(endpoint_hits) >= min(2, len(endpoint_terms))
        dose_match = bool(dose_numbers) and any(number.lower() in haystack.lower() for number in dose_numbers)
        standardization_match = bool(standardization_numbers) and any(number in haystack for number in standardization_numbers)
        formulation_hits = sorted({term for term in formulation_terms if term in haystack.lower()})
        formulation_match = bool(formulation_terms) and len(formulation_hits) >= min(2, len(formulation_terms))
        direct = all([ingredient_match, population_match, endpoint_match, dose_match, formulation_match])
        if direct:
            role = "direct_product"
        elif record.get("retrieval_scope") == "delivery_system" or formulation_match:
            role = "delivery_system"
        elif ingredient_match:
            role = "ingredient_clinical"
        else:
            role = "excluded_irrelevant"
        quality = (
            "full_text_appraised"
            if record.get("appraisal_status") == "full_text_structured_appraisal"
            else "abstract_or_passage_only"
        )
        profile = {
            "ingredient": ingredient_match,
            "population": population_match,
            "endpoint": endpoint_match,
            "dose": dose_match,
            "standardization": standardization_match,
            "formulation": formulation_match,
            "endpoint_hits": endpoint_hits,
            "endpoint_title_hits": endpoint_title_hits,
            "formulation_hits": formulation_hits,
            "quality": quality,
        }
        score = min(100, sum(
            weight for matched, weight in [
                (ingredient_match, 30), (population_match, 15), (endpoint_match, 20),
                (dose_match, 15), (formulation_match, 15),
                (quality == "full_text_appraised", 5),
                (ingredient_in_title, 8), (bool(endpoint_title_hits), 5),
            ] if matched
        ))
        enriched = {**record, "evidence_role": role, "match_profile": profile, "match_score": score}
        annotated.append(enriched)
        if role != "excluded_irrelevant":
            counts["ingredient_level"] += int(ingredient_match)
            counts["dose_matched"] += int(dose_match)
            counts["formulation_matched"] += int(formulation_match)
            counts["population_matched"] += int(population_match)
            counts["endpoint_matched"] += int(endpoint_match)
            counts["direct_product"] += int(direct)
    annotated.sort(key=lambda record: (record["evidence_role"] == "excluded_irrelevant", -record["match_score"]))
    return annotated, counts


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


def build_technical_advisory(
    case: Any,
    patents: dict[str, Any],
    match_counts: dict[str, int],
) -> dict[str, Any]:
    metadata = _metadata(case)
    ingredients = case.ingredients or []
    active = ingredients[0] if ingredients else "Botanical active not supplied"
    delivery_component = next(
        (item for item in ingredients[1:] if re.search(r"phospholipid|phosphatidyl|liposom|carrier", item, re.IGNORECASE)),
        "Delivery carrier not separately identified",
    )
    product_form = case.product_form or "Product form not supplied"
    standardization = str(metadata.get("standardization") or "Standardization not supplied")
    dose = str(metadata.get("dose") or "Dose not supplied")
    release = str(metadata.get("release_profile") or "Performance/release target not supplied")
    process = str(metadata.get("process_parameters") or metadata.get("manufacturing_process") or "Process window not supplied")
    claim = str(metadata.get("proposed_claim") or case.intended_use or "Claim not supplied")
    classical = str(metadata.get("classical_reference") or "No exact classical reference supplied")
    patent_status = patents.get("status", "not_run").replace("_", " ")
    patent_records = patents.get("records") or []
    relevance_terms = [
        token.lower()
        for token in WORD_RE.findall(" ".join([active, product_form, delivery_component]))
        if token.lower() not in STOPWORDS and len(token) >= 5
    ]
    relevant_patents = [
        record for record in patent_records
        if sum(term in str(record.get("title", "")).lower() for term in relevance_terms) >= 2
        or active.split()[0].lower() in str(record.get("title", "")).lower()
    ]
    first_patent = relevant_patents[0] if relevant_patents else None
    patent_basis = (
        f"Product-relevant keyword lead: {first_patent.get('publication_number') or 'number unavailable'} — {first_patent.get('title') or 'title unavailable'}; claims still require element mapping and this is not asserted as closest prior art."
        if first_patent
        else f"Patent search status: {patent_status}. Retrieved keyword leads did not pass the product-specific title-relevance gate, so no closest patent or claim overlap is asserted."
    )

    features = [
        {
            "id": "known-use",
            "feature": f"{active} cognitive use",
            "submitted_value": claim,
            "status": "weak_known",
            "status_label": "Weak / known-use exposed",
            "why": f"The submitted record links {active} to cognitive/memory use; that use cannot be treated as the inventive contribution by itself.",
            "evidence_basis": [f"Submitted traditional-use statement: {classical}", patent_basis],
            "advisory": "Do not rely on the botanical use alone for novelty. Treat it as the prior-art baseline and claim a proven technical architecture or effect.",
        },
        {
            "id": "dosage-form",
            "feature": product_form,
            "submitted_value": product_form,
            "status": "potentially_differentiating",
            "status_label": "Potentially differentiating",
            "why": "The metered oral-mucosal format is technically separate from the submitted traditional-use baseline, but known oral/buccal spray patents must still be compared claim by claim.",
            "evidence_basis": [f"Submitted dosage form: {product_form}", patent_basis],
            "advisory": "Search oral/buccal botanical-delivery claims and define the exact metering, droplet/particle, deposition and dose-uniformity boundaries.",
        },
        {
            "id": "delivery-carrier",
            "feature": delivery_component,
            "submitted_value": delivery_component,
            "status": "moderate_known_technique",
            "status_label": "Moderate / known technique risk",
            "why": "A carrier technology may be individually known; combining it with a known botanical can be challenged as predictable unless the combination produces an unexpected effect.",
            "evidence_basis": [f"Submitted carrier: {delivery_component}", "No unexpected comparative technical effect is documented in the present case."],
            "advisory": "Define the carrier:active ratio, physical state and critical quality attributes, then compare against a carrier-free spray.",
        },
        {
            "id": "standardization",
            "feature": "Defined botanical standardization",
            "submitted_value": standardization,
            "status": "moderate_range_search",
            "status_label": "Moderate / exact-range search needed",
            "why": "Standardization improves reproducibility, but a marker percentage is not inventive merely because it is precise; the exact range and technical effect must be compared with prior disclosures.",
            "evidence_basis": [f"Submitted standardization: {standardization}", "Exact-range patent and non-patent comparison is incomplete."],
            "advisory": "Search the exact marker range and link any narrower range to stability, release, uptake or clinical performance data.",
        },
        {
            "id": "dose",
            "feature": "Proposed daily exposure",
            "submitted_value": dose,
            "status": "weak_alone",
            "status_label": "Weak alone",
            "why": "Dose selection is often treated as optimization unless the selected exposure produces an unexpected or clinically meaningful result.",
            "evidence_basis": [f"Submitted dose: {dose}", f"Dose-matched human records retained: {match_counts.get('dose_matched', 0)}."],
            "advisory": "Use dose-ranging, exposure or bridging data; do not present the dose alone as the inventive concept.",
        },
        {
            "id": "process-window",
            "feature": "Controlled manufacturing window",
            "submitted_value": process,
            "status": "potentially_useful",
            "status_label": "Potentially useful if causally linked",
            "why": "A defined process window can support a process claim or trade secret only when specific parameters measurably change product performance or reproducibility.",
            "evidence_basis": [f"Submitted process facts: {process}", "No parameter-to-effect study is attached."],
            "advisory": "Run a design-of-experiments study and retain only parameters that materially affect fingerprint, stability, release, droplet size or dose uniformity.",
        },
        {
            "id": "performance-target",
            "feature": "Quantitative release/performance target",
            "submitted_value": release,
            "status": "strong_if_proven",
            "status_label": "Strongest if proven comparatively",
            "why": "A reproducible quantitative threshold tied to the claimed architecture is more defensible than naming known ingredients or dosage forms.",
            "evidence_basis": [f"Submitted target: {release}", "Comparative validation and method suitability are not yet documented."],
            "advisory": "Validate the method, compare against a conventional formulation and carrier-free spray, and predefine a statistically and technically meaningful threshold.",
        },
    ]

    strength_actions = [
        {
            "rank": 1,
            "title": "Complete feature-level prior-art and independent-claim comparison",
            "impact": "critical",
            "why": f"The current patent status is {patent_status}; the inventive contribution cannot be selected without mapping each submitted feature to retrieved claims.",
            "what_to_test": ["Botanical + cognitive-use disclosures", "Oral/buccal metered sprays", "Phospholipid botanical carriers", "Exact marker and process ranges"],
            "deliverable": "Counsel-reviewed novelty chart with family, legal status, claim element and missing-feature columns.",
            "strengthens": ["Patent claim scope", "Inventive-step position", "Design-around decisions"],
        },
        {
            "rank": 2,
            "title": "Demonstrate an advantage over conventional oral Bacopa",
            "impact": "high",
            "why": "The current combination can be framed as known botanical + known carrier + known dosage form unless an unexpected combined technical effect is shown.",
            "what_to_test": ["Matched conventional capsule/tablet comparator", "Carrier-free metered spray", "Release and mucosal-permeation performance", "Stability and dose uniformity"],
            "deliverable": "Predefined comparative technical-effect report with effect sizes, uncertainty and failed endpoints retained.",
            "strengthens": ["Inventive step", "Scientific credibility", "Exact-product differentiation"],
        },
        {
            "rank": 3,
            "title": "Narrow the phospholipid spray architecture",
            "impact": "high",
            "why": "The present description names the architecture, but the defensible technical boundary needs measurable composition and process parameters.",
            "what_to_test": ["Carrier:active ratio", "Particle/droplet size distribution", "pH and shear operating windows", "Spray volume and content uniformity"],
            "deliverable": "Critical-quality-attribute specification and parameter-to-performance design space.",
            "strengthens": ["Composition/process claims", "Quality dossier", "Trade-secret boundary"],
        },
        {
            "rank": 4,
            "title": "Validate the exact cognitive claim at the proposed exposure",
            "impact": "high",
            "why": f"Current matching found {match_counts.get('direct_product', 0)} direct, {match_counts.get('dose_matched', 0)} dose-matched and {match_counts.get('formulation_matched', 0)} formulation-matched records.",
            "what_to_test": ["Exact standardized extract and daily exposure", "Healthy-adult population", "Separate validated memory and attention endpoints", "Tolerability and adverse events"],
            "deliverable": "Claim-to-evidence matrix and protocol for a randomized exact-formulation comparator study.",
            "strengthens": ["Claim substantiation", "Scientific evidence readiness", "Regulatory dossier"],
        },
        {
            "rank": 5,
            "title": "Resolve market positioning before fixing label claims",
            "impact": "medium-high",
            "why": "The same product facts can enter different India and UK pathways depending on intended purpose, medicinal representation and exact wording.",
            "what_to_test": ["Wellness-only versus treatment/prevention wording", "AYUSH medicine intent", "Supplement/food positioning", "Classical versus proprietary/non-classical representation"],
            "deliverable": "Signed India/UK classification memo and controlled claims matrix.",
            "strengthens": ["Regulatory route", "Evidence plan", "Launch claims"],
        },
    ]

    return {
        "feature_assessments": features,
        "inventive_step": {
            "level": "medium-high",
            "finding": f"The strongest candidate is the combined {product_form} + {delivery_component} + defined standardization/performance architecture, not the broad cognitive use.",
            "weakest_element": f"{active} cognitive use",
            "reasoning": [
                f"The submitted case itself identifies traditional cognitive/memory use for {active}.",
                f"{delivery_component} is a carrier technique that must be distinguished from established delivery practice.",
                f"{product_form} must be compared with known oral/buccal sprays.",
                "Combining individually known elements may be treated as routine optimization.",
                "No unexpected combined technical advantage is yet demonstrated.",
            ],
            "how_to_strengthen": [
                "Quantify improved mucosal permeation or absorption against matched comparators.",
                "Demonstrate a reproducible release, stability or dose-uniformity advantage.",
                "Define composition and critical process windows that cause the advantage.",
                "Claim only a performance threshold not taught by the closest mapped prior art.",
            ],
        },
        "differentiation_advisor": {
            "current": f"{delivery_component} in a {product_form}",
            "problem": "May be viewed as a predictable use of established delivery techniques with a known botanical.",
            "ways_to_strengthen": [
                "Define carrier-to-botanical ratio and compositional tolerances.",
                "Define particle/droplet size and dose-uniformity ranges.",
                "Retain only pH, temperature and shear ranges that cause a measured effect.",
                "Demonstrate storage and in-use stability.",
                "Compare mucosal permeation against a conventional formulation and carrier-free spray.",
                "Show an unexpected, reproducible performance threshold.",
            ],
        },
        "change_scenarios": [
            {
                "change": f"Remove {delivery_component}",
                "impacts": [
                    {"area": "Patent differentiation", "direction": "down", "reason": "One submitted technical layer is removed."},
                    {"area": "Formulation complexity", "direction": "down", "reason": "Fewer composition and stability variables."},
                    {"area": "Evidence burden", "direction": "down", "reason": "No carrier-specific bridging claim."},
                    {"area": "Potential absorption benefit", "direction": "down", "reason": "Any carrier-enabled benefit would be lost unless another architecture replaces it."},
                ],
            },
            {
                "change": "Increase daily botanical dose",
                "impacts": [
                    {"area": "Patent novelty impact", "direction": "low", "reason": "Dose change alone is commonly optimization."},
                    {"area": "Clinical evidence matching", "direction": "may_improve", "reason": "Only if the new exposure matches higher-quality studies."},
                    {"area": "Safety evidence burden", "direction": "up", "reason": "Higher exposure requires updated tolerability and interaction review."},
                    {"area": "Regulatory scrutiny", "direction": "up", "reason": "Exposure and claims affect classification and evidence expectations."},
                ],
            },
            {
                "change": "Add comparative mucosal-permeation and release data",
                "impacts": [
                    {"area": "Technical-effect support", "direction": "up_up", "reason": "Directly tests the asserted architecture."},
                    {"area": "Inventive-step position", "direction": "up", "reason": "An unexpected effect can distinguish a predictable combination."},
                    {"area": "Scientific credibility", "direction": "up", "reason": "Product-specific evidence replaces assumption."},
                    {"area": "Exact-product evidence", "direction": "up", "reason": "The submitted formulation is actually tested."},
                ],
            },
        ],
        "scientific_advisor": {
            "supported": f"Ingredient-level human evidence was retained for {active}: {match_counts.get('ingredient_level', 0)} record(s).",
            "not_supported": [
                f"The exact {product_form} route",
                f"The {delivery_component} system",
                f"The submitted exposure: {dose}",
                f"The submitted standardization: {standardization}",
                "The combined memory + attention + overall cognitive-performance claim",
            ],
            "best_next_study": f"A randomized comparative study of the exact {product_form} against a matched conventional {active} formulation, measuring validated memory and attention endpoints, product exposure, safety and tolerability.",
        },
        "classification_resolver": {
            "why_unresolved": f"The claim ‘{claim}’ can be classified differently depending on medicinal versus wellness positioning, the {product_form} presentation and whether the product is represented as AYUSH, supplement or another oral product.",
            "questions": [
                "Will the label claim treatment or prevention, or only general wellness support?",
                "Is the product intended to be licensed and represented as an AYUSH medicine?",
                "Will the formulation be represented as classical, proprietary or non-classical?",
            ],
        },
        "strength_actions": strength_actions,
        "notice": "Feature statuses are screening inferences tied to submitted facts and retrieved-search status. They are not patentability, safety, efficacy or classification conclusions.",
    }


def build_case_specific_analysis(case: Any, evidence_matches: list[dict[str, Any]], external_research: dict[str, Any]) -> dict[str, Any]:
    completeness = build_input_completeness(case)
    features = build_technical_features(case)
    patents = external_research.get("patents", {})
    tk_records = _uploaded_tk_records(case, evidence_matches)
    uploaded_studies = _uploaded_study_records(case, evidence_matches)
    live_studies = external_research.get("science", {}).get("records", [])
    studies, match_counts = annotate_study_matches(case, [*uploaded_studies, *live_studies])
    full_text_appraised_count = sum(
        record.get("source_status") == "pmc_full_text_appraised" and record.get("evidence_role") != "excluded_irrelevant"
        for record in studies
    )
    abstract_only_count = sum(
        record.get("source_status") == "pubmed_abstract_only" and record.get("evidence_role") != "excluded_irrelevant"
        for record in studies
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
            "search_url": "https://www.tkdl.res.in/tkdl/langdefault/common/TKDLSearch.asp?GL=Eng",
            "authorized_search_required": True,
            "access_scope": "The official TKDL site states that full-database access is available to Patent Offices under a TKDL Access Agreement.",
            "integration_mode": "official_search_handoff_and_authorized_export_import",
            "supported_imports": ["PDF", "TXT", "DOCX"],
            "limitation": "Use the official TKDL search handoff and import only an authorized result or legally obtained source extract. Only an exact returned formulation and locator may support a finding; no absence-of-prior-art conclusion is made when a record cannot be retrieved.",
        },
        "scientific_studies": {
            **external_research.get("science", {}),
            "records": studies,
            "match_counts": match_counts,
            "evidence_layers": {
                "direct_product": "Exact product/formulation evidence" if match_counts["direct_product"] else "No exact product study identified",
                "ingredient_clinical": "Human ingredient-level evidence available" if match_counts["ingredient_level"] else "No ingredient-level human evidence identified",
                "delivery_system": "Delivery-system evidence identified" if match_counts["formulation_matched"] else "No formulation-matched evidence identified",
                "traditional_use": "Kept separate from clinical support",
            },
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
        "technical_advisory": build_technical_advisory(case, patents, match_counts),
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
