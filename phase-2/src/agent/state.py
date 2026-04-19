"""Typed state contract for the LangGraph lending agent."""

from __future__ import annotations

from typing import Optional, TypedDict


class AgentState(TypedDict):
    """State shared across the profile, risk, retrieval, and report nodes."""

    borrower_data: dict
    ml_risk_score: float
    risk_class: str
    top_features: list[dict]
    borrower_summary: str
    risk_analysis: str
    retrieval_query: str
    retrieved_docs: list[dict]
    final_report: Optional[dict]
    error_flags: list[str]
    processing_steps: list[str]
