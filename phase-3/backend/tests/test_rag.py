"""Retrieval tests for the regulatory RAG layer."""

from __future__ import annotations

from src.rag.retriever import FAISSRetriever


def test_retrieval_returns_relevant_docs() -> None:
    retriever = FAISSRetriever()
    results = retriever.query("loan default probability credit appraisal", top_k=3)
    assert len(results) >= 1
    assert all("content" in item and "source_name" in item and "score" in item for item in results)


def test_deduplication() -> None:
    retriever = FAISSRetriever()
    results = retriever.query("NPA classification", top_k=5)
    source_ids = [(item["source_name"], item["section_id"]) for item in results]
    assert len(source_ids) == len(set(source_ids))


def test_low_similarity_filtered() -> None:
    retriever = FAISSRetriever()
    results = retriever.query(
        "completely unrelated query xyzzy 12345", top_k=3, min_score=0.4
    )
    assert all(item["score"] >= 0.4 for item in results)
