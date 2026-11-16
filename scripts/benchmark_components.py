"""Measure equivalent correct components, never compare different algorithms."""

from pathlib import Path
import json
import time
import numpy as np
from fair_hc import average_linkage, similarities
from fair_hc.metrics import dasgupta_cost
from fair_hc.reference import average_linkage_reference, pairwise_lca_cost
from fair_hc.benchmark import environment
from fair_hc.tree import preorder


def timed(fn):
    start = time.perf_counter()
    value = fn()
    return value, time.perf_counter() - start


def slow_similarities(x):
    return np.array([[1 / (1 + sum((a - b) ** 2) ** 0.5) for b in x] for a in x])


def clades(tree):
    return {
        frozenset(n.leaf_id for n in preorder(root) if n.is_leaf) for root in preorder(tree.root)
    }


def main():
    rows = []
    # Warm compiled paths before measurement.
    average_linkage(similarities(np.arange(12).reshape(6, 2)), ["a", "b"] * 3)
    for n in [32, 64, 128]:
        for seed in range(5):
            x = np.random.default_rng(seed).normal(size=(n, 4))
            labels = ["a", "b"] * (n // 2)
            slow, st = timed(lambda: slow_similarities(x))
            fast, ft = timed(lambda: similarities(x))
            assert np.allclose(slow, fast, rtol=1e-13)
            rows.append(
                dict(
                    component="similarities",
                    n=n,
                    seed=seed,
                    reference_seconds=st,
                    optimized_seconds=ft,
                    speedup=st / ft,
                )
            )
            a, st = timed(lambda: average_linkage_reference(fast, labels))
            b, ft = timed(lambda: average_linkage(fast, labels))
            assert clades(a) == clades(b)
            rows.append(
                dict(
                    component="average_linkage",
                    n=n,
                    seed=seed,
                    reference_seconds=st,
                    optimized_seconds=ft,
                    speedup=st / ft,
                )
            )
            a, st = timed(lambda: pairwise_lca_cost(b, fast))
            b, ft = timed(lambda: dasgupta_cost(b, fast))
            assert np.isclose(a, b, rtol=1e-12)
            rows.append(
                dict(
                    component="cost",
                    n=n,
                    seed=seed,
                    reference_seconds=st,
                    optimized_seconds=ft,
                    speedup=st / ft,
                )
            )
    Path("results/component-speedups.json").write_text(
        json.dumps(
            {
                "environment": environment(),
                "note": "Same inputs and equivalent computations; five seeds; one timing per seed after warmup. Small-case microbenchmarks, not asymptotic or legacy correctness claims.",
                "rows": rows,
            },
            indent=2,
        )
        + "\n"
    )
    for component in ["similarities", "average_linkage", "cost"]:
        values = [r["speedup"] for r in rows if r["n"] == 128 and r["component"] == component]
        print(component, "n=128 median speedup", np.median(values))


if __name__ == "__main__":
    main()
