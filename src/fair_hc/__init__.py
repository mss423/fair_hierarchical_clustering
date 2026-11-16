"""Fair hierarchical clustering with explicit finite-size diagnostics."""
from .algorithm import FairResult, SplitInfeasible, make_fair, split_root
from .tree import Node, Tree, from_linkage, star
from .metrics import evaluate
from .geometry import average_linkage, similarities

__all__ = ["FairResult", "SplitInfeasible", "make_fair", "split_root", "Node", "Tree",
           "from_linkage", "star", "evaluate", "average_linkage", "similarities"]
__version__ = "0.1.0"
