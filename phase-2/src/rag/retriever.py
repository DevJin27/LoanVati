"""FAISS-based regulatory retrieval wrapper."""

from __future__ import annotations

import json
from pathlib import Path

import faiss

from src.preprocessing.dataset import PHASE_ROOT
from src.rag.embedder import DocumentEmbedder


class FAISSRetriever:
    """Load the FAISS index and return filtered, deduplicated document chunks."""

    def __init__(
        self,
        index_path: str | Path = PHASE_ROOT / "rag" / "faiss_index.bin",
        metadata_path: str | Path = PHASE_ROOT / "rag" / "metadata.json",
    ) -> None:
        self.index_path = Path(index_path)
        self.metadata_path = Path(metadata_path)
        if not self.index_path.exists() or not self.metadata_path.exists():
            import sys as _sys
            _project_root = str(PHASE_ROOT)
            if _project_root not in _sys.path:
                _sys.path.insert(0, _project_root)
            from rag.build_index import build_index

            build_index()
        self.index = faiss.read_index(str(self.index_path))
        self.metadata = json.loads(self.metadata_path.read_text())
        self.embedder = DocumentEmbedder()

    @staticmethod
    def _distance_to_score(distance: float) -> float:
        """Convert normalized L2 distance to an easy-to-interpret similarity score."""
        return float(1.0 / (1.0 + distance))

    def query(
        self, query_text: str, top_k: int = 3, min_score: float = 0.4
    ) -> list[dict]:
        """Return the best matching, deduplicated chunks above the score threshold."""
        query_vector = self.embedder.embed([query_text])
        search_size = min(max(top_k * 4, 10), len(self.metadata))
        distances, indices = self.index.search(query_vector, search_size)

        results: list[dict] = []
        seen_sources: set[tuple[str, str]] = set()

        for distance, index in zip(distances[0], indices[0]):
            if index == -1:
                continue
            item = dict(self.metadata[index])
            item["score"] = round(self._distance_to_score(float(distance)), 4)
            source_key = (item["source_name"], item["section_id"])

            if item["score"] < min_score or source_key in seen_sources:
                continue

            seen_sources.add(source_key)
            results.append(item)
            if len(results) == top_k:
                break

        return results
