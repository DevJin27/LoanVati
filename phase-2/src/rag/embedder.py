"""Sentence-transformers wrapper used for regulatory document embeddings."""

from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer


class DocumentEmbedder:
    """Load and reuse the configured sentence-transformer model."""

    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

    def __init__(self) -> None:
        self.model = SentenceTransformer(self.MODEL_NAME)

    def embed(self, texts: list[str]) -> np.ndarray:
        """Encode texts as normalized float32 vectors."""
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(embeddings, dtype="float32")
