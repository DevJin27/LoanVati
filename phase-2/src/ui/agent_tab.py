"""Streamlit agent report tab."""

from __future__ import annotations

import time

import streamlit as st

from src.agent.nodes import profile_node, rag_node, report_node, risk_node
from src.models.predict import CreditRiskPredictor
from src.preprocessing.dataset import PHASE_ROOT
from src.ui.components import (
    build_manual_feature_input,
    load_uploaded_dataframe,
    render_error_banner,
    render_feature_importance_chart,
    render_preview_table,
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
    uploaded_file = st.file_uploader(
        "Upload applicant CSV (.csv)",
        type=["csv"],
        key="agent_uploader",
    )

    borrower_data = None
    if uploaded_file is not None:
        try:
            dataframe, missing_columns = load_uploaded_dataframe(uploaded_file)
            if missing_columns:
                render_error_banner(
                    f"Missing required columns: {', '.join(missing_columns)}"
                )
            else:
                st.success(f"File loaded: {len(dataframe)} rows, {len(dataframe.columns)} columns")
                render_preview_table(dataframe)
                borrower_data = dataframe.iloc[0].where(dataframe.iloc[0].notna(), None).to_dict()
                st.caption("Using the first uploaded row for report generation.")
        except Exception as exc:
            render_error_banner(str(exc))

    with st.expander("Enter borrower details manually"):
        manual_features = build_manual_feature_input()
        if borrower_data is None:
            borrower_data = manual_features

    if st.button("Generate Lending Report", type="primary", disabled=borrower_data is None):
        prediction = get_predictor().predict(borrower_data)
        st.session_state["agent_result"] = {
            "prediction": prediction,
            "state": _run_agent_with_progress(borrower_data, prediction),
        }

    result = st.session_state.get("agent_result")
    if not result:
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
    }[decision_action]
    st.markdown(
        f"""
        <div style="background:{decision_color};padding:16px;border-radius:12px;margin:12px 0;">
            <h3 style="margin:0;">{decision_action}</h3>
            <p style="margin:8px 0 0 0;">{decision.get('justification', 'No justification available.')}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Regulatory Sources", expanded=True):
        for source in report.get("sources", []):
            st.markdown(
                f"- **{source['title']}** | {source['section_id']} | relevance `{source['score']}`"
            )

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
