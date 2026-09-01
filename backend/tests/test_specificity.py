from types import SimpleNamespace

from services import research
from services.research import _bigquery_terms, _parse_pmc_appraisals, _parse_pubmed, _verified_duration, build_research_query
from services.specificity import annotate_study_matches, build_case_specific_analysis, build_specific_design_around


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
    assert "TKDLSearch.asp" in result["traditional_knowledge"]["search_url"]
    assert result["traditional_knowledge"]["integration_mode"] == "official_search_handoff_and_authorized_export_import"
    assert any(row["status"] == "overlap_found" for row in result["novelty_claim_chart"])
    advisory = result["technical_advisory"]
    assert len(advisory["feature_assessments"]) >= 7
    assert len(advisory["strength_actions"]) == 5
    assert len(advisory["change_scenarios"]) == 3
    assert advisory["inventive_step"]["reasoning"]
    assert advisory["classification_resolver"]["questions"]
    design = build_specific_design_around(case, result, ["Patent"], [])
    assert len(design["alternatives"]) == 4
    assert all(item["basis"].startswith("Submitted fact:") for item in design["alternatives"])


def test_pubmed_parser_extracts_structured_appraisal_fields():
    xml = b"""<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID><Article>
      <ArticleTitle>Botanical randomized trial</ArticleTitle><Journal><Title>Evidence Journal</Title>
      <JournalIssue><PubDate><Year>2025</Year></PubDate></JournalIssue></Journal>
      <Abstract><AbstractText>Sixty adult participants were randomized. The dose was 300 mg twice daily. The primary endpoint was a validated stress score. Limitations included short duration and a small sample.</AbstractText></Abstract>
      </Article></MedlineCitation><PubmedData><ArticleIdList><ArticleId IdType="doi">10.1/example</ArticleId><ArticleId IdType="pmc">PMC123</ArticleId></ArticleIdList></PubmedData>
      </PubmedArticle></PubmedArticleSet>"""
    record = _parse_pubmed(xml)[0]
    assert "participants" in record["population"]
    assert "300 mg" in record["dose"]
    assert "endpoint" in record["endpoints"]
    assert "Limitations" in record["limitations"]
    assert record["url"].endswith("/123/")
    assert record["pmcid"] == "PMC123"
    assert record["appraisal_status"] == "abstract_only"


def test_pmc_parser_extracts_full_text_appraisal_and_reporting_signals():
    xml = b"""<pmc-articleset><article><front><article-meta>
      <article-id pub-id-type="pmcid">PMC987654</article-id>
      <permissions><license><license-p>Creative Commons Attribution 4.0.</license-p></license></permissions>
      <abstract><p>A randomized placebo-controlled botanical trial.</p></abstract>
      </article-meta></front><body>
      <sec><title>Methods</title>
        <p>Sixty adult participants were randomized to receive 300 mg twice daily or placebo for 8 weeks.</p>
        <p>The primary endpoint was change in a validated stress score measured at week 8.</p>
        <p>Allocation concealment and double-blind masking were used, and the trial registration was NCT12345678.</p>
      </sec>
      <sec><title>Results</title>
        <p>The mean difference was -3.2 points (95% CI -5.1 to -1.3; p=0.002).</p>
        <p>Adverse events were mild, and two participants withdrew.</p>
      </sec>
      <sec><title>Discussion and limitations</title><p>A limitation was the small sample and short duration.</p></sec>
      </body><back>
      <funding-group><award-group><funding-source>Public Research Council</funding-source></award-group></funding-group>
      <fn-group><fn fn-type="conflict"><p>The authors declare no competing interests.</p></fn></fn-group>
      </back></article></pmc-articleset>"""

    record = _parse_pmc_appraisals(xml)["PMC987654"]

    assert record["source_status"] == "pmc_full_text_appraised"
    assert record["study_type"] == "randomized_trial"
    assert record["appraisal_framework"] == "Randomized-trial reporting signals"
    assert "randomized" in record["study_design"]
    assert "participants" in record["population"]
    assert "300 mg" in record["dose"]
    assert "placebo" in record["comparator"]
    assert "95% CI" in record["numerical_results"]
    assert "Adverse events" in record["adverse_events"]
    assert "small sample" in record["limitations"]
    assert "Public Research Council" in record["funding"]
    assert "no competing interests" in record["conflicts"]
    assert "randomization" in record["risk_of_bias"]["present_signals"]
    assert record["section_locators"]["population"] == "Methods"


