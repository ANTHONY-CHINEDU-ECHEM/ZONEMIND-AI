"""Okapi BM25 lexical ranking, implemented with dense numpy arrays.

The corpus is small (operational documents, not the open web), so the full weight
matrix fits comfortably in memory and a query is a single column gather and sum.
"""
from __future__ import annotations

import numpy as np

from .text import tokenize


class BM25Index:
    def __init__(self, texts: list[str], k1: float = 1.5, b: float = 0.75):
        docs = [tokenize(t) for t in texts]
        self.vocab = {t: i for i, t in enumerate(sorted({t for d in docs for t in d}))}
        tf = np.zeros((len(docs), len(self.vocab)))
        for row, tokens in enumerate(docs):
            for t in tokens:
                tf[row, self.vocab[t]] += 1.0
        length = tf.sum(axis=1, keepdims=True)
        df = (tf > 0).sum(axis=0)
        idf = np.log(1.0 + (len(docs) - df + 0.5) / (df + 0.5))
        norm = tf + k1 * (1.0 - b + b * length / length.mean())
        self.weights = idf * tf * (k1 + 1.0) / norm

    def scores(self, query: str) -> np.ndarray:
        cols = [self.vocab[t] for t in tokenize(query) if t in self.vocab]
        if not cols:
            return np.zeros(self.weights.shape[0])
        return self.weights[:, cols].sum(axis=1)
