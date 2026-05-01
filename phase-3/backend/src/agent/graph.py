"""LangGraph wiring for the Credit Risk AI agent."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from src.agent.nodes import profile_node, rag_node, report_node, risk_node
from src.agent.state import AgentState


def build_agent_graph():
    """Create and compile the linear lending-decision graph."""
    graph = StateGraph(AgentState)
    graph.add_node("ProfileNode", profile_node)
    graph.add_node("RiskNode", risk_node)
    graph.add_node("RAGNode", rag_node)
    graph.add_node("ReportNode", report_node)

    graph.set_entry_point("ProfileNode")
    graph.add_edge("ProfileNode", "RiskNode")
    graph.add_edge("RiskNode", "RAGNode")
    graph.add_edge("RAGNode", "ReportNode")
    graph.add_edge("ReportNode", END)
    return graph.compile()


def run_agent(borrower_data: dict, ml_output: dict) -> dict:
    """Run the graph from borrower input plus ML inference output."""
    required_ml_keys = {"risk_score", "risk_class", "top_features"}
    if not borrower_data:
        raise ValueError("borrower_data is required")
    if not required_ml_keys.issubset(ml_output):
        raise ValueError(f"ml_output must include {sorted(required_ml_keys)}")

    app = build_agent_graph()
    initial_state: AgentState = {
        "borrower_data": borrower_data,
        "ml_risk_score": float(ml_output["risk_score"]),
        "risk_class": ml_output["risk_class"],
        "top_features": ml_output["top_features"],
        "borrower_summary": "",
        "risk_analysis": "",
        "retrieval_query": "",
        "retrieved_docs": [],
        "final_report": None,
        "error_flags": [],
        "processing_steps": [],
    }
    return app.invoke(initial_state)