def test_research_query_uses_ingredient_or_group():
    query = build_research_query(detailed_case())
    assert "Withania somnifera" in query["pubmed"]
    assert "Title/Abstract" in query["pubmed"]
    assert '"and"[Title/Abstract]' not in query["pubmed"]


def test_bacopa_clinical_query_excludes_delivery_excipient_and_keeps_delivery_query_separate():
    case = SimpleNamespace(
        title="BrahmiQ",
        ingredients=["Bacopa monnieri extract", "Phosphatidylcholine", "Glycerol", "Purified water"],
        product_form="Oral mucosal spray",
        intended_use="Supports memory, attention and cognitive performance in healthy adults",
        metadata_json={"delivery_mechanism": "Phospholipid-based metered oral spray"},
    )
    query = build_research_query(case)

    assert "Bacopa monnieri" in query["pubmed_clinical"]
    assert "Phosphatidylcholine" not in query["pubmed_clinical"]
    assert "Glycerol" not in query["pubmed_clinical"]
    assert "Purified water" not in query["pubmed_clinical"]
    assert "oral spray" in query["pubmed_delivery"].lower()


def test_study_matching_does_not_promote_ingredient_study_to_exact_product_evidence():
    case = SimpleNamespace(
        ingredients=["Bacopa monnieri extract"],
        product_form="Oral mucosal spray",
        intended_use="Supports memory, attention and cognitive performance in healthy adults",
        metadata_json={
            "dose": "150 mg/day",
            "standardization": "50% bacosides",
            "delivery_mechanism": "Phospholipid-based metered oral mucosal spray",
        },
    )
    records, counts = annotate_study_matches(case, [{
        "title": "Bacopa monnieri capsules for memory in healthy adults",
        "abstract_excerpt": "Healthy adults received 300 mg capsules. Memory improved; attention was measured.",
        "population": "Healthy adults",
        "dose": "300 mg capsules",
        "endpoints": "Memory and attention",
        "study_design": "Randomized trial",
        "appraisal_status": "abstract_only",
        "retrieval_scope": "ingredient_clinical",
    }])

    assert records[0]["evidence_role"] == "ingredient_clinical"
    assert counts["ingredient_level"] == 1
    assert counts["direct_product"] == 0
    assert counts["dose_matched"] == 0
    assert counts["formulation_matched"] == 0


def test_duration_verifier_requires_an_actual_time_value():
    assert _verified_duration("Participants completed follow-up visits.").startswith("Treatment or follow-up")
    assert _verified_duration("Participants were aged between 6 and 14 years.").startswith("Treatment or follow-up")
    assert _verified_duration("Participants completed 12 weeks of treatment.") == "Participants completed 12 weeks of treatment."


def test_bigquery_query_terms_preserve_searchable_detail():
    terms = _bigquery_terms(detailed_case())

    assert "withania somnifera" in terms
    assert "withanolides" in terms


def test_bigquery_provider_maps_family_and_claim_results(monkeypatch):
    monkeypatch.setattr(research.settings, "google_cloud_project", "billing-project")
    monkeypatch.setattr(
        research,
        "_query_google_patents",
        lambda *_: (
            (
                {
                    "publication_number": "US-123-A1",
                    "family_id": "family-7",
                    "title": "Botanical release tablet",
                    "url": "https://patents.google.com/patent/US123A1/en",
                    "country": "United States",
                    "publication_description": "Application",
                    "term_hits": 2,
                },
            ),
            "2026-08-31T00:00:00+00:00",
            12_345,
        ),
    )

    result = research.search_google_patents_bigquery(detailed_case(), build_research_query(detailed_case()))

    assert result["status"] == "family_live_claims_not_retrieved"
    assert result["family_count"] == 1
    assert result["records"][0]["claims"] == []
    assert result["dataset_modified_at"].startswith("2026-08-31")
    assert result["bytes_billed"] == 12_345
