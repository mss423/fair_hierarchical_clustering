"""Compiled numerical geometry; average linkage of 1 - similarity."""
import numpy as np
from scipy.spatial.distance import pdist, squareform
from scipy.cluster.hierarchy import linkage
from .tree import from_linkage, star


def similarities(features):
    x = np.asarray(features, dtype=np.float64)
    if x.ndim != 2 or not len(x) or not np.isfinite(x).all():
        raise ValueError("Features must be a nonempty finite matrix")
    condensed = pdist(x, metric="euclidean")
    condensed += 1
    np.reciprocal(condensed, out=condensed)
    w = squareform(condensed)
    np.fill_diagonal(w, 1)
    return w


def validate_similarities(w, n, block=256):
    w = np.asarray(w)
    if w.shape != (n, n):
        raise ValueError("Similarity matrix shape does not match leaves")
    for i in range(0, n, block):
        part = w[i:i + block]
        if not np.isfinite(part).all() or (part < 0).any():
            raise ValueError("Similarities must be finite and nonnegative")
        if not np.allclose(part, w[:, i:i + block].T, atol=1e-12, rtol=1e-12):
            raise ValueError("Similarities must be symmetric")
    return w


def average_linkage(w, labels):
    w = validate_similarities(w, len(labels))
    if np.max(w) > 1 + 1e-12:
        raise ValueError("Average linkage on 1 - similarity requires similarities <= 1")
    if len(labels) == 1:
        return star(labels)
    distances = squareform(w, checks=False)
    np.subtract(1, distances, out=distances)
    np.maximum(distances, 0, out=distances)
    return from_linkage(linkage(distances, method="average"), labels)
