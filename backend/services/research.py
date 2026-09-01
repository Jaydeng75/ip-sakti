import logging
import re
from functools import lru_cache
from typing import Any
from urllib.parse import quote_plus
from xml.etree import ElementTree

import httpx

from config import settings

logger = logging.getLogger("ip-sakti.research")
EPO_BASE = "https://ops.epo.org/3.2/rest-services"
EPO_TOKEN_URL = "https://ops.epo.org/3.2/auth/accesstoken"
NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
GOOGLE_PATENTS_RESEARCH_TABLE = "patents-public-data.google_patents_research.publications"
GOOGLE_PATENTS_PUBLICATIONS_TABLE = "patents-public-data.patents.publications"
WORD_RE = re.compile(r"[A-Za-z][A-Za-z-]{2,}")

GOOGLE_PATENTS_SQL = f"""
WITH candidates AS (
  SELECT
    publication_number,
    title,
    url,
    country,
    publication_description,
    (
      SELECT COUNT(*)
      FROM UNNEST(top_terms) AS top_term
      CROSS JOIN UNNEST(@terms) AS query_term
      WHERE STRPOS(LOWER(top_term), query_term) > 0
    ) AS term_hits
  FROM `{GOOGLE_PATENTS_RESEARCH_TABLE}`
  WHERE EXISTS (
    SELECT 1
    FROM UNNEST(top_terms) AS top_term
    CROSS JOIN UNNEST(@terms) AS query_term
    WHERE STRPOS(LOWER(top_term), query_term) > 0
  )
  ORDER BY term_hits DESC, publication_number DESC
  LIMIT @candidate_limit
)
SELECT
  candidate.publication_number,
  candidate.title,
  candidate.url,
  candidate.country,
  candidate.publication_description,
  candidate.term_hits,
  publication.family_id
FROM candidates AS candidate
LEFT JOIN `{GOOGLE_PATENTS_PUBLICATIONS_TABLE}` AS publication
  USING (publication_number)
ORDER BY candidate.term_hits DESC, candidate.publication_number DESC
LIMIT @result_limit
"""


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _element_text(element: ElementTree.Element | None) -> str:
    return _clean(" ".join(element.itertext())) if element is not None else ""


def _latin_name(ingredient: str) -> str:
    parenthesized = re.search(r"\(([A-Z][a-z]+\s+[a-z][a-z-]+)\)", ingredient)
    if parenthesized:
        return parenthesized.group(1)
    direct = re.search(r"\b([A-Z][a-z]+\s+[a-z][a-z-]+)\b", ingredient)
    return direct.group(1) if direct else ingredient.split(",", 1)[0].strip()


def build_research_query(case: Any) -> dict[str, str]:
    ingredients = [_latin_name(item) for item in (case.ingredients or [])[:3]]
    metadata = case.metadata_json or {}
    technical = [
        metadata.get("delivery_mechanism") or case.product_form or "",
        metadata.get("release_profile", ""),
        metadata.get("extraction_ratio", ""),
        metadata.get("standardization", ""),
    ]
    technical_terms = [term for term in technical if term]
    patent_terms = [*ingredients[:2], *technical_terms[:2]] or [case.title]
    patent_cql = " and ".join(f'ta all "{_clean(term)[:100]}"' for term in patent_terms)
    effect_terms = [
        term
        for term in WORD_RE.findall(case.intended_use or "")
        if term.lower() not in {"and", "the", "for", "daily", "support", "management", "without", "claim"}
    ]
    effect = " ".join(effect_terms[:3])
    pubmed_parts = []
    if ingredients:
        pubmed_parts.append("(" + " OR ".join(f'\"{item}\"[Title/Abstract]' for item in ingredients[:2]) + ")")
    if effect:
        pubmed_parts.append(
            "(" + " OR ".join(f'\"{term}\"[Title/Abstract]' for term in effect_terms[:3]) + ")"
        )
    pubmed_query = " AND ".join(pubmed_parts) if pubmed_parts else case.title
    return {
        "patent_cql": patent_cql,
        "patent_display": " + ".join(patent_terms),
        "pubmed": pubmed_query,
    }


