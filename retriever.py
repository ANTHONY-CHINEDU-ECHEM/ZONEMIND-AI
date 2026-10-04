"""Hybrid retrieval with query decomposition and facet coverage fusion.

A control situation is rarely about one thing. At 14:00 on a hot working day the agent
needs the occupied comfort rules, the pre cooling sequence, the standby rule for an
empty zone and the critical event programme all at once. Sending that as one long query
lets the dominant topic crowd out the rest. The retriever therefore accepts one query
per facet, ranks each facet separately with reciprocal rank fusion of the lexical and
dense rankers, and then merges the facets so that every facet gets its best document
before any facet gets its second.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np

from .bm25 import BM25Index
from .dense import LsaEmbedder, SentenceTransformerEmbedder
from .loader import KnowledgeBase


@dataclass(frozen=True)
class Hit:
    doc_id: str
    score: float
    chunk_id: str
    text: str
    facet: str


class Retriever:
    def __init__(self, kb: KnowledgeBase, cfg):
        r = cfg.retrieval
        self.kb, self.mode, self.top_k, self.rrf_k, self.decompose = kb, r.mode, r.top_k, r.rrf_k, r.decompose
        texts = [c.text for c in kb.chunks]
        self.bm25 = BM25Index(texts)
        if r.dense_backend == "sentence_transformers":
            self.dense = SentenceTransformerEmbedder(texts, r.st_model)
        else:
            self.dense = LsaEmbedder(texts, r.dense_dims)
        self._cache: dict[tuple, list[Hit]] = {}
        self.calls = self.cache_hits = 0
        self.seconds = 0.0

    def _rankers(self, mode: str) -> list:
        if mode == "bm25":
            return [self.bm25]
        if mode == "dense":
            return [self.dense]
        return [self.bm25, self.dense]

    def _facet_scores(self, query: str, mode: str) -> np.ndarray:
        """Reciprocal rank fusion of the active rankers for one facet query."""
        fused = np.zeros(len(self.kb.chunks))
        for ranker in self._rankers(mode):
            scores = ranker.scores(query)
            order = np.argsort(-scores, kind="stable")
            ranks = np.empty(len(order))
            ranks[order] = np.arange(1, len(order) + 1)
            fused += np.where(scores > 0, 1.0 / (self.rrf_k + ranks), 0.0)
        return fused

    def search(self, facets: list[str], top_k: int | None = None, mode: str | None = None,
               decompose: bool | None = None) -> list[Hit]:
        mode = mode or self.mode
        top_k = top_k or self.top_k
        decompose = self.decompose if decompose is None else decompose
        if mode == "none" or not facets:
            return []
        key = (tuple(facets), top_k, mode, decompose)
        self.calls += 1
        if key in self._cache:
            self.cache_hits += 1
            return self._cache[key]
        start = time.perf_counter()
        queries = facets if decompose else [" ".join(facets)]

        # Best chunk per document within each facet, then coverage first merge across facets.
        candidates: list[tuple[int, float, str, int]] = []   # (rank in facet, score, facet, chunk index)
        for query in queries:
            fused = self._facet_scores(query, mode)
            seen: set[str] = set()
            rank = 0
            for idx in np.argsort(-fused, kind="stable"):
                if fused[idx] <= 0 or rank >= top_k:
                    break
                doc_id = self.kb.chunks[idx].doc_id
                if doc_id in seen:
                    continue
                seen.add(doc_id)
                candidates.append((rank, float(fused[idx]), query, int(idx)))
                rank += 1
        candidates.sort(key=lambda c: (c[0], -c[1]))
        hits, chosen = [], set()
        for _, score, facet, idx in candidates:
            chunk = self.kb.chunks[idx]
            if chunk.doc_id in chosen:
                continue
            chosen.add(chunk.doc_id)
            hits.append(Hit(chunk.doc_id, score, chunk.id, chunk.text, facet))
            if len(hits) >= top_k:
                break
        self._cache[key] = hits
        self.seconds += time.perf_counter() - start
        return hits
