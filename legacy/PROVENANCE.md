# Archived implementations

`original/` contains the scripts supplied with this workspace, including their
README, requirements, output text, bytecode, and unchanged MIT license notice
(Copyright 2020 wangyuyan2333). The old README identifies the earlier paper,
“Generalized Reductions: Making any Hierarchical Clustering Fair and Balanced
with Low Cost.” These scripts are historical material, not the new top-down
implementation. Input tables now live in `data/raw/` and `data/legacy/`.

`neurips2023-supplement.zip` is the byte-for-byte archive downloaded on 2026-11-16
from the [NeurIPS 2023 supplemental link](https://proceedings.neurips.cc/paper_files/paper/2023/file/8c533f53f76c4df9a7f08e7cb676d132-Supplemental-Conference.zip).
It contains `Fair_HC_NeurIPS_23/codes_fairhc.zip` and `full_paper.pdf`. The Python
sources and full paper are extracted under `supplement/`; its CSV tables are
under `data/legacy/supplement/`. Apple `__MACOSX` metadata was not extracted but
remains in the original ZIP. No separate code license was present in the recovered
archive; the original archive is retained with provenance and no new license
claim is made for that material. It is not included in the Python wheel.

`original-manifest.json` records SHA-256 hashes at the original workspace paths.
`supplement-manifest.json` records the download URL, archive hash, member names,
and hashes of extracted files. The conference PDF supplied under `lit/` was not
modified or replaced by the supplementary full paper.

The modern `src/fair_hc/` implementation was written separately. The supplementary
code was inspected to document differences; it is never imported by the package.
See `docs/algorithm.md` for corrections and finite-size extensions.
