"""Intentionally slow independent references, only for small validation cases."""
import numpy as np
from .tree import Node, Tree, preorder


def pairwise_lca_cost(tree, w):
    leaves = {n.leaf_id: n for n in preorder(tree.root) if n.is_leaf}
    cost = 0.0
    for i in range(len(leaves)):
        for j in range(i + 1, len(leaves)):
            ancestors = set()
            current = leaves[i]
            while current is not None:
                ancestors.add(current)
                current = current.parent
            current = leaves[j]
            while current not in ancestors:
                current = current.parent
            # Count leaves independently of caches.
            size = sum(n.is_leaf for n in preorder(current))
            cost += w[i, j] * size
    return float(cost)


def average_linkage_reference(w, labels):
    active = [(Node(i, leaf_id=i), [i]) for i in range(len(labels))]
    ident = len(labels)
    while len(active) > 1:
        candidates = []
        for i in range(len(active)):
            for j in range(i + 1, len(active)):
                avg = np.mean([w[a, b] for a in active[i][1] for b in active[j][1]])
                candidates.append((-avg, i, j))
        _, i, j = min(candidates)
        a, b = active[i], active[j]
        node = Node(ident, children=[a[0], b[0]])
        ident += 1
        active = [v for t, v in enumerate(active) if t not in (i, j)]
        active.append((node, a[1] + b[1]))
    return Tree(active[0][0], labels)
