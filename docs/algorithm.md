# Algorithm correspondence and implementation limits

This package implements the top-down procedure in Knittel, Springer, Dickerson,
and Hajiaghayi, [NeurIPS 2023](https://proceedings.neurips.cc/paper_files/paper/2023/hash/8c533f53f76c4df9a7f08e7cb676d132-Abstract-Conference.html).
The [full appendix](https://arxiv.org/html/2311.12501) supplies the intended folding
construction. The unchanged supplied conference PDF remains in `lit/`; the
recovered supplement and its full paper are in `legacy/`.

## Correspondence

| Paper operation | Implementation | Interpretation |
|---|---|---|
| Definition 5: deletion/insertion | `operators.del_ins` | Move the donor subtree; contract its old binary parent; introduce a parent at the recipient. Replace an empty recipient directly. |
| Definition 6: shallow folding | `operators.shallow_fold` | Union the children of sibling roots, preserving singleton roots as points. Refine the resulting subtree deterministically into a binary tree before further processing. |
| Algorithm 1: SplitRoot | `algorithm._split`, public `split_root` | Add zero-size placeholders; move a donor found by descending through larger children to a recipient found by descending through smaller children. |
| Algorithm 2: MakeFair | `algorithm.make_fair` | Split; fold once per global color; process each child; flatten terminal subtrees. An explicit stack replaces Python recursion. |
| Definition 2: cost | `metrics.dasgupta_cost` | Sum cross-child similarities times the node's leaf count. Every unordered leaf pair contributes once. |
| Definition 4: structural balance | `metrics.evaluate` | At each node with q children, measure `max_i abs(size(child_i)/size(node) - 1/q)`. |
| Definition 3: representation | `metrics.evaluate` | Evaluate every nonsingleton cluster, including the root, against optional explicit proportion bounds. |

Ties use `(subtree size, minimum leaf ID, node ID)`; density ordering uses decreasing
density followed by minimum leaf ID and node ID. The palette is the sorted set of
**global string labels**, and stays fixed even when a color is absent in a subtree.
Use distinct string representations for distinct groups. SciPy's starting-tree
tie resolution is deterministic within the locked environment; identical tied
linkages across library versions are not promised.

## Corrections to ambiguous pseudocode

1. **Donor and recipient.** Algorithm 1 line 20 writes the arguments in the
   opposite order to its preceding traversal and Definition 5. The selected donor
   `v` moves to recipient `u`. The code exposes `del_ins(tree, donor, recipient)`.
2. **Folding groups.** Follow Section 3.2's prose and the proof of Lemma 4. With
   `h_prime` current children, sort by the current color, divide into `k` contiguous
   chunks of length `width = h_prime/k`, then fold
   `[children[i + j*width] for j in range(k)]` for each `i` in `range(width)`.
   Form every group before mutating anything. This yields `h_prime/k` children.
   The printed loop/stride in Algorithm 2 line 5 does not implement that description.
3. **Recursion.** Test the current child's size against `max(h, 1/(2*epsilon))`,
   rather than reusing the parent's `n` from Algorithm 2 line 9.
4. **Output arity.** SplitRoot returns `h` root children; the `k` in its printed
   output description is inconsistent with the initialization and proof.

The recovered supplementary implementation has further practical differences:
its folding list uses the initial `h` and accumulates one list, and its split loop
can break when the selected nodes are leaves. It is archived, not used as the new
correctness oracle. Tests use separate small reference computations.

## Admissible settings

Require integer `k >= 2`, integer `h >= 2`, `k**lambda` dividing `h`,
`h/k**lambda >= 2`, and `0 < epsilon < min(1/6, 1/h)`. Divisibility is the simplifying
assumption stated in the appendix. The remaining-child restriction prevents a
folded root from becoming a one-child copy of the same subproblem. It is a finite
implementation restriction, not a replacement for the asymptotic `h >> k**lambda`
condition. The default is `k=2`, `h=4*k**lambda`, `epsilon=1/(4*h)`.

For two colors, the published `h=4, k=2` setting folds to one child. It is rejected
before tree mutation. `configs/excluded.json` and `results/excluded/manifest.json`
record the excluded configuration and reason. No exact reproduction of the
paper's inconsistent setting is claimed.

## Integer and finite-size extensions

Standalone SplitRoot raises `SplitInfeasible` without modifying the caller's tree:

- `integer_bounds_infeasible`: with `L=ceil(n*(1/h-epsilon))` and
  `U=floor(n*(1/h+epsilon))`, no integer allocation can satisfy `h*L <= n <= h*U`;
- `below_paper_size_threshold`: the input is smaller than `1/(2*epsilon)`;
- `prescribed_transfer_below_one_leaf`: the prescribed budget
  `min(n/h-smallest_size, largest_size-n/h)` is below one, despite an unmet bound.

Floating comparisons allow an absolute `1e-12` rounding tolerance. MakeFair turns
such a subtree into a star and logs its node ID, leaf count, and reason. The normal
threshold terminal case is logged too. A stall may occur after several moves;
flattening retains all the original leaves, and discards the partial topology.
These extensions guarantee an executable finite procedure, not the paper's
unmodified approximation theorem. The splitting-only ablation also flattens a
node if it would otherwise mix leaf and internal children; that distinct reason
is recorded. MakeFair's completed output always has only leaf children at any
node with a leaf child.

A concrete integer-stall example is covered by the small-tree tests. Feasible
integer bounds alone do not guarantee the prescribed donor budget is integral
or at least one. The published size threshold does not eliminate all such stalls.

## Epsilon and unverified guarantees

The implemented splitting bounds are **additive**:
`n/h - epsilon*n <= child_size <= n/h + epsilon*n`.
The appendix also uses expressions of the form `(1 ± epsilon)*n/h`; these use a
different normalization. We do not silently substitute that normalization.

Merging `k` equally many children can add their deviations: the directly available
additive bound is `k*epsilon`, then `k**lambda*epsilon` after all colors, rather
than automatically the original epsilon. Each fold's **actual** imbalance is
saved separately. The study contains measured violations of the original epsilon
after folding. No unchanged-epsilon theorem or computable finite fairness bounds
are claimed. Supply application-specific `bounds` to `evaluate` when needed;
unknown constants hidden in asymptotic expressions are never guessed.

## Representation and complexity

Trees retain nonbinary output. Leaves are matrix row IDs `0..n-1`; internal node
IDs are stable within a transformation. Cached counts, sizes, and minimum leaf IDs
are updated along affected ancestor paths. Traversals, copying, JSON import, and
transformation use iterative traversal. Public MakeFair copies its input once;
operator mutations do not copy the whole hierarchy. Trace mode additionally saves
whole-tree snapshots and is intended for small examples.

Geometry uses SciPy `pdist`, and average linkage uses SciPy on condensed
`1 - similarity`. Evaluation builds one DFS leaf ordering and subtree intervals,
then sums cross-child blocks (default 256 by 256). Stars use blocked upper-triangle
sums. This avoids per-pair ancestor searches and unbounded cross-product indexing
arrays. Dense similarities still require quadratic storage. No implementation
runtime theorem is inferred from the paper for pathological tree shapes or the
finite-size extensions.
