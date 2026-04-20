"""Streamlit agent report tab."""

from __future__ import annotations

import time

import streamlit as st

from src.agent.nodes import profile_node, rag_node, report_node, risk_node
from src.models.predict import CreditRiskPredictor
from src.preprocessing.dataset import PHASE_ROOT
from src.ui.components import (
    build_manual_feature_input,
    render_feature_importance_chart,
    render_model_artifact_error,
    render_progress_steps,
    render_risk_badge,
)


@st.cache_resource
def get_predictor() -> CreditRiskPredictor:
    return CreditRiskPredictor(models_path=PHASE_ROOT / "models")


def _run_agent_with_progress(borrower_data: dict, prediction: dict) -> dict:
    """Execute agent nodes sequentially so the UI can show each stage."""
    state = {
        "borrower_data": borrower_data,
        "ml_risk_score": prediction["risk_score"],
        "risk_class": prediction["risk_class"],
        "top_features": prediction["top_features"],
        "borrower_summary": "",
        "risk_analysis": "",
        "retrieval_query": "",
        "retrieved_docs": [],
        "final_report": None,
        "error_flags": [],
        "processing_steps": [],
    }

    progress_placeholder = st.empty()
    started_at = time.time()
    for index, (label, node) in enumerate(
        [
            ("Profile Analysis", profile_node),
            ("Risk Reasoning", risk_node),
            ("Regulatory Document Retrieval", rag_node),
            ("Report Generation", report_node),
        ],
        start=1,
    ):
        with progress_placeholder.container():
            render_progress_steps(
                [
                    "Profile Analysis",
                    "Risk Reasoning",
                    "Regulatory Retrieval",
                    "Report Generation",
                ],
                index,
            )
            st.caption(f"Running: {label}")

        if time.time() - started_at > 15:
            st.info("The agent is taking longer than usual. Still processing...")

        state.update(node(state))

    progress_placeholder.empty()
    return state


def render_agent_tab() -> None:
    """Render the AI lending report workflow."""
    st.subheader("Input")
    st.caption("Use sliders and textboxes to enter borrower details.")
    borrower_data = build_manual_feature_input(prefix="agent")

    if st.button("Generate Lending Report", type="primary"):
        try:
            prediction = get_predictor().predict(borrower_data)
        except FileNotFoundError as exc:
            render_model_artifact_error(str(exc))
            return
        st.session_state["agent_result"] = {
            "prediction": prediction,
            "state": _run_agent_with_progress(borrower_data, prediction),
        }

    result = st.session_state.get("agent_result")
    if result is None:
        return

    prediction = result["prediction"]
    state = result["state"]
    report = state.get("final_report") or {}

    if state["error_flags"]:
        st.warning("Report generation encountered an error. Partial results shown below.")

    st.subheader("Report Display")
    with st.container(border=True):
        st.markdown("### Borrower Profile")
        st.write(report.get("profile", state.get("borrower_summary", "")))

    with st.container(border=True):
        st.markdown("### Risk Analysis")
        render_risk_badge(prediction["risk_class"])
        analysis = report.get("risk_analysis", state.get("risk_analysis", ""))
        st.write(analysis)

    decision = report.get("decision", {})
    decision_action = decision.get("action", "MANUAL REVIEW")
    decision_color = {
        "APPROVE": "#dcfce7",
        "REJECT": "#fee2e2",
        "MANUAL REVIEW": "#fef3c7",
    }.get(decision_action, "#fef3c7")
    st.markdown(
        f"""
        <div style="background:{decision_color};padding:16px;border-radius:12px;margin:12px 0;color:#1f2937;">
            <h3 style="margin:0;color:#1f2937;">{decision_action}</h3>
            <p style="margin:8px 0 0 0;">{decision.get('justification', 'No justification available.')}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Regulatory Summary", expanded=True):
        if "regulatory_summary" in report:
            for point in report["regulatory_summary"]:
                st.markdown(f"- {point}")
        else:
            for source in report.get("sources", []):
                st.markdown(f"- **{source['title']}** | relevance `{source['score']}`")

    st.markdown(
        f"*{report.get('disclaimer', 'AI-assisted recommendation. Not the sole basis for lending decisions.')}*"
    )

    with st.expander("Agent Reasoning Trace"):
        for step in state["processing_steps"]:
            st.markdown(f"- {step}")

    with st.expander("Warnings"):
        if state["error_flags"]:
            for warning in state["error_flags"]:
                st.markdown(f"- {warning}")
        else:
            st.write("No warnings")

    with st.expander("Risk Feature Detail"):
        render_feature_importance_chart(prediction["top_features"])
