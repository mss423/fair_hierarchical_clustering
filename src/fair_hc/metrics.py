"""Pair-once Dasgupta cost and cluster-level descriptive measurements."""
import numpy as np
from .tree import preorder, postorder
from .geometry import validate_similarities


def traversal_index(tree):
    leaves, spans, depths = [], {}, {tree.root: 0}
    for node in preorder(tree.root):
        if node.is_leaf:
            spans[node] = (len(leaves), len(leaves) + 1)
            leaves.append(node.leaf_id)
        for child in node.children:
            depths[child] = depths[node] + 1
    for node in postorder(tree.root):
        if node.children:
            spans[node] = (spans[node.children[0]][0], spans[node.children[-1]][1])
    return np.asarray(leaves, dtype=np.intp), spans, depths


def _cross(w, left, right, block):
    result = 0.0
    for i in range(0, len(left), block):
        for j in range(0, len(right), block):
            result += float(w[np.ix_(left[i:i + block], right[j:j + block])].sum())
    return result


def dasgupta_cost(tree, w, *, block=256):
    if not isinstance(block, int) or block < 1:
        raise ValueError("block must be positive")
    order, spans, _ = traversal_index(tree)
    total = 0.0
    for node in postorder(tree.root):
        if not node.children:
            continue
        start, end = spans[node]
        if all(c.is_leaf for c in node.children):
            # A star: handle many leaf children in matrix blocks rather than
            # making a Python call for every singleton pair.
            rows = order[start:end]
            cross = 0.0
            for i in range(0, len(rows), block):
                a = rows[i:i + block]
                cross += float(np.triu(w[np.ix_(a, a)], k=1).sum())
                cross += _cross(w, a, rows[i + block:], block)
        else:
            cross = 0.0
            for child in node.children[:-1]:
                a, b = spans[child]
                cross += _cross(w, order[a:b], order[b:end], block)
        total += node.size * cross
    return total


def evaluate(tree, similarities, labels, *, bounds=None):
    """All nonsingleton clusters, including root; uncertainty belongs to runs.

    bounds is {color: (lower_proportion, upper_proportion)}, optionally partial.
    No asymptotic theorem constants are inferred.
    """
    tree.validate()
    if [str(x) for x in labels] != tree.labels:
        raise ValueError("Labels must match tree rows")
    w = validate_similarities(similarities, tree.root.size)
    bounds = {} if bounds is None else {str(k): v for k, v in bounds.items()}
    for c, (a, b) in bounds.items():
        if c not in tree.palette or not 0 <= a <= b <= 1:
            raise ValueError("Invalid color bounds")
    global_p = tree.root.counts / tree.root.size
    _, _, depths = traversal_index(tree)
    clusters, terminal_sizes = [], []
    for node in preorder(tree.root):
        if node.is_leaf:
            continue
        p = node.counts / node.size
        leaf_children = [c.is_leaf for c in node.children]
        terminal = all(leaf_children)
        if terminal:
            terminal_sizes.append(node.size)
        violations = [c for i, c in enumerate(tree.palette)
                      if c in bounds and not bounds[c][0] - 1e-12 <= p[i] <= bounds[c][1] + 1e-12]
        clusters.append({"id": node.id, "size": node.size, "depth": depths[node],
                         "arity": len(node.children), "counts": node.counts.tolist(),
                         "proportions": p.tolist(),
                         "representation_error": float(np.max(np.abs(p - global_p))),
                         "binary_balance": float(min(p) / max(p)) if len(p) == 2 else None,
                         "size_imbalance": max(abs(c.size / node.size - 1 / len(node.children))
                                               for c in node.children),
                         "terminal": terminal, "mixed_leaf_children": any(leaf_children) and not terminal,
                         "bound_violations": violations})
    proportions = np.asarray([c["proportions"] for c in clusters])
    summary = {"cost": dasgupta_cost(tree, w), "n": tree.root.size, "palette": tree.palette,
               "global_proportions": global_p.tolist(), "cluster_count": len(clusters),
               "depth": max(depths.values()), "terminal_sizes": terminal_sizes,
               "max_representation_error": max((c["representation_error"] for c in clusters), default=0),
               "max_size_imbalance": max((c["size_imbalance"] for c in clusters), default=0),
               "proportion_ranges": {c: [float(proportions[:, i].min()), float(proportions[:, i].max())]
                                     for i, c in enumerate(tree.palette)} if clusters else {},
               "min_binary_balance": min((c["binary_balance"] for c in clusters), default=None)
                                      if len(tree.palette) == 2 else None,
               "mixed_leaf_child_clusters": sum(c["mixed_leaf_children"] for c in clusters),
               "bound_violation_clusters": sum(bool(c["bound_violations"]) for c in clusters),
               "bounds": bounds}
    return {**summary, "clusters": clusters}
