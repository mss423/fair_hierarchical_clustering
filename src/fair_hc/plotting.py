"""Publication exports from saved measurements; seeds are replication units."""

from collections import defaultdict
from pathlib import Path
import gzip
import json
import os
import tempfile
import numpy as np


def pyplot():
    os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "fair-hc-mpl"))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "savefig.dpi": 180,
        }
    )
    return plt


COLORS = {
    "average": "#526777",
    "make_fair": "#007e87",
    "star": "#af6578",
    "splitting_only": "#b77b05",
    "random_fold": "#7152a3",
}
NAMES = {
    "average": "Average linkage",
    "make_fair": "MakeFair",
    "star": "Star",
    "splitting_only": "Splitting only",
    "random_fold": "Random fold",
}


def load_results(directory):
    directory = Path(directory)
    manifests = (
        [directory / "manifest.json"]
        if (directory / "manifest.json").exists()
        else sorted(directory.glob("*/manifest.json"))
    )
    results, statuses = [], defaultdict(int)
    for path in manifests:
        manifest = json.loads(path.read_text())
        for entry in manifest["runs"].values():
            statuses[entry["status"]] += 1
            if entry["status"] == "complete":
                row = json.loads((path.parent / entry["path"]).read_text())
                row["_path"] = path.parent / entry["path"]
                row["_profile"] = manifest["profile"]
                results.append(row)
    return results, dict(statuses)


def scenario(row):
    s = row["spec"]
    name = s["dataset"].title()
    if s["dataset"] == "synthetic":
        name += f" · {s.get('colors', 2)} colors · " + ("skewed" if s.get("skewed") else "balanced")
        name += " · " + ("correlated" if s.get("correlated") else "independent")
    if s["dataset"] == "bank":
        name += " · " + s.get("bank_mapping", "married")
    if s.get("standardized"):
        name += " · standardized"
    return name


def mean_se(values):
    values = np.asarray(values, dtype=float)
    return float(values.mean()), float(values.std(ddof=1) / np.sqrt(len(values))) if len(
        values
    ) > 1 else 0.0


def save(fig, output, name, plt):
    fig.savefig(output / (name + ".svg"), bbox_inches="tight")
    fig.savefig(output / (name + ".pdf"), bbox_inches="tight")
    fig.savefig(output / (name + ".png"), bbox_inches="tight")
    plt.close(fig)


def axes_for(names, plt, *, width=5, height=3.3):
    cols = min(2, len(names))
    rows = (len(names) + cols - 1) // cols
    fig, axes = plt.subplots(
        rows, cols, figsize=(width * cols, height * rows), squeeze=False, layout="constrained"
    )
    for ax in axes.flat[len(names) :]:
        ax.set_visible(False)
    return fig, list(axes.flat)


def seed_values(rows, metric):
    # Repeated parameter settings are not independent replications.
    seeds = defaultdict(list)
    for r in rows:
        seeds[r["spec"]["seed"]].append(metric(r))
    return [np.mean(v) for v in seeds.values()]


