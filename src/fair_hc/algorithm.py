"""Paper Algorithms 1–2, with documented finite-size terminal extensions."""
from dataclasses import dataclass
import math
import numpy as np
from .tree import key
from .operators import binarize, del_ins, flatten, folding_groups, shallow_fold


class SplitInfeasible(ValueError):
    """The prescribed integer split cannot proceed."""


def validate_parameters(h, k, epsilon, colors):
    if isinstance(h, bool) or not isinstance(h, int) or h < 2:
        raise ValueError("h must be an integer >= 2")
    if isinstance(k, bool) or not isinstance(k, int) or k < 2:
        raise ValueError("k must be an integer >= 2")
    if h % k ** colors or h // k ** colors < 2:
        raise ValueError("Require h divisible by k^lambda and h/k^lambda >= 2")
    if not 0 < epsilon < min(1 / 6, 1 / h):
        raise ValueError("Require 0 < epsilon < min(1/6, 1/h)")


def imbalance(node):
    return max((abs(c.size / node.size - 1 / len(node.children))
                for c in node.children), default=0.0)


def _split(tree, root, h, epsilon, emit):
    n = root.size
    low, high = n * (1 / h - epsilon), n * (1 / h + epsilon)
    lo, hi = math.ceil(low - 1e-12), math.floor(high + 1e-12)
    if h > n or h * lo > n or h * hi < n or lo > hi:
        raise SplitInfeasible("integer_bounds_infeasible")
    if n < 1 / (2 * epsilon):
        raise SplitInfeasible("below_paper_size_threshold")
    binarize(tree, root)
    while len(root.children) < h:
        dummy = tree.new_node()
        dummy.parent = root
        root.children.append(dummy)
    while True:
        small = min(root.children, key=key)
        large = max(root.children, key=key)
        if small.size >= low - 1e-12 and large.size <= high + 1e-12:
            break
        budget = min(n / h - small.size, large.size - n / h)
        if budget < 1 - 1e-12:
            raise SplitInfeasible("prescribed_transfer_below_one_leaf")
        donor = large
        while donor.size > budget + 1e-12:
            donor = donor.children[-1]
        recipient = small
        while recipient.children and recipient.children[-1].size >= donor.size:
            recipient = recipient.children[0]
        moved = donor.size
        donor_id, recipient_id = donor.id, recipient.id
        del_ins(tree, donor, recipient)
        emit("move", root=root.id, donor=donor_id, recipient=recipient_id, leaves=moved)
    emit("split", root=root.id, sizes=[c.size for c in root.children],
         imbalance=imbalance(root))


def split_root(tree, *, h, epsilon):
    """Return a new tree with h balanced root children, or raise SplitInfeasible."""
    if not isinstance(h, int) or isinstance(h, bool) or h < 2:
        raise ValueError("h must be an integer >= 2")
    if not 0 < epsilon < min(1 / 6, 1 / h):
        raise ValueError("Invalid epsilon")
    tree.validate()
    out = tree.copy()
    _split(out, out.root, h, epsilon, lambda *a, **kw: None)
    out.validate()
    return out


@dataclass
class FairResult:
    tree: object
    diagnostics: dict
    trace: list | None

    def __iter__(self):
        yield self.tree
        yield self.diagnostics
        yield self.trace


def make_fair(tree, labels, *, h, k, epsilon, trace=False):
    return transform(tree, labels, h=h, k=k, epsilon=epsilon, trace=trace)


def transform(tree, labels, *, h, k, epsilon, trace=False, folding="density", seed=0):
    """Internal common path for MakeFair and its two controlled ablations."""
    tree.validate()
    labels = [str(x) for x in labels]
    if labels != tree.labels:
        raise ValueError("Labels must match tree rows")
    validate_parameters(h, k, epsilon, len(tree.palette))
    if folding not in {"density", "random", "none"}:
        raise ValueError("Unknown folding policy")
    out = tree.copy()
    diagnostics = {"parameters": {"h": h, "k": k, "epsilon": epsilon,
                                  "palette": out.palette, "folding": folding},
                   "operations": {}, "terminal_cases": [], "splits": [], "folds": []}
    events = [] if trace else None

    def emit(operation, **details):
        counts = diagnostics["operations"]
        counts[operation] = counts.get(operation, 0) + 1
        if operation in {"split", "fold"}:
            diagnostics[operation + "s"].append(details)
        if trace:
            snapshot = out.to_dict()
            # Empty placeholders carry no data and are not hierarchy clusters.
            empty = {n['id'] for n in snapshot['nodes']
                     if n['leaf_id'] is None and not n['children']}
            snapshot['nodes'] = [n for n in snapshot['nodes'] if n['id'] not in empty]
            for n in snapshot['nodes']:
                n['children'] = [i for i in n['children'] if i not in empty]
            events.append({"operation": operation, **details, "tree": snapshot})

    emit("start")
    rng = np.random.default_rng(seed)
    stack = [out.root]
    threshold = max(h, 1 / (2 * epsilon))
    while stack:
        root = stack.pop()
        if root.is_leaf:
            continue
        reason = None
        if root.size < threshold:
            reason = "below_paper_size_threshold"
        else:
            try:
                _split(out, root, h, epsilon, emit)
            except SplitInfeasible as exc:
                reason = str(exc)
        if reason:
            flatten(out, root)
            diagnostics["terminal_cases"].append({"node": root.id, "size": root.size,
                                                  "reason": reason})
            emit("terminal", root=root.id, reason=reason)
            continue
        if folding != "none":
            for color in range(len(out.palette)):
                groups = folding_groups(root, color, k, rng=rng if folding == "random" else None)
                ids = [[n.id for n in group] for group in groups]
                new_ids = []
                for group in groups:
                    new_ids.append(shallow_fold(out, group).id)
                emit("fold", root=root.id, color=out.palette[color], groups=ids,
                     folded=new_ids, sizes=[c.size for c in root.children],
                     imbalance=imbalance(root))
        if any(c.is_leaf for c in root.children) and not all(c.is_leaf for c in root.children):
            # Only the splitting-only control can expose singleton children.
            flatten(out, root)
            reason = 'mixed_leaf_children_in_splitting_ablation'
            diagnostics['terminal_cases'].append({'node': root.id, 'size': root.size,
                                                   'reason': reason})
            emit('terminal', root=root.id, reason=reason)
            continue
        # Threshold is evaluated on each queued child, never on its parent.
        stack.extend(reversed(root.children))
    out.validate(final=True)
    emit("finish")
    return FairResult(out, diagnostics, events)
