"""Streamlit ML scoring tab."""

from __future__ import annotations

import time
n.
import plotly.graph_objects as go
import streamlit as st

from src.models.predict import CreditRiskPredictor
from src.preprocessing.dataset import PHASE_ROOT
from src.ui.components import (
    build_manual_feature_input,
    load_eval_metrics,
    render_confusion_matrix,
    render_feature_importance_chart,
    render_progress_steps,
    render_risk_badge,
    render_roc_curve,
)


@st.cache_resource
def get_predictor() -> CreditRiskPredictor:
    return CreditRiskPredictor(models_path=PHASE_ROOT / "models")


def _risk_score_gauge(score: float) -> go.Figure:
    figure = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"valueformat": ".2f"},
            gauge={
                "axis": {"range": [0, 1]},
                "bar": {"color": "#2563eb"},
                "steps": [
                    {"range": [0, 0.3], "color": "#dcfce7"},
                    {"range": [0.3, 0.6], "color": "#fef3c7"},
                    {"range": [0.6, 1.0], "color": "#fee2e2"},
                ],
            },
            title={"text": "Risk Score"},
        )
    )
    figure.update_layout(height=260, margin=dict(l=20, r=20, t=50, b=20))
    return figure


def render_ml_tab() -> None:
    """Render the ML scoring workflow."""
    st.subheader("Borrower Input")
    st.caption("Use sliders and textboxes to enter applicant details.")
    selected_features = build_manual_feature_input(prefix="ml")

    st.subheader("Run Prediction")
    if st.button("Analyse Credit Risk", type="primary"):
        progress_placeholder = st.empty()
        for index, step in enumerate(
            ["Loading model", "Running inference", "Computing SHAP"], start=1
        ):
            with progress_placeholder.container():
                render_progress_steps(
                    ["Loading model", "Running inference", "Computing SHAP"], index
                )
            time.sleep(0.2)

        try:
            st.session_state["ml_result"] = get_predictor().predict(selected_features)
        except FileNotFoundError as exc:
            progress_placeholder.empty()
            st.error(
                "Model artifacts are missing. Run `python src/models/train.py` to generate "
                "`rf_pipeline.joblib`, `preprocessor.joblib`, and `shap_explainer.joblib` in "
                "the models folder."
            )
            st.caption(f"Details: {exc}")
            return
        progress_placeholder.empty()

    result = st.session_state.get("ml_result")
    if result is None:
        return

    metrics = load_eval_metrics()
    st.subheader("Results Dashboard")
    col_score, col_class, col_conf = st.columns(3)
    with col_score:
        st.plotly_chart(_risk_score_gauge(result["risk_score"]), use_container_width=True)
    with col_class:
        st.markdown("#### Risk Class")
        render_risk_badge(result["risk_class"])
    with col_conf:
        st.markdown("#### Confidence")
        st.metric("Confidence", f"{result['confidence']:.2%}")
        interpretation = (
            "High confidence prediction"
            if result["confidence"] >= 0.75
            else "Moderate confidence prediction"
        )
        st.caption(interpretation)

    if "Uncertain" in result["risk_class"]:
        st.warning(
            "Borderline Case — This applicant is near the decision threshold. Manual review is recommended."
        )

    render_feature_importance_chart(result["top_features"])
    with st.expander("What does this mean?"):
        for feature in result["top_features"]:
            st.markdown(
                f"- `{feature['feature']}`: {feature['direction']} with SHAP {feature['shap_value']}"
            )

