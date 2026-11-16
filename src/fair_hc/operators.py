"""In-place operators; the public transformation clones its input once."""
from .tree import key, postorder, preorder


def binarize(tree, root):
    """Deterministic pairwise refinement, with smaller child first."""
    for node in postorder(root):
        children = sorted(node.children, key=key)
        while len(children) > 2:
            new = []
            for i in range(0, len(children) - 1, 2):
                new.append(tree.new_node(children[i:i + 2]))
            if len(children) % 2:
                new.append(children[-1])
            children = sorted(new, key=key)
        node.children = children
        for c in children:
            c.parent = node
        tree.refresh(node)
    tree.update(root.parent)


def del_ins(tree, donor, recipient):
    """Move donor at recipient, contracting donor's binary parent.

    Recipient may be an empty placeholder. Donor and recipient must belong to
    disjoint subtrees. The hierarchy root itself cannot be moved/replaced.
    """
    if donor is recipient or donor.parent is None or recipient.parent is None:
        raise ValueError("Move requires distinct non-root subtrees")
    p = recipient
    while p is not None:
        if p is donor:
            raise ValueError("Cannot insert into donor descendant")
        p = p.parent
    p = donor
    while p is not None:
        if p is recipient:
            raise ValueError("Cannot insert into donor ancestor")
        p = p.parent
    parent = donor.parent
    if len(parent.children) != 2 or parent.parent is None:
        raise ValueError("Donor must have a non-root binary parent")
    sibling = next(c for c in parent.children if c is not donor)
    grand = parent.parent
    grand.children[grand.children.index(parent)] = sibling
    sibling.parent = grand
    parent.children = []
    parent.parent = None
    tree.update(grand, order=True)
    at = recipient.parent
    index = at.children.index(recipient)
    if recipient.size == 0:
        inserted = donor
        recipient.parent = None
    else:
        inserted = tree.new_node(sorted([recipient, donor], key=key))
    at.children[index] = inserted
    inserted.parent = at
    tree.update(at, order=True)
    return inserted


def folding_groups(root, color, k, *, rng=None):
    children = sorted(root.children, key=lambda c: (-c.counts[color] / c.size,
                                                   c.minimum, c.id))
    if len(children) % k:
        raise ValueError("Folding arity must be divisible by k")
    if rng is not None:
        rng.shuffle(children)
    width = len(children) // k
    return [[children[i + j * width] for j in range(k)] for i in range(width)]


def shallow_fold(tree, group):
    if len(group) < 2 or len(set(group)) != len(group):
        raise ValueError("Fold needs distinct siblings")
    parent = group[0].parent
    if parent is None or any(n.parent is not parent for n in group):
        raise ValueError("Fold needs siblings")
    children = []
    # A singleton root has no descendants: retain the point itself.
    for node in group:
        children.extend([node] if node.is_leaf else node.children)
    index = min(parent.children.index(n) for n in group)
    parent.children = [c for c in parent.children if c not in group]
    folded = tree.new_node(children)
    folded.parent = parent
    parent.children.insert(index, folded)
    for n in group:
        if not n.is_leaf:
            n.children = []
            n.parent = None
    binarize(tree, folded)
    tree.update(parent)
    return folded


def flatten(tree, node):
    if not node.is_leaf:
        leaves = sorted((n for n in preorder(node) if n.is_leaf), key=lambda n: n.leaf_id)
        node.children = leaves
        for leaf in leaves:
            leaf.parent = node
        tree.update(node)