def _bigquery_terms(case: Any) -> tuple[str, ...]:
    ingredients = [_clean(_latin_name(item)).lower() for item in (case.ingredients or [])[:3]]
    metadata = case.metadata_json or {}
    technical_text = " ".join(
        str(value)
        for value in [
            case.product_form or "",
            metadata.get("delivery_mechanism", ""),
            metadata.get("standardization", ""),
            metadata.get("release_profile", ""),
            metadata.get("extraction_ratio", ""),
        ]
        if value
    )
    technical_tokens = [
        token.lower()
        for token in WORD_RE.findall(technical_text)
        if len(token) >= 5 and token.lower() not in {"extract", "tablet", "capsule", "release"}
    ]
    ordered = [*ingredients, *technical_tokens]
    return tuple(dict.fromkeys(term for term in ordered if len(term) >= 4))[:8]


@lru_cache(maxsize=32)
def _query_google_patents(
    project: str,
    location: str,
    terms: tuple[str, ...],
    result_limit: int,
    maximum_bytes_billed: int,
) -> tuple[tuple[dict[str, Any], ...], str | None, int | None]:
    from google.cloud import bigquery

    client = bigquery.Client(project=project, location=location)
    job_config = bigquery.QueryJobConfig(
        maximum_bytes_billed=maximum_bytes_billed,
        query_parameters=[
            bigquery.ArrayQueryParameter("terms", "STRING", list(terms)),
            bigquery.ScalarQueryParameter("candidate_limit", "INT64", max(result_limit * 5, 25)),
            bigquery.ScalarQueryParameter("result_limit", "INT64", result_limit),
        ],
    )
    query_job = client.query(GOOGLE_PATENTS_SQL, job_config=job_config, location=location)
    try:
        rows = tuple(dict(row.items()) for row in query_job.result(timeout=settings.external_research_timeout_seconds))
    except Exception:
        query_job.cancel()
        raise
    modified = None
    try:
        table = client.get_table(GOOGLE_PATENTS_RESEARCH_TABLE)
        modified = table.modified.isoformat() if table.modified else None
    except Exception as exc:
        logger.info("Google Patents table metadata unavailable error=%s", type(exc).__name__)
    return rows, modified, query_job.total_bytes_billed


def search_google_patents_bigquery(case: Any, query: dict[str, str]) -> dict[str, Any]:
    search_url = f"https://patents.google.com/?q={quote_plus(query['patent_display'])}"
    base = {
        "provider": "Google Patents Public Datasets on BigQuery",
        "query": query["patent_display"],
        "records": [],
        "family_count": 0,
        "search_url": search_url,
        "coverage_note": "Worldwide discovery metadata and simple-family identifiers; claim text is not retrieved by the bounded default query.",
    }
    if not settings.google_cloud_project:
        return {
            **base,
            "status": "credential_required",
            "limitation": "Set IPSAKTI_GOOGLE_CLOUD_PROJECT and provide Google Application Default Credentials.",
        }
    terms = _bigquery_terms(case)
    if not terms:
        return {
            **base,
            "status": "insufficient_query",
            "limitation": "Add botanical identities or technical parameters before running the patent search.",
        }
    try:
        rows, dataset_modified_at, bytes_billed = _query_google_patents(
            settings.google_cloud_project,
            settings.bigquery_location,
            terms,
            settings.external_research_max_results,
            settings.bigquery_maximum_bytes_billed,
        )
        records = [
            {
                "publication_number": row.get("publication_number") or "Unknown publication",
                "docdb": row.get("publication_number"),
                "family_id": row.get("family_id"),
                "title": row.get("title") or row.get("publication_number") or "Untitled patent",
                "claims": [],
                "url": row.get("url") or f"https://patents.google.com/patent/{str(row.get('publication_number') or '').replace('-', '')}",
                "source": "Google Patents BigQuery public dataset",
                "country": row.get("country"),
                "publication_description": row.get("publication_description"),
                "term_hits": int(row.get("term_hits") or 0),
            }
            for row in rows
        ]
        return {
            **base,
            "status": "family_live_claims_not_retrieved" if records else "no_results",
            "records": records,
            "family_count": len({item["family_id"] or item["publication_number"] for item in records}),
            "dataset_modified_at": dataset_modified_at,
            "bytes_billed": bytes_billed,
            "limitation": (
                "This bounded query retrieves candidate publications and simple-family identifiers without scanning the costly full-claim column. "
                "Open each candidate to verify current family members, legal status and claim text; no claim-level conclusion is asserted."
            ),
        }
    except Exception as exc:
        logger.warning("Google Patents BigQuery research unavailable error=%s", type(exc).__name__)
        return {
            **base,
            "status": "unavailable",
            "limitation": (
                "The BigQuery request failed or exceeded its configured billing cap; no family or claim-level result is asserted."
            ),
        }


