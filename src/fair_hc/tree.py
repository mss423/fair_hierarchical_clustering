"""Mutable nonbinary trees. Leaf IDs are matrix row numbers; node IDs are stable."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import numpy as np


@dataclass(eq=False)
class Node:
    id: int
    leaf_id: int | None = None
    children: list[Node] = field(default_factory=list)
    parent: Node | None = field(default=None, repr=False)
    size: int = 0
    counts: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.int64), repr=False)
    minimum: int = -1

    @property
    def is_leaf(self):
        return self.leaf_id is not None


def preorder(root):
    stack = [root]
    while stack:
        node = stack.pop()
        yield node
        stack.extend(reversed(node.children))


def postorder(root):
    stack = [(root, False)]
    while stack:
        node, visited = stack.pop()
        if visited:
            yield node
        else:
            stack.append((node, True))
            stack.extend((c, False) for c in reversed(node.children))


def key(node):
    return node.size, node.minimum, node.id


class Tree:
    def __init__(self, root: Node, labels):
        self.root = root
        self.labels = [str(x) for x in labels]
        self.palette = sorted(set(self.labels))
        self._colors = {c: i for i, c in enumerate(self.palette)}
        self.next_id = max(n.id for n in preorder(root)) + 1
        self.rebuild()

    def refresh(self, node):
        if node.is_leaf:
            node.size = 1
            node.minimum = node.leaf_id
            node.counts = np.zeros(len(self.palette), dtype=np.int64)
            node.counts[self._colors[self.labels[node.leaf_id]]] = 1
        else:
            node.size = sum(c.size for c in node.children)
            node.minimum = min((c.minimum for c in node.children), default=len(self.labels))
            node.counts = sum((c.counts for c in node.children),
                              start=np.zeros(len(self.palette), dtype=np.int64))

    def rebuild(self):
        self.root.parent = None
        for node in postorder(self.root):
            for child in node.children:
                child.parent = node
            self.refresh(node)

    def update(self, node, *, order=False):
        while node is not None:
            self.refresh(node)
            if order:
                node.children.sort(key=key)
            node = node.parent

    def new_node(self, children=()):
        node = Node(self.next_id, children=list(children))
        self.next_id += 1
        for c in node.children:
            c.parent = node
        self.refresh(node)
        return node

    def copy(self):
        return Tree.from_dict(self.to_dict())

    def to_dict(self):
        return {"schema": "fair-hc.tree", "version": 1, "root": self.root.id,
                "labels": self.labels, "palette": self.palette,
                "nodes": [{"id": n.id, "leaf_id": n.leaf_id,
                           "children": [c.id for c in n.children]} for n in preorder(self.root)]}

    def save(self, path):
        Path(path).write_text(json.dumps(self.to_dict(), separators=(",", ":")) + "\n")

    @classmethod
    def load(cls, path):
        return cls.from_dict(json.loads(Path(path).read_text()))

    @classmethod
    def from_dict(cls, data):
        if data.get("schema") != "fair-hc.tree" or data.get("version") != 1:
            raise ValueError("Unsupported tree schema/version")
        nodes = {}
        for row in data["nodes"]:
            ident = row["id"]
            if not isinstance(ident, int) or ident in nodes:
                raise ValueError("Node IDs must be unique integers")
            nodes[ident] = Node(ident, leaf_id=row["leaf_id"])
        for row in data["nodes"]:
            nodes[row["id"]].children = [nodes[i] for i in row["children"]]
        root = nodes[data["root"]]
        seen = set()
        for node in preorder(root):
            if node in seen:
                raise ValueError("Cycle or shared subtree")
            seen.add(node)
        if len(seen) != len(nodes):
            raise ValueError("Unreachable nodes")
        ids = [n.leaf_id for n in seen if n.is_leaf]
        if sorted(ids) != list(range(len(data["labels"]))):
            raise ValueError("Leaves must correspond exactly to label rows")
        tree = cls(root, data["labels"])
        tree.validate()
        if data.get("palette", tree.palette) != tree.palette:
            raise ValueError("Palette does not match labels")
        return tree

    def validate(self, *, final=False):
        if self.root.parent is not None:
            raise ValueError("Root has parent")
        seen, ids, leaves, cached = set(), set(), [], {}
        for n in preorder(self.root):
            if n in seen or n.id in ids:
                raise ValueError("Cycle, shared subtree, or duplicate node ID")
            seen.add(n)
            ids.add(n.id)
            if n.is_leaf:
                if n.children:
                    raise ValueError("Leaf has children")
                leaves.append(n.leaf_id)
            elif len(n.children) < 2:
                raise ValueError("Dummy or unary internal node")
            for c in n.children:
                if c.parent is not n:
                    raise ValueError("Inconsistent parent")
            if final and any(c.is_leaf for c in n.children) and not all(
                    c.is_leaf for c in n.children):
                raise ValueError("Mixed leaf/internal children")
        if sorted(leaves) != list(range(len(self.labels))):
            raise ValueError("Leaf IDs do not match matrix rows")
        for n in postorder(self.root):
            count = np.zeros(len(self.palette), dtype=np.int64)
            if n.is_leaf:
                count[self._colors[self.labels[n.leaf_id]]] = 1
                size, minimum = 1, n.leaf_id
            else:
                size = sum(cached[c][0] for c in n.children)
                minimum = min(cached[c][2] for c in n.children)
                for c in n.children:
                    count += cached[c][1]
            if n.size != size or n.minimum != minimum or not np.array_equal(n.counts, count):
                raise ValueError("Incorrect cached metadata")
            cached[n] = size, count, minimum
        return True


def star(labels):
    labels = list(labels)
    if not labels:
        raise ValueError("A tree needs at least one leaf")
    nodes = [Node(i, leaf_id=i) for i in range(len(labels))]
    return Tree(nodes[0] if len(nodes) == 1 else Node(len(labels), children=nodes), labels)


def from_linkage(linkage, labels):
    from scipy.cluster.hierarchy import is_valid_linkage
    labels = list(labels)
    z = np.asarray(linkage, dtype=float)
    if len(labels) == 1 and z.size == 0:
        return star(labels)
    if z.shape != (len(labels) - 1, 4):
        raise ValueError("Linkage shape does not match labels")
    is_valid_linkage(z, throw=True)
    nodes = [Node(i, leaf_id=i) for i in range(len(labels))]
    for i, row in enumerate(z):
        nodes.append(Node(len(labels) + i, children=[nodes[int(row[0])], nodes[int(row[1])]]))
    tree = Tree(nodes[-1], labels)
    tree.validate()
    return tree
