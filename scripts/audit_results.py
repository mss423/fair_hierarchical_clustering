"""Audit every saved hierarchy, pairing, source hash, and archive checksum."""

from pathlib import Path
from collections import Counter, defaultdict
import gzip
import json
from fair_hc import Tree
from fair_hc.benchmark import source_hash
from fair_hc.data import sha256


def main():
    current = source_hash()
    statuses = Counter()
    paired = defaultdict(set)
    checked = 0
    for path in sorted(Path("results").glob("*/manifest.json")):
        manifest = json.loads(path.read_text())
        assert manifest["environment"]["source_hash"] == current, path
        for rid, entry in manifest["runs"].items():
            statuses[entry["status"]] += 1
            if entry["status"] != "complete":
                assert entry["status"] == "excluded" and entry["reason"]
                continue
            run = path.parent / entry["path"]
            data = json.loads(run.read_text())
            assert data["run_id"] == rid
            with gzip.open(run.with_name("tree.json.gz"), "rt") as f:
                tree = Tree.from_dict(json.load(f))
            assert tree.validate(
                final=entry["method"] in {"make_fair", "random_fold", "splitting_only", "star"}
            )
            assert tree.root.size == entry["spec"]["n"] == data["metrics"]["n"]
            sample = json.loads(
                (path.parent / "samples" / (data["sample_id"] + ".json")).read_text()
            )
            assert tree.labels == sample["labels"]
            assert len(sample["row_ids"]) == len(set(sample["row_ids"])) == tree.root.size
            with gzip.open(run.with_name("clusters.json.gz"), "rt") as f:
                clusters = json.load(f)
            assert len(clusters) == data["metrics"]["cluster_count"]
            assert all(sum(c["counts"]) == c["size"] for c in clusters)
            paired[(path.parent.name, json.dumps(entry["spec"], sort_keys=True))].add(
                data["sample_id"]
            )
            checked += 1
    assert all(len(ids) == 1 for ids in paired.values())
    for file, expected in json.loads(Path("data/manifest.json").read_text()).items():
        assert sha256(file) == expected
    supplement = json.loads(Path("legacy/supplement-manifest.json").read_text())
    assert sha256("legacy/neurips2023-supplement.zip") == supplement["archive_sha256"]
    for file, expected in supplement["extracted_files"].items():
        assert sha256(file) == expected
    record = {
        "validated_complete_trees": checked,
        "status_counts": dict(statuses),
        "paired_sample_groups": len(paired),
        "source_hash": current,
        "data_and_supplement_checksums": "passed",
    }
    Path("docs/qa").mkdir(parents=True, exist_ok=True)
    Path("docs/qa/artifact-audit.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
