from pathlib import Path
import json
import numpy as np
import pytest
from fair_hc import Tree, average_linkage, make_fair, similarities
from fair_hc.data import load_dataset, sample, synthetic
from fair_hc.adapters import benchmark_adapter, default_parameters
from fair_hc.benchmark import run_benchmark


@pytest.mark.parametrize(
    "name,mapping,count",
    [("adult", "married", 30162), ("bank", "married", 45211), ("bank", "single", 45211)],
)
def test_data_and_stratification(name, mapping, count):
    d = load_dataset(name, bank_mapping=mapping)
    assert len(d.labels) == count
    a, b = sample(d, 129, 8), sample(d, 129, 8)
    assert a.row_ids == b.row_ids and np.array_equal(a.features, b.features)
    assert len(set(a.row_ids)) == 129
    for color in set(d.labels):
        assert abs(a.labels.count(color) - d.labels.count(color) / count * 129) < 1
    scaled = sample(d, 129, 8, standardized=True)
    assert scaled.row_ids == a.row_ids and np.allclose(scaled.features.mean(axis=0), 0, atol=1e-12)
    assert scaled.metadata["scaler"]["fit"] == "sample"


def test_compiled_geometry_equivalence():
    x = np.random.default_rng(7).normal(size=(23, 4))
    w = similarities(x)
    expected = np.array([[1 / (1 + sum((a - b) ** 2) ** 0.5) for b in x] for a in x])
    assert np.allclose(w, expected, rtol=1e-14)


def test_public_adapter_and_trace():
    d = synthetic(64)
    p = default_parameters(d.labels)
    t = benchmark_adapter(d, 0, p)
    assert t.validate(final=True)
    initial = average_linkage(similarities(d.features), d.labels)
    result = make_fair(initial, d.labels, trace=True, **p)
    assert {"move", "fold", "terminal"} <= {e["operation"] for e in result.trace}
    for event in result.trace:
        assert Tree.from_dict(event["tree"]).validate()


def config(tmp_path, methods=None, parameters=None):
    p = tmp_path / "config.json"
    d = {
        "version": 1,
        "name": "test",
        "experiments": [{"dataset": "synthetic", "sizes": [32], "seeds": [0]}],
    }
    if methods is not None:
        d["methods"] = methods
    if parameters is not None:
        d["experiments"][0]["parameters"] = [parameters]
    p.write_text(json.dumps(d))
    return p


def test_resume_and_custom_adapter(tmp_path):
    path = config(tmp_path, ["average", "examples.custom_algorithm:cluster"])
    out = tmp_path / "results"
    result = run_benchmark(path, out)
    assert result["status_counts"] == {"complete": 2}
    files = list(out.glob("runs/*/metrics.json"))
    original = {p: p.stat().st_mtime_ns for p in files}
    resumed = run_benchmark(path, out, resume=True)
    assert resumed["complete"]
    assert original == {p: p.stat().st_mtime_ns for p in files}
    with pytest.raises(ValueError, match="Output exists"):
        run_benchmark(path, out)
    changed = json.loads(path.read_text())
    changed["experiments"][0]["seeds"] = [1]
    path.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="identical"):
        run_benchmark(path, out, resume=True)


def test_visible_resource_limit_and_exclusion(tmp_path):
    path = config(tmp_path)
    result = run_benchmark(path, tmp_path / "memory", memory_gib=0.001)
    assert not result["complete"] and result["status_counts"] == {"resource_limited": 5}
    result = run_benchmark(path, tmp_path / "memory", memory_gib=8, resume=True)
    assert result["complete"]
    result = run_benchmark(path, tmp_path / "time", time_limit=0)
    assert not result["complete"] and result["status_counts"] == {"pending": 5}
    config(tmp_path, parameters={"h": 4, "k": 2, "epsilon": 1 / 64})
    result = run_benchmark(path, tmp_path / "excluded")
    assert result["status_counts"] == {"excluded": 5}
    assert all("h/k^lambda" in r["reason"] for r in result["runs"].values())


def test_plot_from_saved_results(tmp_path):
    from fair_hc.plotting import plot_results

    path = config(tmp_path)
    out = tmp_path / "results"
    run_benchmark(path, out)
    plot_results(out, tmp_path / "figures")
    for suffix in ["svg", "pdf", "png"]:
        assert len(list((tmp_path / "figures").glob("*." + suffix))) == 9
    assert json.loads((tmp_path / "figures/provenance.json").read_text())["complete_runs"] == 5


def test_original_bytes_preserved():
    from fair_hc.data import sha256

    manifest = json.loads(Path("legacy/original-manifest.json").read_text())
    for original, expected in manifest.items():
        p = Path(original)
        if original.startswith("src/"):
            if p.name in ["adult.data", "bank_a.csv", "bank-names.txt", "bank.csv"]:
                p = Path("data/raw") / p.name
            elif p.suffix == ".csv":
                p = Path("data/legacy") / p.name
            else:
                p = Path("legacy/original") / p.name
        assert sha256(p) == expected
