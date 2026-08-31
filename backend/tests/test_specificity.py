from types import SimpleNamespace

from services.research import _parse_pubmed, build_research_query
from services.specificity import build_case_specific_analysis, build_specific_design_around


def detailed_case():
    return SimpleNamespace(
        id=41,
        title="Measured botanical release platform",
        description="A standardized botanical tablet with measured release.",
        ingredients=["Withania somnifera root extract 300 mg"],
        product_form="Film-coated tablet",
        intended_use="Stress resilience in adults after eight weeks",
        biological_sourcing="Cultivated Rajasthan material from supplier lot R-41",
        metadata_json={
            "quantitative_composition": "Withania somnifera root extract 300 mg per tablet",
            "standardization": "5% total withanolides",
            "extraction_ratio": "10:1; 70:30 ethanol:water",
            "dose": "One tablet twice daily for eight weeks",
            "release_profile": "20–35% at 2 h and at least 85% at 12 h",
            "manufacturing_process": "Vacuum concentration and film coating",
            "process_parameters": "50–55°C extraction for 4 h",
            "proposed_claim": "Supports stress resilience in adults after eight weeks",
            "classical_reference": "Charaka Samhita, uploaded extract page 12",
        },
    )


def test_case_specific_analysis_preserves_exact_facts_and_passages():
    case = detailed_case()
    match = {
        "document_id": 7,
        "chunk_index": 2,
        "filename": "authorized-classical-extract.pdf",
        "page_number": 12,
        "content": "The classical formulation contains Withania somnifera and is prepared as a root decoction.",
        "sha256": "a" * 64,
        "score": 0.88,
    }
    external = {
        "patents": {
            "status": "live",
            "provider": "EPO OPS",
            "query": "Withania release",
            "records": [
                {
                    "publication_number": "EP123A1",
                    "family_id": "99",
                    "title": "Botanical release dosage form",
                    "claims": [{"claim": "1", "text": "A tablet comprising Withania and controlled release coating."}],
                    "url": "https://worldwide.espacenet.com/",
                    "source": "EPO OPS live result",
                }
            ],
            "family_count": 1,
            "search_url": "https://worldwide.espacenet.com/",
        },
        "science": {"status": "no_results", "query": "Withania", "records": [], "search_url": "https://pubmed.ncbi.nlm.nih.gov/"},
    }
    result = build_case_specific_analysis(case, [match], external)

    assert result["input_completeness"]["score"] >= 90
    assert any("300 mg" in row["submitted_value"] for row in result["novelty_claim_chart"])
    assert result["traditional_knowledge"]["records"][0]["locator"] == "page 12"
    assert result["traditional_knowledge"]["records"][0]["content_sha256"] == "a" * 64
    assert any(row["status"] == "overlap_found" for row in result["novelty_claim_chart"])
    design = build_specific_design_around(case, result, ["Patent"], [])
    assert len(design["alternatives"]) == 4
    assert all(item["basis"].startswith("Submitted fact:") for item in design["alternatives"])


def test_pubmed_parser_extracts_structured_appraisal_fields():
    xml = b"""<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID><Article>
      <ArticleTitle>Botanical randomized trial</ArticleTitle><Journal><Title>Evidence Journal</Title>
      <JournalIssue><PubDate><Year>2025</Year></PubDate></JournalIssue></Journal>
      <Abstract><AbstractText>Sixty adult participants were randomized. The dose was 300 mg twice daily. The primary endpoint was a validated stress score. Limitations included short duration and a small sample.</AbstractText></Abstract>
      </Article></MedlineCitation><PubmedData><ArticleIdList><ArticleId IdType="doi">10.1/example</ArticleId></ArticleIdList></PubmedData>
      </PubmedArticle></PubmedArticleSet>"""
    record = _parse_pubmed(xml)[0]
    assert "participants" in record["population"]
    assert "300 mg" in record["dose"]
    assert "endpoint" in record["endpoints"]
    assert "Limitations" in record["limitations"]
    assert record["url"].endswith("/123/")


def test_research_query_uses_ingredient_or_group():
    query = build_research_query(detailed_case())
    assert "Withania somnifera" in query["pubmed"]
    assert "Title/Abstract" in query["pubmed"]
    assert '"and"[Title/Abstract]' not in query["pubmed"]
