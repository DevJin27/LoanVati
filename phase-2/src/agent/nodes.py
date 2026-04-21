"""LangGraph node implementations for the lending decision assistant."""

from __future__ import annotations

import json
import os
import time
import importlib

import streamlit as st
from langchain_groq import ChatGroq

from src.agent.prompts import (
    PROFILE_NODE_SYSTEM,
    PROFILE_NODE_USER,
    REPORT_NODE_SYSTEM,
    REPORT_NODE_USER,
    RISK_NODE_SYSTEM,
    RISK_NODE_USER,
)
from src.agent.state import AgentState
from src.rag.retriever import FAISSRetriever

REGULATORY_FALLBACK = {
    "content": (
        "Per RBI fair practice expectations, lenders should assess income stability, "
        "existing debt obligations, and repayment history before making a lending decision."
    ),
    "source_name": "RBI Fair Practices Code (Fallback)",
    "section_id": "General",
    "score": 0.0,
}


def _get_groq_api_key() -> str | None:
    """Resolve GROQ API key from environment or Streamlit secrets."""
    env_key = os.getenv("GROQ_API_KEY")
    if env_key:
        return env_key

    try:
        st = importlib.import_module("streamlit")
        secret_value = st.secrets.get("GROQ_API_KEY")
        return str(secret_value) if secret_value else None
    except Exception:
        return None


def get_llm() -> ChatGroq:
    """Return the configured Groq client with deterministic settings.

    Model: llama-3.3-70b-versatile
    - Groq free tier, same API key as the 8B model
    - Significantly better JSON schema adherence and instruction following
    - Fixes profile text garbling caused by the 8B model hitting token limits mid-sentence
    """
    return ChatGroq(
        groq_api_key=_get_groq_api_key(),
        model="llama-3.3-70b-versatile",
        temperature=0.0,
        max_tokens=2_048,
    )


def _state_copy(state: AgentState) -> dict:
    return {
        "error_flags": list(state.get("error_flags", [])),
        "processing_steps": list(state.get("processing_steps", [])),
    }


def _invoke_prompt(system_prompt: str, user_prompt: str) -> str:
    """Call the LLM with two retries and exponential backoff."""
    if not _get_groq_api_key():
        raise RuntimeError("Missing GROQ_API_KEY (set env var or Streamlit secret)")

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            llm = get_llm()
            response = llm.invoke(
                [
                    ("system", system_prompt),
                    ("user", user_prompt),
                ]
            )
            return getattr(response, "content", str(response)).strip()
        except Exception as exc:  # pragma: no cover - exercised through mocks
            last_error = exc
            if attempt < 2:
                time.sleep(2**attempt)
    raise RuntimeError(str(last_error) if last_error else "Unknown LLM error")


def _fallback_risk_analysis(state: AgentState) -> tuple[str, str]:
    """Create a deterministic analysis if the LLM cannot return valid JSON."""
    top_features = ", ".join(
        feature.get("feature", "unknown_feature") for feature in state.get("top_features", [])[:3]
    )
    risk_analysis = (
        f"The model assigned a risk score of {state['ml_risk_score']:.3f} and classified the "
        f"borrower as {state['risk_class']}. The strongest model signals were {top_features}. "
        "This summary was generated from model outputs because the LLM response could not be parsed."
    )
    retrieval_query = "credit appraisal fair practices manual review lending risk"
    return risk_analysis, retrieval_query


def _validate_report(report: dict, retrieved_docs: list[dict]) -> None:
    required_keys = {"profile", "risk_analysis", "decision", "regulatory_summary", "sources", "disclaimer"}
    if not required_keys.issubset(report.keys()):
        raise ValueError(f"Report JSON is missing required keys: {required_keys - set(report.keys())}")

    decision = report.get("decision", {})
    if decision.get("action") not in {"APPROVE", "REJECT", "MANUAL REVIEW"}:
        raise ValueError("Invalid decision action")

    allowed_sources = {item["source_name"] for item in retrieved_docs}
    for source in report.get("sources", []):
        if source.get("title") not in allowed_sources:
            # We construct `sources` natively now, so this shouldn't fail, but we keep it for integrity
            raise ValueError(f"Report cited a source that was not retrieved: {source.get('title')}")

    disclaimer = report.get("disclaimer", "")
    required_disclaimer = "AI-assisted recommendation. Not the sole basis for lending decisions."
    if required_disclaimer not in disclaimer:
        raise ValueError("Missing required disclaimer text")


def _fallback_report(state: AgentState) -> dict:
    """Return a safe deterministic report when the report LLM fails."""
    decision_action = (
        "MANUAL REVIEW"
        if "Uncertain" in state["risk_class"] or state["ml_risk_score"] >= 0.45
        else "APPROVE"
        if state["ml_risk_score"] < 0.30
        else "REJECT"
    )
    return {
        "profile": state.get("borrower_summary", ""),
        "risk_analysis": state.get("risk_analysis", ""),
        "decision": {
            "action": decision_action,
            "justification": (
                f"Model risk score={state['ml_risk_score']:.3f}; risk class={state['risk_class']}."
            ),
        },
        "sources": [
            {
                "title": item["source_name"],
                "section_id": item["section_id"],
                "score": item["score"],
            }
            for item in state.get("retrieved_docs", [])
        ],
        "regulatory_summary": [
            "Could not parse comprehensive regulatory compliance from LLM.",
            "Please review the explicit source paragraphs manually."
        ],
        "disclaimer": "AI-assisted recommendation. Not the sole basis for lending decisions.",
    }