@lru_cache(maxsize=8)
def _epo_token(consumer_key: str, consumer_secret: str) -> str:
    with httpx.Client(timeout=settings.external_research_timeout_seconds) as client:
        response = client.post(
            EPO_TOKEN_URL,
            auth=(consumer_key, consumer_secret),
            data={"grant_type": "client_credentials"},
        )
        response.raise_for_status()
        return str(response.json()["access_token"])


def _epo_claims(client: httpx.Client, headers: dict[str, str], docdb: str) -> list[dict[str, str]]:
    response = client.get(
        f"{EPO_BASE}/published-data/publication/docdb/{docdb}/claims",
        headers=headers,
    )
    if response.status_code == 404:
        return []
    response.raise_for_status()
    root = ElementTree.fromstring(response.content)
    claims = []
    for index, element in enumerate(root.findall(".//{*}claim")[:5], start=1):
        text = _element_text(element)
        if text:
            claims.append({"claim": str(element.attrib.get("num") or index), "text": text[:1_500]})
    return claims


def search_epo_patents(case: Any, query: dict[str, str]) -> dict[str, Any]:
    search_url = f"https://worldwide.espacenet.com/patent/search?q={quote_plus(query['patent_display'])}"
    if not settings.epo_ops_consumer_key or not settings.epo_ops_consumer_secret:
        return {
            "status": "credential_required",
            "provider": "European Patent Office Open Patent Services",
            "query": query["patent_display"],
            "records": [],
            "family_count": 0,
            "search_url": search_url,
            "limitation": "EPO OPS credentials are not configured; no patent-family or claim-level result is asserted.",
        }
    try:
        token = _epo_token(settings.epo_ops_consumer_key, settings.epo_ops_consumer_secret)
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/xml",
            "Range": f"1-{min(settings.external_research_max_results, 10)}",
        }
        with httpx.Client(timeout=settings.external_research_timeout_seconds) as client:
            response = client.get(
                f"{EPO_BASE}/published-data/search/biblio",
                params={"q": query["patent_cql"]},
                headers=headers,
            )
            response.raise_for_status()
            root = ElementTree.fromstring(response.content)
            records = []
            for document in root.findall(".//{*}exchange-document")[: settings.external_research_max_results]:
                country = document.attrib.get("country", "")
                number = document.attrib.get("doc-number", "")
                kind = document.attrib.get("kind", "")
                docdb = ".".join(item for item in [country, number, kind] if item)
                title = _element_text(document.find(".//{*}invention-title")) or docdb
                family_id = document.attrib.get("family-id")
                claims = _epo_claims(client, headers, docdb) if docdb else []
                records.append(
                    {
                        "publication_number": "".join([country, number, kind]),
                        "docdb": docdb,
                        "family_id": family_id,
                        "title": title,
                        "claims": claims,
                        "url": f"https://worldwide.espacenet.com/patent/search/family/{family_id}" if family_id else search_url,
                        "source": "EPO OPS live result",
                    }
                )
        return {
            "status": "live",
            "provider": "European Patent Office Open Patent Services",
            "query": query["patent_display"],
            "records": records,
            "family_count": len({item["family_id"] or item["docdb"] for item in records}),
            "search_url": search_url,
            "limitation": "Keyword and claim-overlap screening is not a legal novelty or freedom-to-operate opinion.",
        }
    except (httpx.HTTPError, ElementTree.ParseError, KeyError, TypeError, ValueError) as exc:
        logger.warning("EPO OPS research unavailable error=%s", type(exc).__name__)
        return {
            "status": "unavailable",
            "provider": "European Patent Office Open Patent Services",
            "query": query["patent_display"],
            "records": [],
            "family_count": 0,
            "search_url": search_url,
            "limitation": "The live EPO request failed; no patent-family or claim-level result is asserted.",
        }


