"""TF-IDF based regulatory retriever — no FAISS, no PyTorch.

Replaces the FAISS + SentenceTransformer stack that caused a segfault on
Apple Silicon (PyTorch 2.x multiprocessing semaphore cleanup race with
Streamlit).  Because our corpus is only 8 documents, a brute-force numpy
cosine similarity search is faster than FAISS with no quality loss.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from src.preprocessing.dataset import PHASE_ROOT
from src.rag.embedder import DocumentEmbedder


class FAISSRetriever:
    """Drop-in replacement for the old FAISS retriever.

    Uses TF-IDF + cosine similarity instead of FAISS + sentence-transformers,
    with the exact same query() interface so no calling code needs to change.
    """

    def __init__(
        self,
        index_path: str | Path | None = None,   # kept for API compat, unused
        metadata_path: str | Path = PHASE_ROOT / "rag" / "metadata.json",
    ) -> None:
        self.metadata: list[dict] = json.loads(Path(metadata_path).read_text())

        # Build the corpus from document content
        corpus = [item["content"] for item in self.metadata]

        # Fit the TF-IDF embedder on the full corpus once
        self.embedder = DocumentEmbedder(corpus=corpus)

        # Pre-compute and store all document vectors
        self._doc_vectors: np.ndarray = self.embedder.embed(corpus)

    @staticmethod
    def _cosine_similarity(query_vec: np.ndarray, doc_matrix: np.ndarray) -> np.ndarray:
        """Return cosine similarity scores between one query and all docs."""
        # Both query_vec and doc_matrix rows are already L2-normalised
        return doc_matrix @ query_vec.T  # shape: (n_docs,)

    def query(
        self, query_text: str, top_k: int = 3, min_score: float = 0.05
    ) -> list[dict]:
        """Return the best matching, deduplicated chunks above the score floor."""
        query_vec = self.embedder.embed([query_text])  # shape: (1, n_features)
        scores = self._cosine_similarity(query_vec[0], self._doc_vectors)

        # Sort descending by score
        ranked_indices = np.argsort(scores)[::-1]

        results: list[dict] = []
        seen_sources: set[tuple[str, str]] = set()

        for idx in ranked_indices:
            item = dict(self.metadata[idx])
            item["score"] = round(float(scores[idx]), 4)
            source_key = (item["source_name"], item["section_id"])

            if item["score"] < min_score or source_key in seen_sources:
                continue

            seen_sources.add(source_key)
            results.append(item)
            if len(results) == top_k:
                break

        return results
