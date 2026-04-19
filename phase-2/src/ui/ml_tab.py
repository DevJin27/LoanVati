"""Streamlit ML scoring tab."""

from __future__ import annotations

import time

import plotly.graph_objects as go
import streamlit as st

from src.models.predict import CreditRiskPredictor
from src.preprocessing.dataset import PHASE_ROOT
from src.ui.components import (
    load_eval_metrics,
    load_uploaded_dataframe,
    render_confusion_matrix,
    render_error_banner,
    render_feature_importance_chart,
    render_preview_table,
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
    st.subheader("Upload and Validate")
    uploaded_file = st.file_uploader(
        "Upload applicant data (.csv)",
        type=["csv"],
        key="ml_uploader",
    )

    dataframe = None
    selected_features = None
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
                selected_features = dataframe.iloc[0].where(dataframe.iloc[0].notna(), None).to_dict()
                st.caption("Using the first row for scoring in this interactive view.")
        except Exception as exc:
            render_error_banner(str(exc))

    st.subheader("Run Prediction")
    if st.button("Analyse Credit Risk", type="primary", disabled=selected_features is None):
        progress_placeholder = st.empty()
        for index, step in enumerate(
            ["Loading model", "Running inference", "Computing SHAP"], start=1
        ):
            with progress_placeholder.container():
                render_progress_steps(
                    ["Loading model", "Running inference", "Computing SHAP"], index
                )
            time.sleep(0.2)

        st.session_state["ml_result"] = get_predictor().predict(selected_features)
        progress_placeholder.empty()

    result = st.session_state.get("ml_result")
    if not result:
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

    matrix_col, roc_col = st.columns(2)
    with matrix_col:
        render_confusion_matrix(metrics["rf_confusion_matrix"], ["Negative", "Positive"])
    with roc_col:
        render_roc_curve(
            metrics["rf_roc_curve"]["fpr"],
            metrics["rf_roc_curve"]["tpr"],
            metrics["rf_roc_auc"],
        )
