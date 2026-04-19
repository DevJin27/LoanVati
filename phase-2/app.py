"""Streamlit entry point for Credit Risk AI v2.0."""

from __future__ import annotations

from dotenv import load_dotenv
import streamlit as st

load_dotenv()

st.set_page_config(
    page_title="Credit Risk AI — Intelligent Lending Decisions",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

with st.sidebar:
    st.title("🏦 Credit Risk AI")
    st.markdown("**v2.0** | Built on Home Credit Dataset")
    st.markdown("---")
    st.caption("For demonstration and research purposes only.")

st.title("🏦 Credit Risk AI")
st.markdown("*Intelligent lending decisions powered by ML + agentic AI reasoning*")

tab1, tab2 = st.tabs(["📊 ML Risk Scoring", "🤖 AI Lending Report"])

with tab1:
    from src.ui.ml_tab import render_ml_tab

    render_ml_tab()

with tab2:
    from src.ui.agent_tab import render_agent_tab

    render_agent_tab()