def _study_field(abstract: str, patterns: list[str], fallback: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", abstract)
    for sentence in sentences:
        if any(re.search(pattern, sentence, re.IGNORECASE) for pattern in patterns):
            return _clean(sentence)[:500]
    return fallback


def _local_nodes(element: ElementTree.Element, name: str) -> list[ElementTree.Element]:
    return [node for node in element.iter() if node.tag.rsplit("}", 1)[-1] == name]


def _pmc_sections(article: ElementTree.Element) -> dict[str, str]:
    sections: dict[str, str] = {}
    for section in _local_nodes(article, "sec"):
        title_node = next((node for node in list(section) if node.tag.rsplit("}", 1)[-1] == "title"), None)
        title = _element_text(title_node).lower()
        if not title:
            continue
        section_paragraphs = [_element_text(node) for node in _local_nodes(section, "p")]
        text = _clean(" ".join(item for item in section_paragraphs if item))
        if text:
            sections[title] = text[:30_000]
    return sections


def _section_text(sections: dict[str, str], names: tuple[str, ...]) -> str:
    return _clean(" ".join(text for title, text in sections.items() if any(name in title for name in names)))


def _appraisal_field(
    sources: list[tuple[str, str]], patterns: list[str], fallback: str
) -> tuple[str, str | None]:
    for locator, content in sources:
        for sentence in re.split(r"(?<=[.!?])\s+", content):
            if any(re.search(pattern, sentence, re.IGNORECASE) for pattern in patterns):
                return _clean(sentence)[:450], locator
    return fallback, None


def _pmc_identifier(article: ElementTree.Element) -> str | None:
    for identifier in _local_nodes(article, "article-id"):
        if identifier.attrib.get("pub-id-type") in {"pmc", "pmcid"}:
            value = _element_text(identifier)
            return value if value.upper().startswith("PMC") else f"PMC{value}"
    return None


def _study_reporting_screen(article: ElementTree.Element, whole_text: str) -> dict[str, Any]:
    title = _element_text(next(iter(_local_nodes(article, "article-title")), None))
    classification_text = f"{title} {whole_text[:8_000]}"
    if re.search(r"\bsystematic review\b|\bmeta-analysis\b", classification_text, re.IGNORECASE):
        study_type = "systematic_review"
        framework = "Systematic-review reporting signals"
        signal_patterns = {
            "search_strategy": r"\bsearch strateg|\bsearch terms?\b|\b(?:pubmed|medline|embase|scopus|cochrane)\b",
            "eligibility_criteria": r"\beligibility criteria\b|\binclusion criteria\b|\bexclusion criteria\b",
            "independent_screening": r"\b(?:two|2) (?:independent )?reviewers?\b|\bindependently (?:screened|reviewed|assessed)\b",
            "quality_appraisal": r"\brisk of bias\b|\bquality assessment\b|\bquality appraisal\b",
            "protocol_registration": r"\bPROSPERO\b|\bprotocol (?:was )?registered\b",
            "publication_bias": r"\bpublication bias\b|\bfunnel plot\b|\begger(?:'s)? test\b",
        }
    elif re.search(r"\brandomi[sz]|\brandomly (?:allocated|assigned)\b", classification_text, re.IGNORECASE):
        study_type = "randomized_trial"
        framework = "Randomized-trial reporting signals"
        signal_patterns = {
            "randomization": r"\brandomi[sz]|\brandomly (?:allocated|assigned)\b",
            "allocation_concealment": r"\ballocation conceal",
            "blinding": r"\b(?:double|single|triple)[- ]blind|\bmasked\b",
            "comparator": r"\bplacebo\b|\bcontrol group\b|\bcomparator\b",
            "attrition_reporting": r"\blost to follow[- ]up\b|\bwithdraw|\battrition\b",
            "trial_registration": r"\bNCT\d{8}\b|\btrial registration\b|\bregistered at\b",
            "intention_to_treat": r"\bintention[- ]to[- ]treat\b|\bintent[- ]to[- ]treat\b",
        }
    elif re.search(r"\bcohort\b|\bcase.control\b|\bcross-sectional\b|\bobservational\b", classification_text, re.IGNORECASE):
        study_type = "observational_study"
        framework = "Observational-study reporting signals"
        signal_patterns = {
            "eligibility_criteria": r"\beligibility criteria\b|\binclusion criteria\b|\bexclusion criteria\b",
            "exposure_definition": r"\bexposure (?:was )?(?:defined|measured|assessed)\b",
            "outcome_definition": r"\boutcome (?:was )?(?:defined|measured|assessed)\b",
            "confounding_adjustment": r"\bconfound|\badjusted (?:for|model)\b|\bmultivaria(?:te|ble)\b",
            "missing_data": r"\bmissing data\b|\blost to follow[- ]up\b|\battrition\b",
            "sensitivity_analysis": r"\bsensitivity analys",
        }
    elif re.search(r"\breview\b", title, re.IGNORECASE):
        study_type = "narrative_review"
        framework = "Narrative-review transparency signals"
        signal_patterns = {
            "source_search_described": r"\bsearch(?:ed| strategy)?\b|\b(?:pubmed|medline|embase|scopus)\b",
            "selection_criteria": r"\binclusion criteria\b|\bexclusion criteria\b|\bselection criteria\b",
            "quality_appraisal": r"\brisk of bias\b|\bquality assessment\b|\bquality appraisal\b",
            "limitations_discussed": r"\blimitation",
            "funding_reported": r"\bfund(?:ed|ing)\b|\bfinancial support\b",
            "conflicts_reported": r"\bconflict of interest\b|\bcompeting interests\b",
        }
    else:
        study_type = "unclassified_study"
        framework = "General study-reporting signals"
        signal_patterns = {
            "eligibility_criteria": r"\beligibility criteria\b|\binclusion criteria\b|\bexclusion criteria\b",
            "comparator": r"\bplacebo\b|\bcontrol group\b|\bcomparator\b",
            "outcomes_defined": r"\bprimary (?:outcome|endpoint)\b|\boutcome measure\b",
            "adverse_events": r"\badverse event",
            "limitations_discussed": r"\blimitation",
            "registration": r"\bNCT\d{8}\b|\bregistered at\b|\bprotocol registration\b",
        }
    signals = {
        label: bool(re.search(pattern, whole_text, re.IGNORECASE))
        for label, pattern in signal_patterns.items()
    }
    present = [label for label, found in signals.items() if found]
    missing = [label for label, found in signals.items() if not found]
    coverage = len(present) / len(signals) if signals else 0
    rating = (
        "stronger reporting coverage"
        if coverage >= 0.7
        else "partial reporting coverage"
        if coverage >= 0.4
        else "limited or unclear reporting coverage"
    )
    return {
        "study_type": study_type,
        "appraisal_framework": framework,
        "rating": rating,
        "present_signals": present,
        "missing_signals": missing,
        "notice": "Automated reporting-signal screen only; not a validated RoB 2, ROBINS-I or systematic-review appraisal.",
    }


def _parse_pmc_appraisals(content: bytes) -> dict[str, dict[str, Any]]:
    root = ElementTree.fromstring(content)
    appraisals: dict[str, dict[str, Any]] = {}
    for article in _local_nodes(root, "article"):
        pmcid = _pmc_identifier(article)
        if not pmcid:
            continue
        sections = _pmc_sections(article)
        methods = _section_text(
            sections,
            ("method", "material", "participant", "patient", "study design", "trial design"),
        )
        results = _section_text(sections, ("result", "outcome", "finding"))
        discussion = _section_text(sections, ("discussion", "limitation", "conclusion"))
        abstract = _clean(" ".join(_element_text(node) for node in _local_nodes(article, "abstract")))
        whole_text = _clean(" ".join(_element_text(node) for node in _local_nodes(article, "p")))[:100_000]
        method_sources = [("Methods", methods), ("Abstract", abstract)]
        result_sources = [("Results", results), ("Abstract", abstract), ("Discussion", discussion)]

        study_design, design_locator = _appraisal_field(
            method_sources,
            [r"\brandomi[sz]", r"\bdouble[- ]blind", r"\bsingle[- ]blind", r"\bcrossover\b", r"\bcohort\b", r"\bcase.control\b", r"\bparallel.group\b"],
            "Study design was not stated clearly in the retrieved full text.",
        )
        population, population_locator = _appraisal_field(
            method_sources,
            [r"\bparticipants?\b", r"\bpatients?\b", r"\bsubjects?\b", r"\benrolled\b", r"\bn\s*=\s*\d+", r"\beligib"],
            "Population details were not located in the retrieved full text.",
        )
        dose, dose_locator = _appraisal_field(
            method_sources,
            [r"\b\d+(?:\.\d+)?\s*(?:mg|g|ml|µg|mcg)\b", r"\bonce daily\b", r"\btwice daily\b", r"\bintervention\b", r"\badministered\b"],
            "Dose or exposure details were not located in the retrieved full text.",
        )
        comparator, comparator_locator = _appraisal_field(
            method_sources,
            [r"\bplacebo\b", r"\bcontrol group\b", r"\bcomparator\b", r"\busual care\b", r"\bactive control\b"],
            "Comparator details were not located in the retrieved full text.",
        )
        duration, duration_locator = _appraisal_field(
            method_sources,
            [r"\b\d+(?:\.\d+)?\s*(?:days?|weeks?|months?|years?)\b", r"\bfollow[- ]up\b", r"\btreatment period\b"],
            "Treatment or follow-up duration was not located in the retrieved full text.",
        )
        endpoints, endpoints_locator = _appraisal_field(
            method_sources,
            [r"\bprimary (?:outcome|endpoint)\b", r"\bsecondary (?:outcome|endpoint)\b", r"\boutcome measure\b", r"\bwas assessed\b", r"\bwas measured\b"],
            "Endpoint definitions were not located in the retrieved full text.",
        )
        numerical_results, results_locator = _appraisal_field(
            result_sources,
            [r"\bp\s*[<=>]\s*0?\.\d+", r"\bconfidence interval\b", r"\b95%\s*ci\b", r"\bmean difference\b", r"\b\d+(?:\.\d+)?%\b", r"\bsignificant"],
            "No numerical result sentence was extracted from the retrieved full text.",
        )
        adverse_events, adverse_locator = _appraisal_field(
            result_sources,
            [r"\badverse event", r"\bside effect", r"\btolerat", r"\bsafety\b", r"\bwithdraw.*(?:adverse|event)"],
            "Adverse-event reporting was not located in the retrieved full text.",
        )
        limitations, limitations_locator = _appraisal_field(
            [("Limitations / Discussion", discussion), ("Results", results)],
            [r"\blimitation", r"\bsmall sample\b", r"\bshort duration\b", r"\bpotential bias\b", r"\bgenerali[sz]ab", r"\bunderpowered\b"],
            "An explicit author-reported limitation was not located; independent critical appraisal is still required.",
        )

        funding_nodes = _local_nodes(article, "funding-group")
        funding = _clean(" ".join(_element_text(node) for node in funding_nodes))[:450]
        conflict_nodes = [
            node
            for node in _local_nodes(article, "fn")
            if node.attrib.get("fn-type") in {"conflict", "coi-statement", "competing-interests"}
        ]
        conflicts = _clean(" ".join(_element_text(node) for node in conflict_nodes))[:450]
        license_nodes = _local_nodes(article, "license")
        license_text = _clean(" ".join(_element_text(node) for node in license_nodes))[:300]

        reporting_screen = _study_reporting_screen(article, whole_text)

        appraisals[pmcid] = {
            "pmcid": pmcid,
            "full_text_url": f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/",
            "source_status": "pmc_full_text_appraised",
            "appraisal_status": "full_text_structured_appraisal",
            "study_type": reporting_screen["study_type"],
            "appraisal_framework": reporting_screen["appraisal_framework"],
            "study_design": study_design,
            "population": population,
            "dose": dose,
            "comparator": comparator,
            "duration": duration,
            "endpoints": endpoints,
            "numerical_results": numerical_results,
            "adverse_events": adverse_events,
            "limitations": limitations,
            "funding": funding or "Funding information was not located in the retrieved full text.",
            "conflicts": conflicts or "A conflict-of-interest statement was not located in the retrieved full text.",
            "license": license_text or "License statement not extracted; follow the PMC article-level terms.",
            "risk_of_bias": {
                "rating": reporting_screen["rating"],
                "present_signals": reporting_screen["present_signals"],
                "missing_signals": reporting_screen["missing_signals"],
                "notice": reporting_screen["notice"],
            },
            "section_locators": {
                "study_design": design_locator,
                "population": population_locator,
                "dose": dose_locator,
                "comparator": comparator_locator,
                "duration": duration_locator,
                "endpoints": endpoints_locator,
                "numerical_results": results_locator,
                "adverse_events": adverse_locator,
                "limitations": limitations_locator,
            },
        }
    return appraisals


def _parse_pubmed(content: bytes) -> list[dict[str, Any]]:
    root = ElementTree.fromstring(content)
    records = []
    for article in root.findall(".//PubmedArticle"):
        citation = article.find("MedlineCitation")
        article_node = citation.find("Article") if citation is not None else None
        if citation is None or article_node is None:
            continue
        pmid = _element_text(citation.find("PMID"))
        title = _element_text(article_node.find("ArticleTitle"))
        abstract = _clean(" ".join(_element_text(item) for item in article_node.findall(".//AbstractText")))
        journal = _element_text(article_node.find(".//Journal/Title"))
        year = _element_text(article_node.find(".//JournalIssue/PubDate/Year"))
        if not year:
            year = _element_text(article_node.find(".//JournalIssue/PubDate/MedlineDate"))
        doi = ""
        pmcid = ""
        for identifier in article.findall(".//ArticleId"):
            if identifier.attrib.get("IdType") == "doi":
                doi = _element_text(identifier)
            elif identifier.attrib.get("IdType") == "pmc":
                pmcid = _element_text(identifier)
        population = _study_field(
            abstract,
            [r"\bparticipants?\b", r"\bpatients?\b", r"\bsubjects?\b", r"\bvolunteers?\b", r"\bn\s*="],
            "Not reported in the retrieved abstract.",
        )
        dose = _study_field(
            abstract,
            [r"\b\d+(?:\.\d+)?\s*(?:mg|g|ml|µg|mcg)\b", r"\bonce daily\b", r"\btwice daily\b"],
            "Not reported in the retrieved abstract.",
        )
        endpoints = _study_field(
            abstract,
            [r"\bprimary outcome\b", r"\bendpoint\b", r"\bscore\b", r"\bmeasured\b", r"\bsignificant\b"],
            "No explicit endpoint sentence was extracted from the abstract.",
        )
        limitations = _study_field(
            abstract,
            [r"\blimitation", r"\bsmall sample\b", r"\bshort duration\b", r"\bbias\b", r"\bnot significant\b"],
            "Limitations were not stated in the retrieved abstract; full-text appraisal is required.",
        )
        records.append(
            {
                "pmid": pmid,
                "title": title,
                "journal": journal,
                "publication_date": year or "Not reported",
                "doi": doi or None,
                "pmcid": pmcid or None,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "population": population,
                "dose": dose,
                "endpoints": endpoints,
                "limitations": limitations,
                "abstract_excerpt": abstract[:700],
                "source_status": "pubmed_abstract_only",
                "appraisal_status": "abstract_only",
                "study_type": "not_appraised",
                "appraisal_framework": "Abstract-only screening",
                "study_design": "Full-text study design not appraised.",
                "comparator": "Full-text comparator not appraised.",
                "duration": "Full-text treatment duration not appraised.",
                "numerical_results": "Full-text numerical results not appraised.",
                "adverse_events": "Full-text adverse-event reporting not appraised.",
                "funding": "Full-text funding statement not appraised.",
                "conflicts": "Full-text conflict-of-interest statement not appraised.",
                "license": None,
                "full_text_url": None,
                "risk_of_bias": None,
                "section_locators": {},
            }
        )
    return records


@lru_cache(maxsize=128)
def _pubmed_search(query: str) -> tuple[dict[str, Any], ...]:
    params: dict[str, str | int] = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": settings.external_research_max_results,
        "sort": "relevance",
        "tool": "ip_sakti",
    }
    if settings.ncbi_api_key:
        params["api_key"] = settings.ncbi_api_key
    if settings.ncbi_contact_email:
        params["email"] = settings.ncbi_contact_email
    with httpx.Client(timeout=settings.external_research_timeout_seconds) as client:
        response = client.get(f"{NCBI_BASE}/esearch.fcgi", params=params)
        response.raise_for_status()
        identifiers = response.json().get("esearchresult", {}).get("idlist", [])
        if not identifiers:
            return ()
        fetch_params = {"db": "pubmed", "id": ",".join(identifiers), "retmode": "xml", "tool": "ip_sakti"}
        if settings.ncbi_api_key:
            fetch_params["api_key"] = settings.ncbi_api_key
        if settings.ncbi_contact_email:
            fetch_params["email"] = settings.ncbi_contact_email
        fetched = client.get(f"{NCBI_BASE}/efetch.fcgi", params=fetch_params)
        fetched.raise_for_status()
        records = _parse_pubmed(fetched.content)
        pmcids = [record["pmcid"] for record in records if record.get("pmcid")]
        if pmcids:
            try:
                full_text_params: dict[str, str] = {
                    "db": "pmc",
                    "id": ",".join(pmcids),
                    "retmode": "xml",
                    "tool": "ip_sakti",
                }
                if settings.ncbi_api_key:
                    full_text_params["api_key"] = settings.ncbi_api_key
                if settings.ncbi_contact_email:
                    full_text_params["email"] = settings.ncbi_contact_email
                full_text = client.get(f"{NCBI_BASE}/efetch.fcgi", params=full_text_params)
                full_text.raise_for_status()
                appraisals = _parse_pmc_appraisals(full_text.content)
                for record in records:
                    if record.get("pmcid") in appraisals:
                        record.update(appraisals[record["pmcid"]])
            except (httpx.HTTPError, ElementTree.ParseError, KeyError, TypeError, ValueError) as exc:
                logger.warning("PMC full-text appraisal unavailable error=%s", type(exc).__name__)
    return tuple(records)


