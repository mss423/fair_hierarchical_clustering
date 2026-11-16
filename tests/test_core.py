import copy
import numpy as np
import pytest
from fair_hc import (
    Tree,
    Node,
    make_fair,
    split_root,
    SplitInfeasible,
    average_linkage,
    similarities,
    star,
    evaluate,
)
from fair_hc.algorithm import validate_parameters
from fair_hc.operators import del_ins, shallow_fold, folding_groups, binarize
from fair_hc.reference import average_linkage_reference, pairwise_lca_cost
from fair_hc.tree import preorder
from fair_hc.data import synthetic


def clades(tree):
    return {
        frozenset(n.leaf_id for n in preorder(node) if n.is_leaf) for node in preorder(tree.root)
    }


def balanced(n, labels=None):
    nodes = [Node(i, leaf_id=i) for i in range(n)]
    ident = n
    while len(nodes) > 1:
        nxt = []
        for i in range(0, len(nodes) - 1, 2):
            nxt.append(Node(ident, children=nodes[i : i + 2]))
            ident += 1
        if len(nodes) % 2:
            nxt.append(nodes[-1])
        nodes = nxt
    return Tree(nodes[0], labels or [str(i % 2) for i in range(n)])


@pytest.mark.parametrize("n", [1, 2, 17, 31, 32, 33, 64, 127, 128, 257])
def test_transform_invariants_cost_immutability(n):
    data = synthetic(max(2, n), seed=4)
    labels = data.labels[:n]
    w = similarities(data.features[:n])
    initial = average_linkage(w, labels)
    before = initial.to_dict()
    a = make_fair(initial, labels, h=16, k=2, epsilon=1 / 64)
    b = make_fair(initial, labels, h=16, k=2, epsilon=1 / 64)
    assert a.tree.validate(final=True)
    assert a.tree.to_dict() == b.tree.to_dict()
    assert initial.to_dict() == before
    assert evaluate(a.tree, w, labels)["cost"] == pytest.approx(pairwise_lca_cost(a.tree, w))
    assert Tree.from_dict(a.tree.to_dict()).to_dict() == a.tree.to_dict()


@pytest.mark.parametrize("colors", [2, 3, 4])
@pytest.mark.parametrize("skewed", [False, True])
def test_multicolor_missing_local_colors(colors, skewed):
    d = synthetic(256, 7, colors=colors, skewed=skewed, correlated=True)
    t = average_linkage(similarities(d.features), d.labels)
    result = make_fair(t, d.labels, h=4 * 2**colors, k=2, epsilon=1 / (16 * 2**colors))
    assert result.tree.validate(final=True)
    assert result.tree.palette == t.palette
    assert all(len(n.counts) == colors for n in preorder(result.tree.root))


@pytest.mark.parametrize(
    "h,k,eps",
    [
        (4, 2, 0.01),
        (16, 1, 0.01),
        (9, 2, 0.01),
        (16, 2, 0),
        (16, 2, 1 / 16),
        (16, 2, float("nan")),
        (True, 2, 0.01),
    ],
)
def test_invalid_parameters(h, k, eps):
    with pytest.raises(ValueError):
        validate_parameters(h, k, eps, 2)


def test_hand_worked_move_and_fold():
    t = balanced(8)
    donor = t.root.children[0].children[1]
    recipient = t.root.children[1].children[0]
    del_ins(t, donor, recipient)
    assert t.validate()
    assert frozenset([2, 3, 4, 5]) in clades(t)
    group = list(t.root.children)
    folded = shallow_fold(t, group)
    # Folding all siblings creates a unary parent, an intermediate operator state.
    assert folded.size == 8
    assert sorted(n.leaf_id for n in preorder(folded) if n.is_leaf) == list(range(8))


