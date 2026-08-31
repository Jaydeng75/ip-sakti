import json
import re
from pathlib import Path
from typing import Any

from config import settings
from services.evidence import evidence_citation

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
    }


def _text(case: Any) -> str:
    fields = [
        case.title,
        case.description,
        case.product_form or "",
        case.intended_use or "",
        case.biological_sourcing or "",
        " ".join(case.ingredients or []),
    ]
    return " ".join(fields).lower()


def _contains(text: str, words: list[str]) -> bool:
    return any(word in text for word in words)


def classify_product(case: Any) -> dict[str, Any]:
    text = _text(case)
    therapeutic = _contains(text, ["treat", "cure", "prevent", "therapy", "disease", "pain", "diabetes"])
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
        "citations": [public_citation(item) for item in citation_ids],
    }


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


def build_risks(case: Any) -> list[dict[str, Any]]:
    text = _text(case)
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
            "title": "Traditional Knowledge Risk",
            "score": tk_score,
            "level": "high" if tk_score >= 70 else "medium",
            "summary": "A documented classical or customary use may be prior art and can narrow patentable subject matter.",
        },
        {
            "key": "patent_opportunity",
            "title": "Patent Opportunity",
            "score": patent_score,
            "level": "strong" if patent_score >= 65 else "uncertain",
            "summary": "Novel delivery, standardization or process features may be more defensible than the known ingredients or use.",
        },
        {
            "key": "regulatory",
            "title": "Regulatory Complexity",
            "score": regulatory_score,
            "level": "high" if regulatory_score >= 70 else "medium",
            "summary": "Classification and claims must be fixed before the evidence and licensing route can be confirmed.",
        },
        {
            "key": "abs",
            "title": "ABS Review Required",
            "score": abs_score,
            "level": "required" if abs_score >= 60 else "screen",
            "summary": "Trace resource identity, source, provider, access date and parties before deciding ABS obligations.",
        },
        {
            "key": "evidence",
            "title": "Scientific Evidence Strength",
            "score": evidence_score,
            "level": "moderate" if evidence_score >= 60 else "limited",
            "summary": "Traditional use is not equivalent to clinically established efficacy; claim-specific modern evidence is needed.",
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


def build_evidence(case: Any, evidence_matches: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    text = _text(case)
    document_citations = [evidence_citation(case.id, match) for match in (evidence_matches or [])[:5]]
    modern = (
        f"{len(document_citations)} relevant passage(s) were retrieved from case documents. They remain user-supplied and require critical appraisal."
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
            "status": "documents_retrieved_unappraised" if document_citations else "limited",
            "summary": modern,
            "confidence": 0.52 if document_citations else 0.30,
        },
        "safety": {
            "status": "review_required",
            "summary": "Provide identity, purity, contaminants, interactions, contraindications, dose and adverse-event information.",
            "confidence": 0.22,
        },
        "confidence": {
            "label": "Moderate retrieval confidence; appraisal pending" if document_citations else "Low pending document review",
            "score": 0.51 if document_citations else 0.31,
            "basis": (
                "Relevant case-document passages were retrieved with page/chunk lineage, but authenticity and study quality remain unverified."
                if document_citations
                else "No uploaded evidence has been critically appraised in this run."
            ),
        },
        "gaps": [
            "Claim-specific efficacy evidence",
            "Batch standardization and analytical methods",
            "Safety and interaction assessment",
            "Population, dose and duration justification",
        ],
        "citations": [
            public_citation("us-fda-botanical-drug-guidance"),
            public_citation("eu-traditional-herbal-medicinal-products"),
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
    result = {
        "case": {"id": case.id, "title": case.title, "status": "analyzed"},
        "executive_summary": "This is a screening analysis. The strongest defensible value is likely to sit in verified technical differentiation, controlled know-how and brand assets; traditional-knowledge, classification, evidence and biological-resource questions need documented review.",
        "classification": classification,
        "genome": build_genome(case),
        "risk_cards": build_risks(case),
        "knowledge_graph": build_knowledge_graph(case, evidence_matches),
        "scientific_evidence": build_evidence(case, evidence_matches),
        "ip_strategy": build_ip_strategy(case),
        "regulatory_abs": build_regulatory(case, classification),
        "jurisdictions": build_jurisdictions(case),
        "challenges": build_challenges(case, evidence_matches),
        "evidence_retrieval": {
            **evidence_overview,
            "retrieved_passage_count": len(evidence_matches),
            "citations": [evidence_citation(case.id, match) for match in evidence_matches],
            "method": "hybrid lexical and deterministic vector retrieval",
            "appraisal_status": "human appraisal required",
        },
        "next_actions": [
            "Freeze the quantitative formulation, intended use, dose, delivery and claims.",
            "Complete patent, non-patent and traditional-knowledge searches with a qualified professional.",
            "Create a resource provenance and ABS screening record.",
            "Build a claim-to-evidence matrix and quality/safety gap plan.",
        ],
        "confidence": {
            "score": 0.64 if evidence_matches else 0.58,
            "label": "Moderate grounded screening confidence",
            "basis": (
                "Curated primary sources plus retrieved case-document passages; comprehensive clearance and human appraisal remain required."
                if evidence_matches
                else "Curated primary-source registry; no comprehensive database clearance or document appraisal."
            ),
        },
        "corpus_version": settings.corpus_version,
        "generated_by": "IP-SAKTI hybrid evidence retrieval and grounded screening engine",
        "warnings": [
            DISCLAIMER,
            "Legal and regulatory requirements can change; citations show the source date or status available in the registry.",
        ],
    }
    return result


def answer_question(
    case: Any, question: str, evidence_matches: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
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
