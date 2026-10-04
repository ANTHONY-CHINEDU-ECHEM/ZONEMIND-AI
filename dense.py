"""Dense retrieval backends.

``LsaEmbedder`` is the default. It builds a TF IDF matrix over unigrams and bigrams and
projects it onto its leading singular vectors (latent semantic analysis). It needs no
model download, runs anywhere, and captures co occurrence structure that pure keyword
matching misses. ``SentenceTransformerEmbedder`` is a drop in replacement that uses a
neural encoder when the optional dependency and model weights are available.
"""
from __future__ import annotations

import numpy as np

from .text import tokenize, with_bigrams


def _normalise(m: np.ndarray) -> np.ndarray:
    return m / np.maximum(np.linalg.norm(m, axis=-1, keepdims=True), 1e-12)


class LsaEmbedder:
    def __init__(self, texts: list[str], dims: int = 48):
        docs = [with_bigrams(tokenize(t)) for t in texts]
        counts: dict[str, int] = {}
        for d in docs:
            for t in set(d):
                counts[t] = counts.get(t, 0) + 1
        # Terms seen in a single chunk carry no co occurrence signal for the projection.
        self.vocab = {t: i for i, t in enumerate(sorted(t for t, c in counts.items() if c >= 2))}
        df = np.array([counts[t] for t in self.vocab], dtype=float)
        self.idf = np.log((1.0 + len(docs)) / (1.0 + df)) + 1.0
        matrix = _normalise(np.vstack([self._tfidf(d) for d in docs]))
        u, s, vt = np.linalg.svd(matrix, full_matrices=False)
        k = min(dims, len(s))
        self.components = vt[:k].T
        self.doc_vectors = _normalise(u[:, :k] * s[:k])

    def _tfidf(self, tokens: list[str]) -> np.ndarray:
        vec = np.zeros(len(self.vocab))
        for t in tokens:
            idx = self.vocab.get(t)
            if idx is not None:
                vec[idx] += 1.0
        return np.where(vec > 0, 1.0 + np.log(np.maximum(vec, 1.0)), 0.0) * self.idf

    def scores(self, query: str) -> np.ndarray:
        q = self._tfidf(with_bigrams(tokenize(query))) @ self.components
        norm = np.linalg.norm(q)
        if norm < 1e-12:
            return np.zeros(self.doc_vectors.shape[0])
        return self.doc_vectors @ (q / norm)


class SentenceTransformerEmbedder:
    """Neural embeddings through the optional ``sentence_transformers`` package."""

    def __init__(self, texts: list[str], model_name: str):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("install the 'neural' extra to use sentence transformer embeddings") from exc
        self.model = SentenceTransformer(model_name)
        self.doc_vectors = _normalise(np.asarray(self.model.encode(texts, show_progress_bar=False)))
        self._cache: dict[str, np.ndarray] = {}

    def scores(self, query: str) -> np.ndarray:  # pragma: no cover - optional dependency
        if query not in self._cache:
            self._cache[query] = _normalise(np.asarray(self.model.encode([query]))[0])
        return self.doc_vectors @ self._cache[query]