def search_pubmed(case: Any, query: dict[str, str]) -> dict[str, Any]:
    search_url = f"https://pubmed.ncbi.nlm.nih.gov/?term={quote_plus(query['pubmed'])}"
    if not settings.external_research_enabled:
        return {
            "status": "disabled",
            "provider": "NCBI PubMed E-utilities",
            "query": query["pubmed"],
            "records": [],
            "search_url": search_url,
        }
    try:
        records = list(_pubmed_search(query["pubmed"]))
        return {
            "status": "live" if records else "no_results",
            "provider": "NCBI PubMed E-utilities",
            "query": query["pubmed"],
            "records": records,
            "search_url": search_url,
        }
    except (httpx.HTTPError, ElementTree.ParseError, KeyError, TypeError, ValueError) as exc:
        logger.warning("PubMed research unavailable error=%s", type(exc).__name__)
        return {
            "status": "unavailable",
            "provider": "NCBI PubMed E-utilities",
            "query": query["pubmed"],
            "records": [],
            "search_url": search_url,
        }


def search_patents(case: Any, query: dict[str, str]) -> dict[str, Any]:
    provider = settings.patent_search_provider.lower()
    if provider == "google_bigquery":
        return search_google_patents_bigquery(case, query)
    if provider == "epo_ops":
        return search_epo_patents(case, query)
    if settings.google_cloud_project:
        result = search_google_patents_bigquery(case, query)
        if result["status"] not in {"unavailable", "credential_required"}:
            return result
        if settings.epo_ops_consumer_key and settings.epo_ops_consumer_secret:
            return search_epo_patents(case, query)
        return result
    return search_epo_patents(case, query)


def run_external_research(case: Any) -> dict[str, Any]:
    query = build_research_query(case)
    if not settings.external_research_enabled:
        return {
            "query": query,
            "patents": search_patents(case, query),
            "science": search_pubmed(case, query),
            "status": "disabled",
        }
    patents = search_patents(case, query)
    science = search_pubmed(case, query)
    return {
        "query": query,
        "patents": patents,
        "science": science,
        "status": "live" if "live" in {patents["status"], science["status"]} else "unavailable",
    }
