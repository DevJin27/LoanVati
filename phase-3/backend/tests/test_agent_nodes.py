"""Tests for agent nodes and graph wiring."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from src.agent.graph import run_agent
from src.agent.nodes import REGULATORY_FALLBACK, profile_node, rag_node, report_node


def build_minimal_state() -> dict:
    return {
        "borrower_data": {"AMT_INCOME_TOTAL": 180000, "DAYS_EMPLOYED": -2200},
        "ml_risk_score": 0.48,
        "risk_class": "Uncertain — Manual Review Required",
        "top_features": [
            {"feature": "credit_income_ratio", "shap_value": 0.21, "direction": "increases risk"}
        ],
        "borrower_summary": "",
        "risk_analysis": "",
        "retrieval_query": "credit appraisal",
        "retrieved_docs": [],
        "final_report": None,
        "error_flags": [],
        "processing_steps": [],
    }


def build_full_mock_state() -> dict:
    state = build_minimal_state()
    state["borrower_summary"] = "Stable income with moderate leverage."
    state["risk_analysis"] = "Risk is elevated because repayment burden is high."
    state["retrieved_docs"] = [
        {
            "content": "Sample regulatory context",
            "source_name": "Rbi Fair Practices Code",
            "section_id": "Section 3.1 - Credit Appraisal Principles",
            "score": 0.71,
        }
    ]
    return state


MOCK_REPORT_JSON = json.dumps(
    {
        "profile": "Stable income with moderate leverage.",
        "risk_analysis": "Risk is elevated because repayment burden is high.",
        "decision": {
            "action": "MANUAL REVIEW",
            "justification": "Score is near the decision threshold.",
        },
        "sources": [
            {
                "title": "Rbi Fair Practices Code",
                "section_id": "Section 3.1 - Credit Appraisal Principles",
                "score": 0.71,
            }
        ],
        "disclaimer": "AI-assisted recommendation. Not the sole basis for lending decisions.",
    }
)


def test_profile_node_populates_summary() -> None:
    with patch("src.agent.nodes.get_llm") as mock_llm:
        mock_llm.return_value.invoke.return_value = MagicMock(
            content="Borrower shows steady income and moderate employment tenure."
        )
        result = profile_node(build_minimal_state())
        assert "borrower_summary" in result
        assert len(result["borrower_summary"]) > 20


def test_rag_node_uses_fallback_on_empty_results() -> None:
    with patch("src.agent.nodes.FAISSRetriever") as mock_retriever:
        mock_retriever.return_value.query.return_value = []
        result = rag_node(build_minimal_state())
        assert result["retrieved_docs"] == [REGULATORY_FALLBACK]
        assert "RAG_ZERO_RESULTS" in result["error_flags"][0]


def test_report_node_validates_5_sections() -> None:
    state = build_full_mock_state()
    with patch("src.agent.nodes.get_llm") as mock_llm:
        mock_llm.return_value.invoke.return_value = MagicMock(content=MOCK_REPORT_JSON)
        result = report_node(state)
        assert result.get("final_report") is not None
        for key in ["profile", "risk_analysis", "decision", "sources", "disclaimer"]:
            assert key in result["final_report"]


def test_agent_graph_end_to_end_mock() -> None:
    responses = iter(
        [
            MagicMock(content="Borrower profile summary."),
            MagicMock(
                content=json.dumps(
                    {
                        "risk_analysis": "Risk explanation based on SHAP.",
                        "retrieval_query": "credit appraisal fair practices",
                    }
                )
            ),
            MagicMock(content=MOCK_REPORT_JSON),
        ]
    )

    with patch("src.agent.nodes.get_llm") as mock_llm:
        mock_llm.return_value.invoke.side_effect = lambda *_args, **_kwargs: next(responses)
        with patch("src.agent.nodes.FAISSRetriever") as mock_retriever:
            mock_retriever.return_value.query.return_value = build_full_mock_state()[
                "retrieved_docs"
            ]
            result = run_agent(
                {"AMT_INCOME_TOTAL": 180000},
                {
                    "risk_score": 0.48,
                    "risk_class": "Uncertain — Manual Review Required",
                    "top_features": [
                        {
                            "feature": "credit_income_ratio",
                            "shap_value": 0.21,
                            "direction": "increases risk",
                        }
                    ],
                },
            )
            assert result["final_report"] is not None
            assert len(result["processing_steps"]) == 4
