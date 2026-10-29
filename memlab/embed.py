"""all-MiniLM-L6-v2 embeddings and cosine top-k.

This is the retriever behind the paper's strongest BEAM-100K baseline (all-turns, MiniLM, top-10).
The ONNX export through fastembed truncates at 256 word pieces, as sentence-transformers does, and
returns unit vectors, so a dot product is the cosine.
"""

import functools

import numpy as np

NAME = "sentence-transformers/all-MiniLM-L6-v2"


@functools.lru_cache(maxsize=1)
def _model():
    from fastembed import TextEmbedding
    return TextEmbedding(NAME)


def embed(texts):
    if not texts:
        return np.zeros((0, 384), dtype=np.float32)
    return np.array(list(_model().embed(list(texts), batch_size=64)), dtype=np.float32)


def top_k(query_vec, matrix, k):
    """Indices of the k rows of `matrix` closest to `query_vec`, best first. Ties keep row order."""
    if len(matrix) == 0:
        return []
    scores = matrix @ query_vec
    order = np.argsort(-scores, kind="stable")
    return [int(i) for i in order[:k]]