def test_fold_groups_contiguous_chunks_not_adjacent_batches():
    nodes = [Node(i, leaf_id=i) for i in range(16)]
    groups = [Node(16 + i, children=nodes[2 * i : 2 * i + 2]) for i in range(8)]
    t = Tree(Node(24, children=groups), ["r"] * 8 + ["b"] * 8)
    ordered = sorted(groups, key=lambda c: (-c.counts[0] / c.size, c.minimum, c.id))
    result = folding_groups(t.root, 0, 2)
    assert result == [[ordered[i], ordered[i + 4]] for i in range(4)]
    for g in result:
        shallow_fold(t, g)
    assert len(t.root.children) == 4
    assert t.validate()
    assert all(c.size == 4 for c in t.root.children)


def test_split_and_integer_failures():
    t = balanced(64)
    out = split_root(t, h=16, epsilon=1 / 64)
    assert len(out.root.children) == 16
    assert all(3 <= c.size <= 5 for c in out.root.children)
    with pytest.raises(SplitInfeasible, match="integer_bounds"):
        split_root(balanced(33), h=16, epsilon=1 / 64)
    # Feasible rounded bounds do not imply that prescribed transfers can succeed.
    found = False
    for n in range(34, 70):
        try:
            split_root(balanced(n), h=16, epsilon=1 / 64)
        except SplitInfeasible as exc:
            found |= str(exc) == "prescribed_transfer_below_one_leaf"
    assert found


def test_skew_tree_iterative():
    n = 1500
    root = Node(0, leaf_id=0)
    for i in range(1, n):
        root = Node(n + i, children=[root, Node(i, leaf_id=i)])
    t = Tree(root, ["a" if i % 5 else "b" for i in range(n)])
    r = make_fair(t, t.labels, h=16, k=2, epsilon=1 / 64)
    assert r.tree.validate(final=True)
    assert t.copy().validate()


@pytest.mark.parametrize("kind", ["untied", "tied", "duplicates"])
def test_linkage_reference(kind):
    rng = np.random.default_rng(44)
    x = rng.normal(size=(14, 3))
    if kind == "tied":
        x = np.zeros((14, 3))
    if kind == "duplicates":
        x[4:] = x[:10]
    labels = ["a", "b"] * 7
    w = similarities(x)
    a, b = average_linkage(w, labels), average_linkage_reference(w, labels)
    assert a.validate() and b.validate()
    if kind == "untied":
        assert clades(a) == clades(b)
    for t in [a, b, star(labels)]:
        assert evaluate(t, w, labels)["cost"] == pytest.approx(pairwise_lca_cost(t, w))


def test_json_rejects_bad_structure_and_cache():
    t = balanced(8)
    d = t.to_dict()
    bad = copy.deepcopy(d)
    bad["nodes"][0]["children"].append(bad["root"])
    with pytest.raises(ValueError, match="Cycle"):
        Tree.from_dict(bad)
    bad = copy.deepcopy(d)
    bad["nodes"].append(bad["nodes"][0])
    with pytest.raises(ValueError, match="unique"):
        Tree.from_dict(bad)
    t.root.size += 1
    with pytest.raises(ValueError, match="metadata"):
        t.validate()


def test_bounds_and_structural_metrics():
    t = balanced(8, ["a"] * 4 + ["b"] * 4)
    w = np.ones((8, 8))
    result = evaluate(t, w, t.labels, bounds={"a": (0.25, 0.75)})
    assert result["cluster_count"] == 7
    assert result["bound_violation_clusters"] == 6
    assert result["max_representation_error"] == 0.5
    assert result["proportion_ranges"]["a"] == [0.0, 1.0]
    s = evaluate(star(t.labels), w, t.labels)
    assert s["cluster_count"] == 1 and s["terminal_sizes"] == [8]
    assert s["max_representation_error"] == 0
    assert s["cost"] == 8 * 28


def test_nonbinary_input():
    t = star(["a", "b"] * 32)
    b = t.copy()
    binarize(b, b.root)
    assert b.validate() and all(len(n.children) <= 2 for n in preorder(b.root))
    assert make_fair(t, t.labels, h=16, k=2, epsilon=1 / 64).tree.validate(final=True)