def plot_results(directory, output):
    plt = pyplot()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rows, statuses = load_results(directory)
    if not rows:
        raise ValueError("No complete saved runs to plot")
    scenarios = sorted(set(scenario(r) for r in rows))
    methods = list(dict.fromkeys(r["method"] for r in rows))
    note = "Mean ± SE across seeds; parameter settings averaged within seed where present."
    for metric, name, ylabel in [
        ("cost_ratio_to_average", "cost-inflation", "Cost / paired average-linkage cost"),
        ("max_representation_error", "representation-error", "Maximum color-proportion deviation"),
        ("max_size_imbalance", "structural-balance", "Maximum relative child-size imbalance"),
    ]:
        fig, axes = axes_for(scenarios, plt)
        for ax, group in zip(axes, scenarios):
            for method in methods:
                selected = [r for r in rows if scenario(r) == group and r["method"] == method]
                sizes = sorted(set(r["spec"]["n"] for r in selected))
                points = [
                    mean_se(
                        seed_values(
                            [r for r in selected if r["spec"]["n"] == n],
                            lambda r: r["metrics"][metric],
                        )
                    )
                    for n in sizes
                ]
                if sizes:
                    ax.errorbar(
                        sizes,
                        [p[0] for p in points],
                        yerr=[p[1] for p in points],
                        marker="o",
                        ms=3,
                        capsize=2,
                        label=NAMES.get(method, method),
                        color=COLORS.get(method),
                    )
            ax.set(xscale="log", title=group, xlabel="Sample size n", ylabel=ylabel)
            ax.grid(alpha=0.15)
        axes[0].legend(fontsize=8)
        fig.suptitle(ylabel + "\n" + note, fontsize=11)
        save(fig, output, name, plt)
    # Histograms average normalized distributions per run, then per seed.
    groups = [
        (s, c)
        for s in scenarios
        for c in next(r["metrics"]["palette"] for r in rows if scenario(r) == s)
    ]
    fig, axes = axes_for(groups, plt, height=2.8)
    bins = np.linspace(0, 1, 21)
    cluster_cache = {}

    def clusters(row):
        path = row["_path"].with_name("clusters.json.gz")
        if path not in cluster_cache:
            with gzip.open(path, "rt") as f:
                cluster_cache[path] = json.load(f)
        return cluster_cache[path]

    for ax, (s, color) in zip(axes, groups):
        largest = max(r["spec"]["n"] for r in rows if scenario(r) == s)
        for method in methods:
            selected = [
                r
                for r in rows
                if scenario(r) == s and r["method"] == method and r["spec"]["n"] == largest
            ]
            hist_by_seed = defaultdict(list)
            for row in selected:
                ci = row["metrics"]["palette"].index(color)
                values = [c["proportions"][ci] for c in clusters(row)]
                hist = np.histogram(values, bins)[0] / max(len(values), 1)
                hist_by_seed[row["spec"]["seed"]].append(hist)
            if hist_by_seed:
                hist = np.mean([np.mean(h, axis=0) for h in hist_by_seed.values()], axis=0)
                ax.stairs(hist, bins, label=NAMES.get(method, method), color=COLORS.get(method))
        ax.set(
            title=f"{s}\nColor {color}, n={largest}",
            xlabel="Cluster color proportion",
            ylabel="Mean within-run fraction",
        )
    axes[0].legend(fontsize=7)
    fig.suptitle(
        "All nonsingleton clusters, root included · each seed has equal weight", fontsize=11
    )
    save(fig, output, "color-distributions", plt)
    fig, axes = axes_for(scenarios, plt)
    for ax, s in zip(axes, scenarios):
        largest = max(r["spec"]["n"] for r in rows if scenario(r) == s)
        for method in methods:
            selected = [
                r
                for r in rows
                if scenario(r) == s and r["method"] == method and r["spec"]["n"] == largest
            ]
            x, y, err = [], [], []
            for low in [2**i for i in range(1, int(np.log2(largest)) + 1)]:
                seeds = defaultdict(list)
                for r in selected:
                    values = [
                        c["representation_error"] for c in clusters(r) if low <= c["size"] < 2 * low
                    ]
                    if values:
                        seeds[r["spec"]["seed"]].append(np.mean(values))
                if seeds:
                    mean, se = mean_se([np.mean(v) for v in seeds.values()])
                    x.append(low)
                    y.append(mean)
                    err.append(se)
            ax.errorbar(
                x,
                y,
                yerr=err,
                marker=".",
                label=NAMES.get(method, method),
                color=COLORS.get(method),
                capsize=2,
            )
        ax.set(
            xscale="log",
            title=s,
            xlabel="Cluster-size bin lower edge (powers of two)",
            ylabel="Mean representation error",
        )
    axes[0].legend(fontsize=8)
    fig.suptitle(
        "Representation versus cluster size · largest sample · mean ± SE of seed means", fontsize=11
    )
    save(fig, output, "error-by-cluster-size", plt)
    fig, axes = axes_for(scenarios, plt)
    for ax, s in zip(axes, scenarios):
        selected = [r for r in rows if scenario(r) == s and r["method"] == "make_fair"]
        settings = sorted(
            set(
                (r["parameters"]["h"], r["parameters"]["k"], r["parameters"]["epsilon"])
                for r in selected
            )
        )
        for h, k, eps in settings:
            subset = [
                r
                for r in selected
                if (r["parameters"]["h"], r["parameters"]["k"], r["parameters"]["epsilon"])
                == (h, k, eps)
            ]
            for n in sorted(set(r["spec"]["n"] for r in subset)):
                sample_rows = [r for r in subset if r["spec"]["n"] == n]
                x, xe = mean_se([r["metrics"]["cost_ratio_to_average"] for r in sample_rows])
                y, ye = mean_se([r["metrics"]["max_representation_error"] for r in sample_rows])
                ax.errorbar(
                    x,
                    y,
                    xerr=xe,
                    yerr=ye,
                    fmt="o",
                    capsize=2,
                    label=f"h={h}, k={k}, ε={eps:.4g}, n={n}",
                )
        ax.set(
            title=s,
            xlabel="Cost / paired average-linkage cost",
            ylabel="Maximum representation error",
        )
        ax.legend(fontsize=6)
    fig.suptitle(
        "Measured fairness–cost trade-off · MakeFair · mean ± SE across seeds", fontsize=11
    )
    save(fig, output, "fairness-cost", plt)
    fig, axes = axes_for(scenarios, plt)
    for ax, s in zip(axes, scenarios):
        for method in methods:
            selected = [r for r in rows if scenario(r) == s and r["method"] == method]
            sizes = sorted(set(r["spec"]["n"] for r in selected))
            values = [
                mean_se(
                    seed_values(
                        [r for r in selected if r["spec"]["n"] == n],
                        lambda r: sum(r["times"].values()),
                    )
                )
                for n in sizes
            ]
            ax.errorbar(
                sizes,
                [v[0] for v in values],
                yerr=[v[1] for v in values],
                marker=".",
                capsize=2,
                label=NAMES.get(method, method),
                color=COLORS.get(method),
            )
        ax.set(
            xscale="log", yscale="log", title=s, xlabel="Sample size n", ylabel="End-to-end seconds"
        )
    axes[0].legend(fontsize=8)
    fig.suptitle(
        "Runtime scaling · shared preprocessing/construction charged to each method", fontsize=11
    )
    save(fig, output, "runtime-scaling", plt)
    fig, axes = axes_for(scenarios, plt)
    for ax, s in zip(axes, scenarios):
        n = max(r["spec"]["n"] for r in rows if scenario(r) == s)
        bottoms = np.zeros(len(methods))
        for stage in ["preprocessing", "construction", "transformation", "evaluation"]:
            values = [
                np.mean(
                    seed_values(
                        [
                            r
                            for r in rows
                            if scenario(r) == s and r["method"] == m and r["spec"]["n"] == n
                        ],
                        lambda r: r["times"][stage],
                    )
                )
                for m in methods
            ]
            ax.bar(np.arange(len(methods)), values, bottom=bottoms, label=stage)
            bottoms += values
        ax.set(title=f"{s}, n={n}", ylabel="Mean seconds")
        ax.set_xticks(
            np.arange(len(methods)),
            [NAMES.get(m, m) for m in methods],
            rotation=25,
            ha="right",
            fontsize=8,
        )
    axes[0].legend(fontsize=7)
    fig.suptitle("Stage breakdown · largest sample", fontsize=11)
    save(fig, output, "runtime-stages", plt)
    fig, axes = plt.subplots(
        len(scenarios), 3, figsize=(13, 3 * len(scenarios)), squeeze=False, layout="constrained"
    )
    for axs, s in zip(axes, scenarios):
        n = max(r["spec"]["n"] for r in rows if scenario(r) == s)
        for ax, metric, label in zip(
            axs,
            ["depth", "cluster_count", "terminal_sizes"],
            ["Hierarchy depth", "Nonsingleton clusters", "Mean terminal-cluster size"],
        ):
            points = []
            for m in methods:
                selected = [
                    r for r in rows if scenario(r) == s and r["method"] == m and r["spec"]["n"] == n
                ]
                points.append(
                    mean_se(
                        seed_values(
                            selected,
                            lambda r: np.mean(r["metrics"][metric])
                            if metric == "terminal_sizes"
                            else r["metrics"][metric],
                        )
                    )
                )
            ax.bar(
                np.arange(len(methods)),
                [p[0] for p in points],
                yerr=[p[1] for p in points],
                color=[COLORS.get(m, "#555") for m in methods],
                capsize=2,
            )
            ax.set_xticks(
                np.arange(len(methods)),
                [NAMES.get(m, m) for m in methods],
                rotation=25,
                ha="right",
                fontsize=7,
            )
            ax.set(title=f"{s}\n{label}", ylabel=label)
            if metric != "depth":
                ax.set_yscale("log")
    fig.suptitle("Hierarchy resolution · largest sample · mean ± SE across seeds", fontsize=11)
    save(fig, output, "hierarchy-resolution", plt)
    multicolor = [r for r in rows if r["spec"]["dataset"] == "synthetic"]
    palettes = sorted(set(r["spec"].get("colors", 2) for r in multicolor))
    if len(palettes) > 1:
        n = max(r["spec"]["n"] for r in multicolor)
        fig, axes = plt.subplots(
            2, len(palettes), figsize=(13, 7), squeeze=False, layout="constrained"
        )
        conditions = [(False, False), (False, True), (True, False), (True, True)]
        width = 0.8 / len(methods)
        for column, colors in enumerate(palettes):
            for row_index, (metric, label) in enumerate(
                [
                    ("cost_ratio_to_average", "Cost / average linkage"),
                    ("max_representation_error", "Max representation error"),
                ]
            ):
                ax = axes[row_index, column]
                for mi, method in enumerate(methods):
                    points = []
                    for skewed, correlated in conditions:
                        selected = [
                            r
                            for r in multicolor
                            if r["method"] == method
                            and r["spec"]["n"] == n
                            and r["spec"].get("colors", 2) == colors
                            and r["spec"].get("skewed", False) == skewed
                            and r["spec"].get("correlated", False) == correlated
                        ]
                        points.append(
                            mean_se(seed_values(selected, lambda r: r["metrics"][metric]))
                        )
                    ax.bar(
                        np.arange(4) - 0.4 + width * (mi + 0.5),
                        [p[0] for p in points],
                        width,
                        yerr=[p[1] for p in points],
                        label=NAMES.get(method, method),
                        color=COLORS.get(method),
                        capsize=1,
                    )
                ax.set_xticks(
                    np.arange(4),
                    ["Bal. / indep.", "Bal. / corr.", "Skew / indep.", "Skew / corr."],
                    rotation=20,
                    ha="right",
                    fontsize=8,
                )
                ax.set(title=f"{colors} colors", ylabel=label)
        axes[0, 0].legend(fontsize=7)
        fig.suptitle(f"Multicolor synthetic data · n={n} · mean ± SE across seeds", fontsize=12)
        save(fig, output, "multicolor-summary", plt)
    (output / "provenance.json").write_text(
        json.dumps(
            {
                "source": str(directory),
                "status_counts": statuses,
                "complete_runs": len(rows),
                "uncertainty": "standard error across independent seeds; no cluster-level replication",
                "warnings": [
                    "No optimum is computed. Cost ratios use paired average linkage.",
                    "Terminal stars reduce resolution. See hierarchy-resolution figures.",
                    "Incomplete runs are excluded from plots and counted above.",
                ],
            },
            indent=2,
        )
        + "\n"
    )
    print(f"Wrote figures to {output} ({len(rows)} complete runs; statuses {statuses})")
