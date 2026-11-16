# Data and source provenance

All originally supplied files were moved without changing their bytes.
`legacy/original-manifest.json` records their original paths and SHA-256 hashes,
including the unchanged conference PDF. `tests/test_integration.py` verifies the
archived files against that manifest.

## Adult

Source: [UCI Adult](https://archive.ics.uci.edu/dataset/2/adult), Becker and Kohavi
(1996), DOI [10.24432/C5XW20](https://doi.org/10.24432/C5XW20).
The bundled `data/raw/adult.data` is the training partition, with 32,561 data rows;
the 48,842-row combined UCI dataset is not silently substituted. A trailing blank
record is ignored as an invalid row.

We use age, fnlwgt, education-num, capital-gain, capital-loss, and hours-per-week.
The protected label is White versus every other race category. Rows with `?` or
empty fields in any column are removed, including missing unused categorical
fields: this explicit complete-case choice leaves 30,162 rows. It matches the
historical preprocessing intent but changes the eligible population. No imputation
is performed. The preprocessed historical `adult.csv` is retained under
`data/legacy/` and is not an input to the new experiments.

## Bank

Source: [UCI Bank Marketing](https://archive.ics.uci.edu/dataset/222/bank+marketing),
Moro, Rita, and Cortez, DOI [10.24432/C5K306](https://doi.org/10.24432/C5K306).
The bundled file **`data/raw/bank_a.csv` has 45,211 records** and the older full
Bank schema. Its misleading local name is preserved for provenance. The bundled
`bank.csv` contains only 4,521 records and is archived but not used. The supplied
`bank-names.txt` describes both files and retains the original citation request
for Moro, Laureano, and Cortez (ESM 2011).

Features are age, balance, day, duration, campaign, pdays, and previous. Married
versus other marital categories is primary; single versus other is a separate
sensitivity. Unknown unused categorical values are retained. Missing selected
numerical or marital fields would be dropped; all 45,211 supplied rows are
eligible. The numerical sentinel `pdays=-1` is retained as supplied.

## Geometry, row identity, and sampling

Primary experiments use raw numerical features and
`similarity(i,j) = 1/(1 + EuclideanDistance(i,j))`. Large-scale fields can dominate
raw Euclidean distance. Standardized runs are separately labeled; means and
population standard deviations are fitted on the sampled rows, and constant
features use scale one. These runs do not replace raw-feature runs.

For each seed, largest-remainder proportional allocation determines group sample
counts, followed by seeded sampling without replacement inside each group. Each
count differs from its ideal population-proportional allocation by less than one.
Selected original row IDs are sorted and saved, and tree leaf IDs index that
saved ordering. Row IDs are zero-based data rows, excluding the header where one
exists. This preserves observed proportions rather than enforcing the paper's
rounded ratios. Every method within an experiment uses exactly the same sample.

Each sample JSON records source SHA-256, eligible/dropped rows, group counts,
feature columns, mapping, sampled row IDs, seed, scaling values, and a hash of the
actual sampled numerical array and labels. Root input provenance and all file
hashes are also saved in `data/manifest.json`.

Synthetic experiments use two numerical coordinates, Gaussian noise, fixed group
counts rounded by largest remainders, and shuffled labels. Skewed weights are
`[4,1,...,1]`; correlated geometry adds `3*color_index` to the first coordinate.
Balanced/skewed and independent/correlated conditions are distinct experiments.
