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
WORD_RE = re.compile(r"[A-Za-z][A-Za-z-]{2,}")


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
        for identifier in article.findall(".//ArticleId"):
            if identifier.attrib.get("IdType") == "doi":
                doi = _element_text(identifier)
                break
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
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "population": population,
                "dose": dose,
                "endpoints": endpoints,
                "limitations": limitations,
                "abstract_excerpt": abstract[:700],
                "source_status": "live_pubmed_abstract",
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
    return tuple(_parse_pubmed(fetched.content))


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


def run_external_research(case: Any) -> dict[str, Any]:
    query = build_research_query(case)
    if not settings.external_research_enabled:
        return {
            "query": query,
            "patents": search_epo_patents(case, query),
            "science": search_pubmed(case, query),
            "status": "disabled",
        }
    patents = search_epo_patents(case, query)
    science = search_pubmed(case, query)
    return {
        "query": query,
        "patents": patents,
        "science": science,
        "status": "live" if "live" in {patents["status"], science["status"]} else "unavailable",
    }
