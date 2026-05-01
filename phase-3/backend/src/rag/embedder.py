"""Keyword-based embedder using sklearn TF-IDF.

Replaces sentence-transformers (which requires PyTorch) to eliminate the
Apple Silicon segfault caused by PyToch multiprocessing semaphore cleanup
when the model is loaded inside a Streamlit process.

TF-IDF on the 8-document regulatory corpus is semantically sufficient:
the documents have rich, domain-specific vocabulary and the queries are
always short regulatory/credit-risk phrases.
"""

from __future__ import annotations

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


class DocumentEmbedder:
    """Fit a TF-IDF vectorizer once and expose the same embed() interface
    as the old SentenceTransformer wrapper so nothing else needs to change.
    """

    def __init__(self, corpus: list[str] | None = None) -> None:
        self._vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=1,
            analyzer="word",
        )
        if corpus:
            self._vectorizer.fit(corpus)
            self._fitted = True
        else:
            self._fitted = False

    def fit(self, corpus: list[str]) -> None:
        self._vectorizer.fit(corpus)
        self._fitted = True

    def embed(self, texts: list[str]) -> np.ndarray:
        """Return L2-normalised float32 TF-IDF vectors."""
        if not self._fitted:
            raise RuntimeError("DocumentEmbedder must be fitted before embed() is called")
        matrix = self._vectorizer.transform(texts).toarray().astype("float32")
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        return matrix / norms
