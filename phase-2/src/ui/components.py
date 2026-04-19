"""Reusable Streamlit UI components for the Credit Risk AI application."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.api.schemas import REQUIRED_FEATURES
from src.preprocessing.dataset import PHASE_ROOT


def render_risk_badge(risk_class: str) -> None:
    """Render a color-coded risk badge."""
    colors = {"Low": "#22c55e", "Medium": "#f59e0b", "High": "#ef4444"}
    color = colors.get(risk_class.split("—")[0].strip(), "#6b7280")
    st.markdown(
        f"""
        <span style="background:{color};color:white;padding:4px 12px;border-radius:12px;
        font-weight:600;font-size:0.9rem">{risk_class}</span>
        """,
        unsafe_allow_html=True,
    )


def render_progress_steps(steps: list[str], current: int) -> None:
    """Render a simple horizontal step progress indicator."""
    columns = st.columns(len(steps))
    for index, (column, step) in enumerate(zip(columns, steps), start=1):
        if index < current:
            label = f"✅ {step}"
        elif index == current:
            label = f"⏳ {step}"
        else:
            label = f"⬜ {step}"
        column.markdown(label)


def render_error_banner(message: str) -> None:
    """Display a consistent user-facing error banner."""
    st.error(f"Warning: {message}")


def render_feature_importance_chart(top_features: list[dict]) -> None:
    """Plot a horizontal SHAP bar chart with risk direction colors."""
    if not top_features:
        st.info("No feature importance data available.")
        return

    names = [item["feature"] for item in top_features][::-1]
    values = [item["shap_value"] for item in top_features][::-1]
    colors = ["#ef4444" if value >= 0 else "#22c55e" for value in values]
    directions = [item["direction"] for item in top_features][::-1]

    figure = go.Figure(
        go.Bar(
            x=values,
            y=names,
            orientation="h",
            marker_color=colors,
            customdata=directions,
            hovertemplate="%{y}<br>SHAP=%{x}<br>%{customdata}<extra></extra>",
        )
    )
    figure.update_layout(
        title="Top Risk Drivers",
        margin=dict(l=20, r=20, t=50, b=20),
        height=320,
    )
    st.plotly_chart(figure, use_container_width=True)


def render_confusion_matrix(cm: list[list], labels: list[str]) -> None:
    """Render an annotated confusion matrix heatmap."""
    figure = go.Figure(
        data=go.Heatmap(
            z=cm,
            x=labels,
            y=labels,
            text=cm,
            texttemplate="%{text}",
            colorscale="Blues",
        )
    )
    figure.update_layout(title="Confusion Matrix", xaxis_title="Predicted", yaxis_title="Actual")
    st.plotly_chart(figure, use_container_width=True)


def render_roc_curve(fpr: list, tpr: list, auc_score: float) -> None:
    """Render the ROC curve with the reference diagonal."""
    figure = go.Figure()
    figure.add_trace(go.Scatter(x=fpr, y=tpr, mode="lines", name=f"AUC = {auc_score:.3f}"))
    figure.add_trace(
        go.Scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(dash="dash"), name="Baseline")
    )
    figure.update_layout(
        title="ROC Curve",
        xaxis_title="False Positive Rate",
        yaxis_title="True Positive Rate",
    )
    st.plotly_chart(figure, use_container_width=True)


def load_uploaded_dataframe(uploaded_file) -> tuple[pd.DataFrame | None, list[str]]:
    """Load a CSV upload and return any missing required columns."""
    if uploaded_file is None:
        return None, []
    if not uploaded_file.name.lower().endswith(".csv"):
        raise ValueError("Only CSV files are supported.")

    dataframe = pd.read_csv(uploaded_file)
    missing = [column for column in REQUIRED_FEATURES if column not in dataframe.columns]
    return dataframe, missing


def render_preview_table(dataframe: pd.DataFrame) -> None:
    """Display a trimmed preview of the uploaded data."""
    preview = dataframe.head(5).copy()
    preview.columns = [column[:24] for column in preview.columns]
    st.dataframe(preview, use_container_width=True)


def load_eval_metrics() -> dict:
    """Load persisted evaluation metrics from disk."""
    metrics_path = PHASE_ROOT / "models" / "eval_metrics.json"
    return json.loads(metrics_path.read_text())


def build_manual_feature_input() -> dict:
    """Render a compact manual entry form and return borrower features."""
    return {
        "AMT_INCOME_TOTAL": st.number_input("Annual Income", min_value=1.0, value=180000.0),
        "AMT_CREDIT": st.number_input("Requested Credit", min_value=1.0, value=500000.0),
        "AMT_ANNUITY": st.number_input("Annuity", min_value=1.0, value=42000.0),
        "CNT_FAM_MEMBERS": st.number_input("Family Members", min_value=1.0, value=2.0),
        "DAYS_BIRTH": st.number_input("Days Since Birth", value=-12000.0),
        "DAYS_EMPLOYED": st.number_input("Days Employed", value=-2500.0),
        "NAME_INCOME_TYPE": st.selectbox(
            "Income Type",
            ["Working", "Commercial associate", "State servant", "Pensioner"],
        ),
        "NAME_EDUCATION_TYPE": st.selectbox(
            "Education Type",
            ["Higher education", "Secondary / secondary special", "Incomplete higher"],
        ),
        "NAME_FAMILY_STATUS": st.selectbox(
            "Family Status",
            ["Married", "Single / not married", "Civil marriage"],
        ),
        "NAME_HOUSING_TYPE": st.selectbox(
            "Housing Type",
            ["House / apartment", "With parents", "Rented apartment"],
        ),
    }
