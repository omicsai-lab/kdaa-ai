"""Injectable embedding backend for C0-S (Freeze Section 10, C0-S).

The final embedding model is explicitly not locked at this stage (WP4/Checkpoint A
guardrail). ``EmbeddingBackend`` is a narrow protocol so the actual backend can be swapped
without touching C0-S's ranking logic:

- ``FakeEmbeddingBackend`` -- deterministic, dependency-free bag-of-words vectors, for
  tests, so test runtime and behavior never depend on scikit-learn internals.
- ``TfidfEmbeddingBackend`` -- the development-pilot default: local, already-installed
  (scikit-learn is an existing project dependency), fully reproducible TF-IDF vectors
  fit per call. This is the "clearly documented lexical/TF-IDF semantic fallback"
  Checkpoint A calls for rather than installing a new large dependency to obtain a
  particular sentence-embedding model.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Protocol

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_PATTERN.findall(text.lower())


class EmbeddingBackend(Protocol):
    def embed_many(self, texts: list[str]) -> list[list[float]]:
        """Return one fixed-length vector per input text, in the same order."""
        ...


class FakeEmbeddingBackend:
    """Deterministic bag-of-words vectors with no ML dependency. For tests."""

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        tokenized = [_tokenize(text) for text in texts]
        vocab = sorted({token for tokens in tokenized for token in tokens})
        if not vocab:
            return [[0.0] for _ in texts]
        vectors = []
        for tokens in tokenized:
            counts = Counter(tokens)
            vectors.append([float(counts.get(term, 0)) for term in vocab])
        return vectors


class TfidfEmbeddingBackend:
    """Local TF-IDF vectors (scikit-learn, an existing project dependency). A fresh
    vectorizer is fit per call, over exactly the batch of texts being compared, so
    results are fully deterministic and require no external model download.
    """

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        from sklearn.feature_extraction.text import TfidfVectorizer

        vectorizer = TfidfVectorizer(lowercase=True, stop_words="english")
        try:
            matrix = vectorizer.fit_transform(texts)
        except ValueError:
            # Empty vocabulary (e.g. every text is empty or all-stopwords).
            return [[0.0] for _ in texts]
        return matrix.toarray().tolist()


def cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    """Pure-Python cosine similarity, safe for zero vectors (returns 0.0)."""
    if len(vector_a) != len(vector_b):
        raise ValueError("Vectors must have the same length to compare")
    dot = sum(a * b for a, b in zip(vector_a, vector_b, strict=True))
    norm_a = sum(a * a for a in vector_a) ** 0.5
    norm_b = sum(b * b for b in vector_b) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
