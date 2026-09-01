import json
import re
from pathlib import Path
from typing import Any

from config import settings
from services.assurance import build_claim_evidence_graph
from services.evidence import evidence_citation, retrieval_status
from services.research import run_external_research
from services.specificity import build_case_specific_analysis, build_specific_design_around

SOURCE_PATH = Path(__file__).resolve().parents[1] / "data" / "sources.json"
DISCLAIMER = (
    "Decision support only — not legal, regulatory, medical or patent advice. "
    "Verify current law and obtain qualified human review before filing or market entry."
)


def load_sources() -> list[dict[str, Any]]:
    return json.loads(SOURCE_PATH.read_text(encoding="utf-8"))


SOURCES = load_sources()
SOURCE_BY_ID = {source["id"]: source for source in SOURCES}


def public_citation(source_id: str, excerpt: str | None = None) -> dict[str, str]:
    source = SOURCE_BY_ID[source_id]
    return {
        "id": source["id"],
        "title": source["title"],
        "authority": source["authority"],
        "jurisdiction": source["jurisdiction"],
        "effective_date": source["effective_date"],
        "url": source["url"],
        "support_status": source["support_status"],
        "excerpt": excerpt or source["summary"],
        "source_type": "official",
        "locator": source.get("locator"),
    }


def _text(case: Any) -> str:
    fields = [
        case.title,
        case.description,
        case.product_form or "",
        case.intended_use or "",
        case.biological_sourcing or "",
        " ".join(case.ingredients or []),
        " ".join(str(value) for value in (case.metadata_json or {}).values() if value),
    ]
    return " ".join(fields).lower()


def _contains(text: str, words: list[str]) -> bool:
    return any(word in text for word in words)


def classify_product(case: Any) -> dict[str, Any]:
    text = " ".join(
        value.lower()
        for value in [case.title, case.description, case.product_form or "", case.intended_use or "", _metadata_claim(case)]
        if value
    )
    non_disease_claim = _contains(text, ["without a disease-treatment claim", "without a disease treatment claim", "non-therapeutic claim"])
    therapeutic = _contains(text, ["treat", "cure", "prevent", "therapy", "disease", "pain", "diabetes"]) and not non_disease_claim
    food = _contains(text, ["food", "drink", "tea", "beverage", "nutrition", "supplement", "edible"])
    cosmetic = _contains(text, ["cosmetic", "skin", "hair", "cream", "serum", "shampoo"])
    if therapeutic:
        label = "Potential ASU drug / botanical medicinal product"
        pathway = "Therapeutic claims are likely to trigger a medicines pathway; confirm exact ASU/proprietary classification."
        confidence = 0.74
        citation_ids = ["drugs-cosmetics-act-india"]
    elif food:
        label = "Potential Ayurveda Aahara / food product"
        pathway = "Check ingredient eligibility, scheduled formulation, claims, labelling and licensing under the food pathway."
        confidence = 0.76
        citation_ids = ["fssai-ayurveda-aahara-2022"]
    elif cosmetic:
        label = "Potential cosmetic with botanical ingredients"
        pathway = "Classification depends on composition, presentation and whether claims remain cosmetic rather than therapeutic."
        confidence = 0.68
        citation_ids = ["drugs-cosmetics-act-india"]
    elif _contains(text, ["wellbeing", "wellness", "stress", "resilience", "support"]):
        label = "Provisional classification: requires route determination"
        pathway = "Candidate pathways are an AYUSH proprietary medicine, a nutraceutical/food supplement, or another applicable oral wellness-product pathway. The final route depends on exact claims, dosage form, composition and market presentation."
        confidence = 0.63
        citation_ids = ["fssai-ayurveda-aahara-2022", "drugs-cosmetics-act-india"]
    else:
        label = "Classification unresolved"
        pathway = (
            "The description does not provide enough claim and dosage information for a defensible classification."
        )
        confidence = 0.42
        citation_ids = ["drugs-cosmetics-act-india", "fssai-ayurveda-aahara-2022"]
    return {
        "label": label,
        "pathway": pathway,
        "confidence": confidence,
        "requires_human_review": True,
        "status": "unresolved",
        "candidate_pathways": [
            "AYUSH proprietary medicine",
            "Nutraceutical / food supplement",
            "Other applicable oral wellness-product pathway",
        ] if label == "Provisional classification: requires route determination" else [label],
        "decision_factors": ["Exact intended claim", "Dosage form and route", "Composition and dose", "Labelling and market presentation"],
        "citations": [public_citation(item) for item in citation_ids],
    }


def _metadata_claim(case: Any) -> str:
    return str((case.metadata_json or {}).get("proposed_claim", ""))


