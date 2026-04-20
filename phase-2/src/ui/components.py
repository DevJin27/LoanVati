"""Reusable Streamlit UI components for the Credit Risk AI application."""

from __future__ import annotations

import json
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

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


def load_eval_metrics() -> dict:
    """Load persisted evaluation metrics from disk."""
    metrics_path = PHASE_ROOT / "models" / "eval_metrics.json"
    return json.loads(metrics_path.read_text())


def build_manual_feature_input(prefix: str = "manual") -> dict:
    """Render structured controls and return borrower features."""
    import datetime

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Financial Profile")
        amt_income_total = st.number_input(
            "Annual Income", min_value=10_000.0, max_value=2_000_000.0, value=180_000.0, step=5000.0, key=f"{prefix}_amt_income"
        )
        amt_credit = st.number_input(
            "Requested Credit", min_value=10_000.0, max_value=5_000_000.0, value=500_000.0, step=10000.0, key=f"{prefix}_amt_credit"
        )
        amt_annuity = st.number_input(
            "Annuity", min_value=1_000.0, max_value=500_000.0, value=42_000.0, step=1000.0, key=f"{prefix}_amt_annuity"
        )
        name_income_type = st.selectbox(
            "Income Type",
            options=["Working", "State servant", "Commercial associate", "Pensioner", "Unemployed", "Student", "Businessman", "Maternity leave"],
            index=0,
            key=f"{prefix}_income_type",
        )
        years_employed = st.number_input(
            "Years Employed", min_value=0.0, max_value=50.0, value=5.0, step=0.5, key=f"{prefix}_years_employed"
        )

    with col2:
        st.subheader("Demographics")
        dob = st.date_input(
            "Date of Birth",
            value=datetime.date.today() - datetime.timedelta(days=12000),
            min_value=datetime.date.today() - datetime.timedelta(days=30000),
            max_value=datetime.date.today() - datetime.timedelta(days=6500),
            key=f"{prefix}_dob",
        )
        name_education_type = st.selectbox(
            "Education Type",
            options=["Secondary / secondary special", "Higher education", "Incomplete higher", "Lower secondary", "Academic degree"],
            index=1,
            key=f"{prefix}_education_type",
        )
        name_family_status = st.selectbox(
            "Family Status",
            options=["Single / not married", "Married", "Civil marriage", "Widow", "Separated", "Unknown"],
            index=1,
            key=f"{prefix}_family_status",
        )
        name_housing_type = st.selectbox(
            "Housing Type",
            options=["House / apartment", "Rented apartment", "With parents", "Municipal apartment", "Office apartment", "Co-op apartment"],
            index=0,
            key=f"{prefix}_housing_type",
        )
        cnt_fam_members = st.number_input(
            "Family Members", min_value=1, max_value=20, value=2, step=1, key=f"{prefix}_fam_members"
        )

    days_birth = (dob - datetime.date.today()).days
    days_employed = int(-years_employed * 365)

    return {
        "AMT_INCOME_TOTAL": float(amt_income_total),
        "AMT_CREDIT": float(amt_credit),
        "AMT_ANNUITY": float(amt_annuity),
        "CNT_FAM_MEMBERS": float(cnt_fam_members),
        "DAYS_BIRTH": float(days_birth),
        "DAYS_EMPLOYED": float(days_employed),
        "NAME_INCOME_TYPE": name_income_type.strip(),
        "NAME_EDUCATION_TYPE": name_education_type.strip(),
        "NAME_FAMILY_STATUS": name_family_status.strip(),
        "NAME_HOUSING_TYPE": name_housing_type.strip(),
    }
