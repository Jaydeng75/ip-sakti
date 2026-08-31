from evaluation import evaluate


def test_starter_retrieval_evaluation_is_reproducible():
    report = evaluate()
    assert report["query_count"] == 8
    assert report["status"] == "engineering-smoke-set-not-expert-validation"
    assert report["metrics"]["recall_at_5"] >= 0.8
    assert report["metrics"]["abstention_accuracy"] == 1.0
    assert report["warning"].startswith("This starter engineering set")
