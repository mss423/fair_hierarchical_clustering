"""Runnable adapter: deterministic random binary hierarchy, independent of colors."""

import numpy as np
from fair_hc import Node, Tree


def cluster(dataset, seed, parameters, starting_tree=None):
    rng = np.random.default_rng(seed)
    nodes = [Node(i, leaf_id=i) for i in rng.permutation(len(dataset.labels)).tolist()]
    ident = len(nodes)
    while len(nodes) > 1:
        next_level = []
        for i in range(0, len(nodes) - 1, 2):
            next_level.append(Node(ident, children=nodes[i : i + 2]))
            ident += 1
        if len(nodes) % 2:
            next_level.append(nodes[-1])
        nodes = next_level
    return Tree(nodes[0], dataset.labels)


if __name__ == "__main__":
    from fair_hc.data import synthetic
    from fair_hc.adapters import default_parameters

    data = synthetic(32)
    tree = cluster(data, 0, default_parameters(data.labels))
    tree.validate()
    print("Custom hierarchy:", tree.root.size, "leaves")