def build_genome(case: Any) -> dict[str, Any]:
    ingredients = case.ingredients or ["Ingredients not yet supplied"]
    process = case.metadata_json.get("manufacturing_process", "Manufacturing process not yet described")
    delivery = case.metadata_json.get("delivery_mechanism", case.product_form or "Product form not specified")
    claimed_effect = case.intended_use or "Intended use not specified"
    nodes = [
        {
            "id": "invention",
            "label": case.title,
            "type": "invention",
            "status": "current",
        },
        {
            "id": "ingredients",
            "label": ", ".join(ingredients[:5]),
            "type": "ingredients",
            "status": "review",
        },
        {
            "id": "traditional",
            "label": "Classical formulation"
            if case.classical_formulation
            else "Traditional-use relationship unverified",
            "type": "traditional_use",
            "status": "risk" if case.classical_formulation else "review",
        },
        {
            "id": "delivery",
            "label": delivery,
            "type": "delivery",
            "status": "opportunity",
        },
        {"id": "process", "label": process, "type": "process", "status": "opportunity"},
        {
            "id": "effect",
            "label": claimed_effect,
            "type": "claimed_effect",
            "status": "review",
        },
        {
            "id": "brand",
            "label": case.metadata_json.get("brand", "Brand not supplied"),
            "type": "branding",
            "status": "opportunity",
        },
    ]
    edges = [
        {
            "id": f"e-{node['id']}",
            "source": node["id"],
            "target": "invention",
            "relation": "component of",
        }
        for node in nodes[1:]
    ]
    return {"nodes": nodes, "edges": edges}


