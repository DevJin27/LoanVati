"""Streamlit agent report tab."""

from __future__ import annotations

import time
import re

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


def _clean_prose(text: str) -> str:
    """Strip LLM formatting artifacts from plain-text responses.

    Llama 3.3 sometimes wraps the whole response in double-quotes or
    italic markers (*...*) which Streamlit's markdown engine renders as
    cursive text with collapsed word spaces.
    """
    text = text.strip()
    # Remove surrounding double or single quotes
    if (text.startswith('"') and text.endswith('"')) or (
        text.startswith("'") and text.endswith("'")
    ):
        text = text[1:-1].strip()
    # Remove wrapping * or ** (italic / bold)
    text = re.sub(r'^\*{1,2}(.+?)\*{1,2}$', r'\1', text, flags=re.DOTALL)
    return text.strip()


def _prose_html(text: str) -> str:
    """Render cleaned prose inside an explicit HTML paragraph so Streamlit
    cannot misinterpret the content as markdown italic / bold."""
    cleaned = _clean_prose(text)
    # Escape HTML special chars, then restore newlines as <br>
    import html
    safe = html.escape(cleaned).replace('\n', '<br>')
    return (
        f'<p style="font-size:0.97rem;line-height:1.75;'
        f'font-style:normal;font-weight:400;color:inherit;">'
        f'{safe}</p>'
    )


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
        st.markdown("### 🧑 Borrower Profile")
        profile_text = report.get("profile", state.get("borrower_summary", ""))
        st.markdown(_prose_html(profile_text), unsafe_allow_html=True)

    st.markdown("---")
    with st.container(border=True):
        st.markdown("### ⚠️ Risk Analysis")
        render_risk_badge(prediction["risk_class"])
        st.markdown("")
        analysis = report.get("risk_analysis", state.get("risk_analysis", ""))
        st.markdown(_prose_html(analysis), unsafe_allow_html=True)

    st.markdown("---")
    decision = report.get("decision", {})
    decision_action = decision.get("action", "MANUAL REVIEW")
    decision_icon = {"APPROVE": "✅", "REJECT": "❌", "MANUAL REVIEW": "🔎"}.get(decision_action, "🔎")
    decision_color = {
        "APPROVE": "#dcfce7",
        "REJECT": "#fee2e2",
        "MANUAL REVIEW": "#fef3c7",
    }.get(decision_action, "#fef3c7")
    decision_border = {
        "APPROVE": "#16a34a",
        "REJECT": "#dc2626",
        "MANUAL REVIEW": "#d97706",
    }.get(decision_action, "#d97706")
    st.markdown(
        f"""
        <div style="background:{decision_color};padding:20px 24px;border-radius:12px;margin:12px 0;
                    border-left:5px solid {decision_border};color:#1f2937;">
            <h3 style="margin:0 0 8px 0;color:#1f2937;">{decision_icon} {decision_action}</h3>
            <p style="margin:0;line-height:1.6;">{decision.get('justification', 'No justification available.')}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    with st.expander("📋 Regulatory Summary", expanded=True):
        if "regulatory_summary" in report and report["regulatory_summary"]:
            for point in report["regulatory_summary"]:
                st.markdown(f"• {point}")
        elif report.get("sources"):
            for source in report["sources"]:
                st.markdown(f"• **{source['title']}** (section `{source.get('section_id', 'N/A')}`) — relevance score `{source['score']:.3f}`")
        else:
            st.info("No regulatory context was retrieved for this profile.")

    st.markdown("---")
    disclaimer = report.get('disclaimer', 'AI-assisted recommendation. Not the sole basis for lending decisions.')
    st.caption(f"⚖️ {disclaimer}")

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