def profile_node(state: AgentState) -> dict:
    """Summarize borrower context into a short analyst-ready profile."""
    update = _state_copy(state)
    try:
        response = _invoke_prompt(
            PROFILE_NODE_SYSTEM,
            PROFILE_NODE_USER.format(
                borrower_data_json=json.dumps(state["borrower_data"], indent=2, default=str)
            ),
        )
        update["borrower_summary"] = response
        update["processing_steps"].append("ProfileNode: OK")
    except Exception as exc:
        fallback_summary = (
            f"Borrower summary unavailable from LLM. Using raw data with "
            f"{len(state['borrower_data'])} supplied fields."
        )
        update["borrower_summary"] = fallback_summary
        update["error_flags"].append(f"PROFILE_NODE_ERROR: {exc}")
        update["processing_steps"].append("ProfileNode: FALLBACK")
    return update


def risk_node(state: AgentState) -> dict:
    """Explain model drivers and synthesize a retrieval query."""
    update = _state_copy(state)
    top_features_json = json.dumps(state["top_features"], indent=2, default=str)
    user_prompt = RISK_NODE_USER.format(
        borrower_summary=state["borrower_summary"],
        ml_risk_score=state["ml_risk_score"],
        risk_class=state["risk_class"],
        top_features_json=top_features_json,
    )

    for attempt in range(2):
        try:
            response = _invoke_prompt(RISK_NODE_SYSTEM, user_prompt)
            
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            elif cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()

            payload = json.loads(cleaned_response)
            update["risk_analysis"] = payload["risk_analysis"]
            update["retrieval_query"] = payload["retrieval_query"]
            update["processing_steps"].append("RiskNode: OK")
            return update
        except Exception as exc:
            if attempt == 0:
                user_prompt += "\nReturn valid JSON only."
                continue
            fallback_analysis, fallback_query = _fallback_risk_analysis(state)
            update["risk_analysis"] = fallback_analysis
            update["retrieval_query"] = fallback_query
            update["error_flags"].append(f"RISK_NODE_ERROR: {exc}")
            update["processing_steps"].append("RiskNode: FALLBACK")
            return update

    return update


@st.cache_resource(show_spinner="Loading regulatory index...")
def _get_retriever() -> "FAISSRetriever":
    """Load the FAISS retriever once and cache it for the lifetime of the
    Streamlit session.  Re-creating it on every agent run causes PyTorch to
    reload the SentenceTransformer model each time, which segfaults on
    Apple Silicon when the process tries to clean up the multiprocessing
    semaphores that sentence-transformers internally allocates.
    """
    return FAISSRetriever()


def rag_node(state: AgentState) -> dict:
    """Retrieve relevant regulatory context without using the LLM."""
    update = _state_copy(state)
    try:
        retriever = _get_retriever()
        results = retriever.query(state["retrieval_query"], top_k=3)
        if not results:
            update["retrieved_docs"] = [REGULATORY_FALLBACK]
            update["error_flags"].append(
                "RAG_ZERO_RESULTS: using fallback regulatory context"
            )
            update["processing_steps"].append("RAGNode: FALLBACK")
            return update

        update["retrieved_docs"] = results
        update["processing_steps"].append("RAGNode: OK")
    except Exception as exc:
        update["retrieved_docs"] = [REGULATORY_FALLBACK]
        update["error_flags"].append(f"RAG_NODE_ERROR: {exc}")
        update["processing_steps"].append("RAGNode: FALLBACK")
    return update


def report_node(state: AgentState) -> dict:
    """Synthesize the final five-section lending report."""
    update = _state_copy(state)
    user_prompt = REPORT_NODE_USER.format(
        borrower_summary=state["borrower_summary"],
        risk_analysis=state["risk_analysis"],
        ml_risk_score=state["ml_risk_score"],
        risk_class=state["risk_class"],
        top_features_json=json.dumps(state["top_features"], indent=2, default=str),
        retrieved_docs_json=json.dumps(state["retrieved_docs"], indent=2, default=str),
    )

    last_response = ""
    for attempt in range(2):
        try:
            response = _invoke_prompt(REPORT_NODE_SYSTEM, user_prompt)
            last_response = response
            
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            elif cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()

            report = json.loads(cleaned_response)
            
            # Forcibly inject the raw sources natively so the LLM doesn't have to guess or mis-capitalize
            report["sources"] = [
                {
                    "title": item["source_name"],
                    "section_id": item["section_id"],
                    "score": item["score"],
                }
                for item in state.get("retrieved_docs", [])
            ]
            
            _validate_report(report, state["retrieved_docs"])
            update["final_report"] = report
            update["processing_steps"].append("ReportNode: OK")
            return update
        except Exception as exc:
            if attempt == 0:
                user_prompt += "\nReturn only valid JSON with the required schema."
                continue
            
            with open("/tmp/report_fallback_error.log", "w") as f:
                f.write(f"Exception: {repr(exc)}\n\nRAW RESPONSE:\n{last_response}")

            update["final_report"] = _fallback_report(state)
            update["error_flags"].append(f"REPORT_NODE_ERROR: {exc}")
            update["processing_steps"].append("ReportNode: FALLBACK")
            return update

    return update
