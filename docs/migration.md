# Migration from the historical scripts

Historical Python files, requirements, README, output text, bytecode, and license
are under `legacy/original/`. Their old relative input paths no longer resolve
from `src/`; if archival execution is needed, copy the relevant data into a
separate scratch directory and recreate the historical environment there.

The recovered NeurIPS scripts are under `legacy/supplement/`, with their tables
under `data/legacy/supplement/`. They are not imported by the modern package.
No deprecated function is silently redirected to a different algorithm.

Use `fair_hc.average_linkage` and `make_fair` in place of script-level mutation,
`evaluate` in place of repeated pairwise tree searches, and the CLI for experiments.
MakeFair returns `FairResult(tree, diagnostics, trace)` and leaves its input intact.
Labels belong to stable matrix rows, not internal nodes. Final trees can be
nonbinary: store them in the versioned JSON format rather than forcing them into
SciPy linkage. `from_linkage` imports a SciPy starting hierarchy.

The new default two-color settings are `h=16, k=2, epsilon=1/64`. The published
`h=4, k=2` case is explicitly excluded. New measurements use corrected operations,
observed group proportions, and documented integer terminal extensions, so they
should not be presented as exact reproduction of old script outputs.
