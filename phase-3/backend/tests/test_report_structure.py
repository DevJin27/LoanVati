"""Contract tests for the final structured lending report."""

SAMPLE_RETRIEVED_DOCS = [
    {
        "content": "Sample RBI fair practices excerpt.",
        "source_name": "Rbi Fair Practices Code",
        "section_id": "Section 3.1 - Credit Appraisal Principles",
        "score": 0.71,
    },
    {
        "content": "Sample Basel default probability excerpt.",
        "source_name": "Basel3 Credit Risk",
        "section_id": "Section 2.1 - Probability of Default",
        "score": 0.66,
    },
]

SAMPLE_REPORT = {
    "profile": "Stable income with moderate leverage and steady employment.",
    "risk_analysis": "Risk is elevated but not conclusive, so escalation is prudent.",
    "decision": {
        "action": "MANUAL REVIEW",
        "justification": "The score is near the threshold and needs human review.",
    },
    "sources": [
        {
            "title": "Rbi Fair Practices Code",
            "section_id": "Section 3.1 - Credit Appraisal Principles",
            "score": 0.71,
        },
        {
            "title": "Basel3 Credit Risk",
            "section_id": "Section 2.1 - Probability of Default",
            "score": 0.66,
        },
    ],
    "disclaimer": "AI-assisted recommendation. Not the sole basis for lending decisions.",
}


def test_report_has_all_5_sections() -> None:
    required = ["profile", "risk_analysis", "decision", "sources", "disclaimer"]
    for key in required:
        assert key in SAMPLE_REPORT, f"Missing section: {key}"


def test_disclaimer_text_present() -> None:
    assert "AI-assisted recommendation" in SAMPLE_REPORT["disclaimer"]
    assert "Not the sole basis" in SAMPLE_REPORT["disclaimer"]


def test_decision_is_valid_action() -> None:
    assert SAMPLE_REPORT["decision"]["action"] in ["APPROVE", "REJECT", "MANUAL REVIEW"]


def test_sources_only_cite_retrieved_docs() -> None:
    retrieved_sources = {document["source_name"] for document in SAMPLE_RETRIEVED_DOCS}
    for source in SAMPLE_REPORT["sources"]:
        assert source["title"] in retrieved_sources, f"Hallucinated citation: {source['title']}"