def build_risks(case: Any, specific: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    text = _text(case)
    metadata = case.metadata_json or {}
    specific = specific or {}
    study_counts = specific.get("scientific_studies", {}).get("match_counts", {})
    botanical = (case.ingredients or ["the botanical ingredient"])[0]
    short_botanical = re.sub(r"\s+(?:extract|powder).*", "", botanical, flags=re.IGNORECASE)
    delivery = str(metadata.get("delivery_mechanism") or case.product_form or "the submitted delivery format")
    standardization = str(metadata.get("standardization") or "the submitted standardization")
    dose = str(metadata.get("dose") or metadata.get("quantitative_composition") or "the proposed dose")
    tk_score = (
        84 if case.classical_formulation else (68 if _contains(text, ["ayur", "traditional", "classical"]) else 38)
    )
    patent_score = (
        71
        if _contains(
            text,
            [
                "novel",
                "encapsulation",
                "delivery",
                "extract",
                "process",
                "standardized",
            ],
        )
        else 48
    )
    regulatory_score = 82 if _contains(text, ["treat", "cure", "disease", "therapeutic"]) else 61
    abs_score = 79 if (case.biological_sourcing or case.ingredients) else 34
    evidence_score = 66 if _contains(text, ["trial", "study", "clinical", "assay", "validated"]) else 31
    risks = [
        {
            "key": "traditional_knowledge",
            "title": "Traditional knowledge exposure",
            "score": tk_score,
            "level": "high" if tk_score >= 70 else "medium",
            "summary": f"High relevance for {short_botanical} and the submitted cognitive/traditional use; lower or unknown relevance for {delivery}.",
            "primary_finding": f"High for: {short_botanical} + the claimed use",
            "positive_signals": [f"Modern technical feature: {delivery}", f"Modern compositional feature: {standardization}"],
            "negative_signals": [f"Known-use exposure: {short_botanical} and the claimed use", "Verified exact TK source is not yet linked"],
            "missing_evidence": ["Exact classical formulation/passage and locator", "Authorized TKDL or classical-source verification"],
            "what_changes_score": ["Exact source linkage increases certainty", "A verified absence cannot be inferred from an incomplete TKDL search"],
        },
        {
            "key": "patent_opportunity",
            "title": "Patent screening",
            "score": patent_score,
            "level": "strong" if patent_score >= 65 else "uncertain",
            "summary": f"Strongest candidate: {delivery}. The known botanical use is the weakest candidate until claim-level prior-art comparison is complete.",
            "primary_finding": f"Strongest candidate: {delivery}",
            "positive_signals": ["Non-classical dosage form", "Phospholipid/delivery architecture", "Metered delivery and defined standardization"],
            "negative_signals": [f"Known {short_botanical} use", "Possible obviousness", "Prior-art search incomplete", "No complete claim-level comparison"],
            "missing_evidence": ["Feature-by-feature independent claim chart", "Patent-family/legal-status review", "Comparative technical-effect data"],
            "what_changes_score": ["A non-obvious measured technical effect strengthens the screen", "Close claim overlap or routine optimization weakens it"],
        },
        {
            "key": "regulatory",
            "title": "Regulatory Complexity",
            "score": regulatory_score,
            "level": "high" if regulatory_score >= 70 else "medium",
            "summary": "Classification remains unresolved among AYUSH, nutraceutical/supplement and other oral wellness pathways.",
            "primary_finding": "Status: unresolved",
            "positive_signals": ["Dosage form, composition and target markets are supplied"],
            "negative_signals": ["Final intended market claim and positioning control the route"],
            "missing_evidence": ["Signed claim/positioning matrix", "India and UK route determinations"],
            "what_changes_score": ["Final label wording and therapeutic positioning can change the applicable pathway"],
        },
        {
            "key": "abs",
            "title": "ABS review priority",
            "score": abs_score,
            "level": "required" if abs_score >= 60 else "screen",
            "summary": "Resource provenance is captured at intake; legal applicability and transaction-specific obligations still require review.",
            "display_value": "High" if abs_score >= 60 else "Screen",
            "score_is_probability": False,
            "primary_finding": "Provenance captured; applicability unresolved",
            "positive_signals": [case.biological_sourcing or "Botanical resource identity supplied"],
            "negative_signals": ["The screening score is not a probability of legal obligation"],
            "missing_evidence": ["Provider/access-date/party verification", "Qualified ABS applicability review"],
            "what_changes_score": ["Species, origin, transaction and applicant status determine the legal analysis"],
        },
        {
            "key": "evidence",
            "title": "Scientific evidence readiness",
            "score": evidence_score,
            "level": "moderate" if evidence_score >= 60 else "limited",
            "summary": f"Ingredient-level human evidence may exist, but evidence matching {dose}, {delivery}, the proposed population and the complete claim remains incomplete.",
            "display_value": f"{evidence_score}/100",
            "score_is_probability": False,
            "primary_finding": "Exact-formulation claim support is not established",
            "positive_signals": [f"Ingredient-level matched studies: {study_counts.get('ingredient_level', 0)}", f"Population-matched studies: {study_counts.get('population_matched', 0)}"],
            "negative_signals": [f"Dose-matched studies: {study_counts.get('dose_matched', 0)}", f"Formulation-matched studies: {study_counts.get('formulation_matched', 0)}", f"Direct exact-product studies: {study_counts.get('direct_product', 0)}"],
            "missing_evidence": ["Same/comparable standardized extract", "Dose-matched healthy-adult evidence", "Oral-mucosal delivery bridging evidence", "Claim-specific safety/tolerability"],
            "what_changes_score": ["Direct formulation trials raise readiness", "Indirect ingredient evidence alone cannot establish the exact product claim"],
        },
    ]
    support = {
        "traditional_knowledge": ["india-tkdl", "india-patents-act-1970"],
        "patent_opportunity": ["india-patents-act-1970", "wto-trips"],
        "regulatory": ["drugs-cosmetics-act-india", "fssai-ayurveda-aahara-2022"],
        "abs": ["india-biological-diversity-act-2002", "cbd-nagoya-protocol"],
        "evidence": ["us-fda-botanical-drug-guidance", "eu-traditional-herbal-medicinal-products"],
    }
    for risk in risks:
        risk["claim_type"] = "inference"
        risk["citations"] = [public_citation(source_id) for source_id in support[risk["key"]]]
    return risks


def build_knowledge_graph(case: Any, evidence_matches: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    ingredients = case.ingredients or ["Unspecified botanical resource"]
    nodes = [
        {
            "id": "user-invention",
            "label": case.title,
            "type": "invention",
            "risk": "current",
        },
        {
            "id": "tkdl",
            "label": "TKDL / classical-text search",
            "type": "traditional_text",
            "risk": "high",
        },
        {
            "id": "patents",
            "label": "Patent family search",
            "type": "patent",
            "risk": "review",
        },
        {
            "id": "papers",
            "label": "Scientific literature",
            "type": "paper",
            "risk": "review",
        },
    ]
    for index, ingredient in enumerate(ingredients[:6]):
        nodes.append(
            {
                "id": f"ingredient-{index}",
                "label": ingredient,
                "type": "ingredient",
                "risk": "review",
            }
        )
    edges = [
        {
            "id": "kg-1",
            "source": "tkdl",
            "target": "user-invention",
            "label": "possible known use",
        },
        {
            "id": "kg-2",
            "source": "patents",
            "target": "user-invention",
            "label": "novelty / inventive-step search",
        },
        {
            "id": "kg-3",
            "source": "papers",
            "target": "user-invention",
            "label": "evidence / disclosure",
        },
    ]
    edges.extend(
        {
            "id": f"kg-i-{index}",
            "source": f"ingredient-{index}",
            "target": "user-invention",
            "label": "included in",
        }
        for index, _ in enumerate(ingredients[:6])
    )
    document_citations = []
    for index, match in enumerate((evidence_matches or [])[:4]):
        node_id = f"document-{match['document_id']}-{match['chunk_index']}"
        nodes.append(
            {
                "id": node_id,
                "label": f"{match['filename']} · {match.get('page_number') or 'document'}",
                "type": "case_document",
                "risk": "evidence",
            }
        )
        edges.append(
            {
                "id": f"kg-d-{index}",
                "source": node_id,
                "target": "user-invention",
                "label": "retrieved case evidence",
            }
        )
        document_citations.append(evidence_citation(case.id, match))
    return {
        "nodes": nodes,
        "edges": edges,
        "findings": [
            "No definitive prior-art clearance has been performed in the currently available corpus.",
            "Search each ingredient, synonym, claimed use, process parameter and delivery feature in patent and non-patent literature.",
            "TKDL availability is restricted; route the final search through an authorized patent professional or examining authority.",
        ],
        "citations": [
            public_citation("india-tkdl"),
            public_citation("india-patents-act-1970"),
            *document_citations,
        ],
    }


def scientific_citation(record: dict[str, Any]) -> dict[str, Any]:
    identifier = record.get("pmid") or record.get("pmcid") or record.get("doi") or str(abs(hash(record.get("title", "study"))))
    return {
        "id": f"science-{identifier}",
        "title": record.get("title") or "Scientific study",
        "authority": record.get("journal") or "Scientific literature",
        "jurisdiction": "International scientific literature",
        "effective_date": record.get("publication_date") or "Not reported",
        "url": record.get("full_text_url") or record.get("url") or "https://pubmed.ncbi.nlm.nih.gov/",
        "support_status": record.get("evidence_role", "scientific_screening"),
        "excerpt": record.get("abstract_excerpt") or record.get("endpoints") or "Study record retrieved for appraisal.",
        "source_type": "scientific_literature",
        "locator": record.get("pmcid") or (f"PMID {record['pmid']}" if record.get("pmid") else record.get("locator")),
    }


def build_evidence(
    case: Any,
    evidence_matches: list[dict[str, Any]] | None = None,
    scientific_studies: dict[str, Any] | None = None,
) -> dict[str, Any]:
    text = _text(case)
    document_citations = [evidence_citation(case.id, match) for match in (evidence_matches or [])[:5]]
    scientific_studies = scientific_studies or {}
    records = [record for record in scientific_studies.get("records", []) if record.get("evidence_role") != "excluded_irrelevant"]
    counts = scientific_studies.get("match_counts", {})
    science_citations = [scientific_citation(record) for record in records[:8]]
    modern = (
        f"{len(records)} relevant scientific record(s) were retained after active-ingredient matching; {counts.get('direct_product', 0)} directly match the product, dose, population, endpoints and formulation."
        if records
        else f"{len(document_citations)} relevant passage(s) were retrieved from case documents. They remain user-supplied and require critical appraisal."
        if document_citations
        else "Some study language appears in the case description; individual studies still require appraisal."
        if _contains(text, ["study", "trial", "clinical"])
        else "No claim-specific modern scientific studies have been supplied."
    )
    return {
        "notice": "Traditional use is not equivalent to clinically established efficacy.",
        "traditional_use": {
            "status": "reported" if case.classical_formulation else "unverified",
            "summary": "The case identifies a classical formulation relationship."
            if case.classical_formulation
            else "A classical text, monograph or documented customary-use source has not been linked.",
            "confidence": 0.68 if case.classical_formulation else 0.25,
        },
        "modern_science": {
            "status": "ingredient_evidence_only" if records and not counts.get("direct_product") else "direct_evidence_identified" if counts.get("direct_product") else "documents_retrieved_unappraised" if document_citations else "limited",
            "summary": modern,
            "confidence": 0.52 if records or document_citations else 0.30,
        },
        "safety": {
            "status": "review_required",
            "summary": "Provide identity, purity, contaminants, interactions, contraindications, dose and adverse-event information.",
            "confidence": 0.22,
        },
        "confidence": {
            "label": "Low–Moderate",
            "score": 0.51 if document_citations else 0.31,
            "basis": "Ingredient-level human evidence may be available, but exact dose, standardization, population and oral-mucosal formulation matching are incomplete.",
        },
        "readiness_score": 31,
        "match_counts": counts,
        "evidence_layers": scientific_studies.get("evidence_layers", {}),
        "gaps": [
            "Claim-specific efficacy evidence",
            "Batch standardization and analytical methods",
            "Safety and interaction assessment",
            "Population, dose and duration justification",
        ],
        "citations": [
            *science_citations,
            *document_citations,
        ],
    }


def build_ip_strategy(case: Any) -> dict[str, Any]:
    text = _text(case)
    process_strength = (
        78 if _contains(text, ["process", "extract", "encapsulation", "standardized", "delivery"]) else 52
    )
    routes = [
        {
            "name": "Patent",
            "strength": process_strength,
            "relevance": "high",
            "protects": "Novel, inventive technical features such as process, composition parameters or delivery",
            "caution": "Known traditional ingredients/use and excluded subject matter can limit scope.",
        },
        {
            "name": "Trademark",
            "strength": 84,
            "relevance": "high",
            "protects": "Distinctive name, logo and source identity",
            "caution": "Clearance search and correct classes are required.",
        },
        {
            "name": "Trade Secret",
            "strength": 72,
            "relevance": "high",
            "protects": "Non-public process know-how, controls and supplier specifications",
            "caution": "Requires access controls, contracts and a documented secrecy programme.",
        },
        {
            "name": "Design",
            "strength": 48,
            "relevance": "medium",
            "protects": "Novel visual features of packaging or product configuration",
            "caution": "Does not protect function or underlying formulation.",
        },
        {
            "name": "Geographical Indication",
            "strength": 28,
            "relevance": "conditional",
            "protects": "Community-linked goods whose qualities or reputation are attributable to origin",
            "caution": "Usually not an individual-company right and needs a qualifying producer community.",
        },
    ]
    return {
        "routes": routes,
        "recommended_strategy": [
            "Run focused patent and non-patent prior-art searches before public disclosure.",
            "Draft claims around demonstrated technical differentiation, not the traditional use by itself.",
            "Clear and file the brand while keeping manufacturing know-how under controlled trade-secret procedures.",
            "Document resource provenance and inventor/contributor roles before filing.",
        ],
        "citations": [
            public_citation("india-patents-act-1970"),
            public_citation("wto-trips"),
            public_citation("wipo-gratk-2024"),
        ],
    }


def build_regulatory(case: Any, classification: dict[str, Any]) -> dict[str, Any]:
    source_citation = classification["citations"][0]
    steps = [
        {
            "order": 1,
            "name": "Product Classification",
            "status": "review",
            "detail": classification["label"],
            "deliverable": "Signed classification memo with intended-use and claims matrix",
        },
        {
            "order": 2,
            "name": "Applicable Regulation",
            "status": "pending",
            "detail": classification["pathway"],
            "deliverable": "Applicable Acts, Rules, standards and competent authority",
        },
        {
            "order": 3,
            "name": "Biological Resource / ABS Check",
            "status": "pending",
            "detail": "Map species, origin, supplier, access date, parties, research and commercialization facts.",
            "deliverable": "Resource provenance and ABS decision record",
        },
        {
            "order": 4,
            "name": "Required Evidence",
            "status": "pending",
            "detail": "Set claim-specific quality, safety and efficacy requirements.",
            "deliverable": "Evidence plan and gap register",
        },
        {
            "order": 5,
            "name": "Documentation",
            "status": "pending",
            "detail": "Compile specifications, labels, licences, agreements and technical dossier.",
            "deliverable": "Submission-ready controlled dossier",
        },
        {
            "order": 6,
            "name": "Market Entry",
            "status": "pending",
            "detail": "Complete authority interaction, approvals, vigilance and change control.",
            "deliverable": "Launch authorization and post-market plan",
        },
    ]
    return {
        "steps": steps,
        "abs_flag": bool(case.biological_sourcing or case.ingredients),
        "abs_summary": "A screening flag is present; it is not a legal conclusion. Confirm current Indian and provider-country requirements with resource-level facts.",
        "citations": [
            source_citation,
            public_citation("india-biological-diversity-act-2002"),
            public_citation("cbd-nagoya-protocol"),
        ],
    }


def build_jurisdictions(case: Any) -> list[dict[str, Any]]:
    requested = {market.lower() for market in (case.target_markets or [])}
    rows = [
        {
            "name": "India",
            "selected": not requested or "india" in requested,
            "patent": "TK and Section 3 exclusions require careful claim design",
            "tk": "High relevance; search TKDL/classical and patent sources",
            "regulation": "FSSAI or AYUSH/CDSCO pathway depends on classification and claims",
            "evidence": "Quality, safety and claim support are pathway-specific",
            "market_entry": "High",
            "citations": [
                "india-patents-act-1970",
                "fssai-ayurveda-aahara-2022",
                "drugs-cosmetics-act-india",
            ],
        },
        {
            "name": "European Union",
            "selected": "eu" in requested or "european union" in requested,
            "patent": "EPC/national analysis and prior art remain product-specific",
            "tk": "Traditional use may support registration but also affect novelty",
            "regulation": "Food, supplement, cosmetic or medicinal pathway varies by claims",
            "evidence": "Traditional registration still requires quality, safety and qualifying use",
            "market_entry": "High",
            "citations": ["eu-traditional-herbal-medicinal-products"],
        },
        {
            "name": "United Kingdom",
            "selected": "uk" in requested or "united kingdom" in requested or "great britain" in requested,
            "patent": "UKIPO patentability and prior-art analysis is distinct from regulatory market classification",
            "tk": "Traditional use can support a THR route while the same disclosure may affect patent novelty",
            "regulation": "MHRA herbal-medicine/THR or food-supplement route depends on intended purpose and claims",
            "evidence": "Exact product evidence is distinct from traditional-use eligibility and authorised food health claims",
            "market_entry": "High",
            "citations": ["uk-mhra-traditional-herbal-registration", "uk-food-health-claims"],
        },
        {
            "name": "United States",
            "selected": "us" in requested or "usa" in requested or "united states" in requested,
            "patent": "USPTO search and eligibility/novelty analysis required",
            "tk": "Global public disclosures can be prior art",
            "regulation": "Dietary supplement, cosmetic or drug pathway depends on intended use",
            "evidence": "Drug claims require the relevant FDA development route",
            "market_entry": "High",
            "citations": ["us-fda-botanical-drug-guidance"],
        },
        {
            "name": "International baseline",
            "selected": True,
            "patent": "Rights remain territorial despite treaty baselines",
            "tk": "Genetic-resource/TK disclosure landscape is evolving",
            "regulation": "No single international market authorization",
            "evidence": "Local authority standards control",
            "market_entry": "Variable",
            "citations": ["wipo-gratk-2024", "wto-trips", "cbd-nagoya-protocol"],
        },
    ]
    for row in rows:
        row["citations"] = [public_citation(source_id) for source_id in row["citations"]]
    return rows


def build_challenges(
    case: Any, evidence_matches: list[dict[str, Any]] | None = None
) -> dict[str, list[dict[str, Any]]]:
    challenges = {
        "patent_examiner": [
            {
                "severity": "high",
                "objection": "The claimed ingredients or use may already be disclosed in traditional-knowledge or patent sources.",
                "missing": "Element-by-element novelty chart and dated prior-art search",
                "next_step": "Search synonyms, botanical names, formulations, uses, process parameters and patent families.",
            },
            {
                "severity": "high",
                "objection": "The inventive contribution is not yet distinguished from a known admixture or expected optimization.",
                "missing": "Comparative technical data showing an unexpected effect",
                "next_step": "Define the closest prior art and generate side-by-side evidence for the technical advantage.",
            },
        ],
        "regulatory_reviewer": [
            {
                "severity": "high",
                "objection": "Product classification is provisional because final formulation, dose, presentation and claims are incomplete.",
                "missing": "Final claims matrix, label concept and quantitative composition",
                "next_step": "Freeze intended use and classify before choosing the dossier route.",
            },
            {
                "severity": "medium",
                "objection": "Quality controls and batch consistency are not documented.",
                "missing": "Specifications, analytical methods and stability protocol",
                "next_step": "Build a quality target product profile and method-validation plan.",
            },
        ],
        "abs_reviewer": [
            {
                "severity": "high",
                "objection": "Biological-resource provenance and access facts are insufficient for an ABS decision.",
                "missing": "Species, source location, provider, dates, party nationality/control and intended utilization",
                "next_step": "Complete a resource-level provenance ledger and obtain current specialist advice.",
            },
        ],
        "scientific_evidence_reviewer": [
            {
                "severity": "high",
                "objection": "Traditional-use evidence does not by itself establish clinical efficacy for the proposed claim.",
                "missing": "Claim-specific modern evidence and a transparent evidence appraisal",
                "next_step": "Create a PICO-style question, systematic search and evidence-to-claim matrix.",
            },
            {
                "severity": "medium",
                "objection": "Safety conclusions cannot be reached from the present description.",
                "missing": "Dose, contraindications, interactions, contaminants and adverse-event data",
                "next_step": "Commission a qualified toxicology and clinical-safety review.",
            },
        ],
    }
    official_support = {
        "patent_examiner": ["india-patents-act-1970", "india-tkdl"],
        "regulatory_reviewer": ["drugs-cosmetics-act-india", "fssai-ayurveda-aahara-2022"],
        "abs_reviewer": ["india-biological-diversity-act-2002", "cbd-nagoya-protocol"],
        "scientific_evidence_reviewer": [
            "us-fda-botanical-drug-guidance",
            "eu-traditional-herbal-medicinal-products",
        ],
    }
    document_support = [evidence_citation(case.id, match) for match in (evidence_matches or [])[:2]]
    for reviewer, findings in challenges.items():
        citations = [public_citation(source_id) for source_id in official_support[reviewer]]
        for finding in findings:
            finding["citations"] = [*citations, *document_support]
    return challenges


def build_decision_brief(case: Any, specific: dict[str, Any], classification: dict[str, Any]) -> dict[str, Any]:
    metadata = case.metadata_json or {}
    ingredient = (case.ingredients or ["Botanical active"])[0]
    delivery = str(metadata.get("delivery_mechanism") or case.product_form or "Submitted delivery format")
    dose = str(metadata.get("dose") or "Proposed dose")
    standardization = str(metadata.get("standardization") or "Standardization not supplied")
    studies = specific.get("scientific_studies", {}).get("match_counts", {})
    return {
        "strongest_protectable_element": delivery,
        "highest_tk_risk": f"{ingredient} + the submitted cognitive/traditional-use claim",
        "largest_scientific_gap": f"No direct exact-product study identified; dose-matched {studies.get('dose_matched', 0)}, formulation-matched {studies.get('formulation_matched', 0)}.",
        "regulatory_status": classification["label"],
        "abs_status": "Resource provenance captured; legal applicability review still required",
        "most_important_next_step": "Complete a feature-level patent-family and independent-claim comparison for the botanical + oral-spray + phospholipid architecture.",
        "known": [
            f"{ingredient} is the submitted active botanical",
            f"Standardization supplied: {standardization}",
            f"Dose supplied: {dose}",
            f"Delivery architecture supplied: {delivery}",
            f"Target markets supplied: {' + '.join(case.target_markets or ['not specified'])}",
        ],
        "not_established": [
            "Exact patent novelty or freedom to operate",
            "Efficacy of the exact formulation and dose",
            "Final product classification",
            "Verified exact traditional-knowledge source linkage",
            "Final ABS obligation",
        ],
    }


def analyze_case(
    case: Any,
    evidence_matches: list[dict[str, Any]] | None = None,
    evidence_overview: dict[str, int] | None = None,
) -> dict[str, Any]:
    evidence_matches = evidence_matches or []
    evidence_overview = evidence_overview or {
        "document_count": 0,
        "indexed_document_count": 0,
        "chunk_count": 0,
    }
    classification = classify_product(case)
    ip_strategy = build_ip_strategy(case)
    challenges = build_challenges(case, evidence_matches)
    external_research = run_external_research(case)
    specific = build_case_specific_analysis(case, evidence_matches, external_research)
    risks = build_risks(case, specific)
    claim_graph = build_claim_evidence_graph(classification, risks, challenges)
    design_around = build_specific_design_around(
        case,
        specific,
        ip_strategy["recommended_strategy"],
        [
            public_citation("india-patents-act-1970"),
            public_citation("india-tkdl"),
            public_citation("india-biological-diversity-act-2002"),
        ],
    )
    knowledge_graph = build_knowledge_graph(case, evidence_matches)
    for index, patent in enumerate(specific["patent_landscape"].get("records", [])[:4]):
        node_id = f"live-patent-{index}"
        knowledge_graph["nodes"].append(
            {
                "id": node_id,
                "label": f"{patent.get('publication_number')}: {patent.get('title')}",
                "type": "patent",
                "risk": "live_evidence",
            }
        )
        knowledge_graph["edges"].append(
            {"id": f"kg-p-{index}", "source": node_id, "target": "user-invention", "label": "retrieved claim comparison"}
        )
    for index, record in enumerate(specific["traditional_knowledge"]["records"][:4]):
        node_id = f"exact-tk-{index}"
        knowledge_graph["nodes"].append(
            {"id": node_id, "label": f"{record['source_title']} · {record.get('locator') or 'passage'}", "type": "traditional_text", "risk": "evidence"}
        )
        knowledge_graph["edges"].append(
            {"id": f"kg-tk-{index}", "source": node_id, "target": "user-invention", "label": "exact retrieved passage"}
        )
    patent_status = specific["patent_landscape"].get("status", "not run")
    completeness = specific["input_completeness"]
    scientific_evidence = build_evidence(case, evidence_matches, specific["scientific_studies"])
    scientific_evidence["study_matrix"] = specific["scientific_studies"]
    scientific_evidence["traditional_knowledge_records"] = specific["traditional_knowledge"]["records"]
    result = {
        "case": {"id": case.id, "title": case.title, "status": "analyzed"},
        "executive_summary": (
            f"{completeness['supplied_count']}/{completeness['required_count']} intake fields completed. "
            f"External verification remains incomplete for prior art, regulatory classification and scientific evidence; patent research status is {patent_status.replace('_', ' ')}. "
            "Submitted quantities, extract, delivery and process facts are preserved, and missing conclusions remain explicit."
        ),
        "classification": classification,
        "decision_brief": build_decision_brief(case, specific, classification),
        "genome": build_genome(case),
        "risk_cards": risks,
        "knowledge_graph": knowledge_graph,
        "scientific_evidence": scientific_evidence,
        "ip_strategy": ip_strategy,
        "regulatory_abs": build_regulatory(case, classification),
        "jurisdictions": build_jurisdictions(case),
        "challenges": challenges,
        "claim_evidence_graph": claim_graph,
        "design_around": design_around,
        "case_specific_analysis": specific,
        "evidence_retrieval": {
            **evidence_overview,
            "retrieved_passage_count": len(evidence_matches),
            "citations": [evidence_citation(case.id, match) for match in evidence_matches],
            **retrieval_status(evidence_matches),
            "appraisal_status": "human appraisal required",
        },
        "next_actions": [
            "Finalize exact claim wording and intended market positioning.",
            "Complete the botanical + oral-spray + phospholipid-delivery prior-art and independent-claim search.",
            "Verify biological-resource provenance and ABS applicability.",
            "Build a claim-to-evidence matrix for each proposed cognitive outcome.",
            "Compare India and UK regulatory pathways before final label and marketing claims.",
        ],
        "confidence": {
            "score": round(min(0.82, 0.35 + completeness["score"] / 250 + (0.08 if evidence_matches else 0)), 2),
            "label": "Case-specific screening confidence",
            "basis": (
                "Submitted technical facts, curated primary sources and retrieved case-document passages; comprehensive clearance and human appraisal remain required."
                if evidence_matches
                else "Submitted technical facts and curated primary sources; no uploaded-document appraisal is available."
            ),
        },
        "corpus_version": settings.corpus_version,
        "generated_by": "IP-SAKTI evidence assurance engine with feature-level patent comparison, study extraction, hybrid retrieval, reranking and claim provenance",
        "warnings": [
            DISCLAIMER,
            "Legal and regulatory requirements can change; citations show the source date or status available in the registry.",
        ],
    }
    return result


def classify_question_intent(question: str) -> str:
    normalized = question.lower()
    if _contains(normalized, ["legally market", "lawful claim", "regulatory", "classification", "label", "license", "licence"]):
        return "REGULATORY"
    if _contains(normalized, ["human evidence", "clinical evidence", "scientific evidence", "efficacy", "study", "studies", "trial", "dose", "formulation", "memory", "attention", "cognitive", "safety", "tolerability"]):
        return "SCIENTIFIC_EVIDENCE"
    if _contains(normalized, ["patent", "novel", "inventive", "prior art", "claim overlap"]):
        return "PATENT"
    if _contains(normalized, ["traditional knowledge", "tkdl", "classical", "prior use"]):
        return "TRADITIONAL_KNOWLEDGE"
    if _contains(normalized, ["abs", "biological resource", "biodiversity", "provenance"]):
        return "ABS"
    return "GENERAL"


def answer_scientific_question(case: Any, question: str, analysis: dict[str, Any]) -> dict[str, Any]:
    studies = analysis.get("case_specific_analysis", {}).get("scientific_studies", {})
    counts = studies.get("match_counts", {})
    records = [record for record in studies.get("records", []) if record.get("evidence_role") != "excluded_irrelevant"]
    metadata = case.metadata_json or {}
    ingredient = (case.ingredients or ["the submitted botanical"])[0]
    dose = str(metadata.get("dose") or metadata.get("quantitative_composition") or "the submitted dose").rstrip(". ")
    formulation = str(metadata.get("delivery_mechanism") or case.product_form or "the submitted formulation")
    claim = str(metadata.get("proposed_claim") or case.intended_use or question)
    direct = counts.get("direct_product", 0)
    ingredient_level = counts.get("ingredient_level", 0)
    conclusion = "NOT ESTABLISHED FOR THE EXACT PRODUCT"
    ingredient_status = "AVAILABLE" if ingredient_level else "NOT IDENTIFIED"
    answer = (
        f"Current conclusion: {conclusion}.\n\n"
        f"The retrieved literature provides {ingredient_status.lower()} ingredient-level human evidence for {ingredient}, "
        f"but it does not establish the complete claim — ‘{claim}’ — for {dose} delivered as {formulation}.\n\n"
        "Claim-level assessment\n"
        f"• Ingredient-level human evidence: {ingredient_level} matched record(s).\n"
        f"• Healthy-population match: {counts.get('population_matched', 0)} record(s).\n"
        f"• Endpoint match: {counts.get('endpoint_matched', 0)} record(s); memory, attention and broad cognitive performance must each be supported.\n"
        f"• Dose match: {counts.get('dose_matched', 0)} record(s); materially different exposure is indirect evidence.\n"
        f"• Formulation match: {counts.get('formulation_matched', 0)} record(s); spray/phospholipid benefits cannot be assumed from capsules or tablets.\n"
        f"• Direct exact-product evidence: {direct} record(s).\n\n"
        "Evidence status: PARTIALLY SUPPORTED AT INGREDIENT LEVEL / FORMULATION-SPECIFIC EVIDENCE MISSING. "
        "The claim is not yet claim-ready for this exact product. Traditional use is assessed separately and is not clinical proof."
    )
    citations = [scientific_citation(record) for record in records[:8]]
    return {
        "answer": answer,
        "claim_type": "interpretation" if citations else "unsupported",
        "confidence": 0.52 if citations else 0.24,
        "confidence_label": "Low–Moderate" if citations else "Low",
        "confidence_basis": "Ingredient-level human evidence may exist, but exact dose, population, endpoint and formulation matching are incomplete.",
        "intent": "SCIENTIFIC_EVIDENCE",
        "evidence_summary": {
            "direct_evidence": direct,
            "ingredient_level_human_evidence": ingredient_level,
            "dose_matched_evidence": counts.get("dose_matched", 0),
            "formulation_matched_evidence": counts.get("formulation_matched", 0),
            "population_matched_evidence": counts.get("population_matched", 0),
            "endpoint_matched_evidence": counts.get("endpoint_matched", 0),
        },
        "methodology": [
            "Scientific-evidence intent selected; legal and regulatory sources excluded.",
            "Clinical retrieval requires the active botanical and ranks ingredient, population, endpoint, quality, dose and formulation matches.",
            "PMC full text is appraised when available; abstract-only records remain screening leads.",
        ],
        "citations": citations,
        "requires_human_review": True,
        "limitations": [
            DISCLAIMER,
            "This is a claim-level evidence screen, not a systematic review, medical recommendation or marketing authorization.",
        ],
    }


def answer_question(
    case: Any,
    question: str,
    evidence_matches: list[dict[str, Any]] | None = None,
    analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    intent = classify_question_intent(question)
    if intent == "SCIENTIFIC_EVIDENCE" and analysis:
        return answer_scientific_question(case, question, analysis)
    normalized = re.sub(r"[^a-z0-9\s-]", " ", question.lower())
    scored: list[tuple[int, dict[str, Any]]] = []
    tokens = {token for token in normalized.split() if len(token) > 2}
    for source in SOURCES:
        haystack = " ".join([source["title"], source["summary"], *source["keywords"]]).lower()
        score = sum(1 for token in tokens if token in haystack)
        if source["jurisdiction"].lower() in normalized:
            score += 2
        scored.append((score, source))
    matches = [source for score, source in sorted(scored, key=lambda item: item[0], reverse=True) if score > 0][:3]
    evidence_matches = evidence_matches or []
    if not matches and not evidence_matches:
        return {
            "answer": "The curated source registry does not contain enough directly relevant material to answer this reliably. Add the relevant document or request expert review rather than treating a generated response as authority.",
            "claim_type": "unsupported",
            "confidence": 0.12,
            "confidence_label": "Low",
            "confidence_basis": "No sufficiently relevant primary or case-document source was retrieved.",
            "intent": intent,
            "evidence_summary": None,
            "methodology": ["Hybrid retrieval with safe abstention."],
            "citations": [],
            "requires_human_review": True,
            "limitations": [
                DISCLAIMER,
                "Safe abstention: no sufficiently relevant primary source was retrieved.",
            ],
        }
    official_summary = " ".join(source["summary"] for source in matches)
    evidence_summary = " ".join(
        "The supplied document "
        f"{match['filename']} states: {' '.join(match['content'].split())[:360]}"
        for match in evidence_matches[:3]
    )
    combined = " ".join(value for value in [official_summary, evidence_summary] if value)
    answer = f"For {case.title}: {combined} This is a source-grounded screening interpretation, not a final legal conclusion."
    limitations = [
        DISCLAIMER,
        "The answer covers only the retrieved official and case-document sources, not a comprehensive search or authenticity appraisal.",
    ]
    return {
        "answer": answer,
        "claim_type": "interpretation",
        "confidence": min(0.82, 0.50 + 0.06 * len(matches) + 0.04 * len(evidence_matches)),
        "confidence_label": "Moderate",
        "confidence_basis": "Relevant primary and case-document sources were retrieved, but human interpretation remains required.",
        "intent": intent,
        "evidence_summary": None,
        "methodology": ["Hybrid lexical and neural retrieval with reranking."],
        "citations": [
            *[public_citation(source["id"]) for source in matches],
            *[evidence_citation(case.id, match) for match in evidence_matches[:3]],
        ],
        "requires_human_review": True,
        "limitations": limitations,
    }


def list_sources(jurisdiction: str | None = None) -> list[dict[str, Any]]:
    sources = SOURCES
    if jurisdiction:
        sources = [source for source in sources if source["jurisdiction"].lower() == jurisdiction.lower()]
    return [public_citation(source["id"]) for source in sources]
