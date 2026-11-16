# Validation record

Local validation on 2026-11-16 used CPython 3.13.5 on macOS arm64, NumPy 2.3.3,
SciPy 1.16.3, and Matplotlib 3.10.8. Exact dependencies and artifact hashes are in
`requirements.lock`. CI is configured for Python 3.11 and 3.13; remote CI has not
yet been run for this refresh.

## Completed

- **42 tests passed** with `pytest -q`. Coverage includes tree invariants,
  hand-worked operators and grouping, deep skew trees, two to four colors,
  missing local colors, nondivisible sizes, invalid global settings, integer
  stalls, tied similarities, duplicate points, nonbinary cost, independent
  pairwise-LCA evaluation, independent untied average-linkage clades, deterministic
  output, input immutability, JSON validation/round trips, proportional sampling,
  saved traces, custom adapters, resource/time limits, resume, and saved-result plots.
- `ruff check src/fair_hc tests examples scripts` passed.
- Source distribution and wheel built with `python -m build --no-isolation`.
  A separate clean virtual environment installed all hash-verified locked
  dependencies and the wheel. Its import resolved to that environment's
  `site-packages`, not the editable source tree. `pip check` passed.
- In the clean wheel environment, smoke benchmark, resume, plot, demo, and the
  custom-adapter example all completed. The full saved main study also passed a
  no-work resume against the original code/input/config signature.
- **3,017 completed saved hierarchies** passed a separate full artifact audit:
  no cycles/shared nodes, unique IDs, correct parents, cached sizes and color
  counts, leaf preservation, and final leaf-child structure for the transformed
  methods. All 604 experiment sample groups were paired across their methods.
  Saved cluster counts and sample labels match the trees. Data and supplement
  SHA-256 checks passed. See `docs/qa/artifact-audit.json`.
- All seven profiles completed: 3,017 method-runs and five explicit exclusions.
  Main coverage includes both datasets through 8,192 rows and all ten seeds.
  No resource-limited or failed study runs remain. Peak recorded process RSS was
  1.649 GiB under the configured 8 GiB estimate/check budget.
- Independent small-case component benchmarks checked equivalent similarity
  matrices, untied linkage clades, and costs before recording timings. Raw
  measurements are in `results/component-speedups.json`.
- Saved figure families export SVG, PDF, and PNG. PDFs were reopened and rendered
  with PyMuPDF (Poppler was unavailable); every text bounding box was checked
  against its page. Representative main, parameter, resolution, and walkthrough
  companion figures were visually inspected. `docs/qa/pdf-check.json` records
  PDF export checks.
- The offline walkthrough was generated from 27 actual tree snapshots. Each
  snapshot passed the tree validator and independent evaluation. A dependency-free
  JavaScript DOM harness exercised all states, previous/next/start/final controls,
  next-fold navigation, slider, keyboard handlers, highlighting, and cluster
  inspection. No external scripts or other assets are referenced. See
  `docs/qa/dom-check.json` and `scripts/check_demo_dom.mjs`.

## Browser validation completed

The first external browser run reached the mobile assertion and failed: the
390-pixel viewport had page-level horizontal overflow. Its screenshot showed the
720-pixel tree expanding the mobile grid's automatic minimum column width. The
template and generated HTML now use shrinkable grid tracks/cards, with horizontal
scrolling contained inside the tree panel. Metric cards also adapt to narrow
screens. The subsequent external browser run passed all checks. Its saved report,
`docs/qa/browser-check.json`, records Chrome 159.0.8154.6 and successful checks of
all 27 trace states at six viewport widths. The updated mobile screenshot was
also inspected: the page fits the viewport and the tree scrolls within its panel.

The agent's sandbox still cannot launch Chromium because macOS denies the
`MachPortRendezvousServer` bootstrap operation. The successful browser run was
performed by the user outside that sandbox and completes the previously blocked
browser validation. The DOM-only report records its narrower scope separately.

The supplied `scripts/check_demo.mjs` performs the real Playwright checks,
including all 27 states at widths 320, 390, 768, 900, 901, and 1440 pixels,
highlights, inspection, keyboard navigation, page overflow, local tree scrolling,
offline requests, and desktop/mobile screenshots. Failures now report the viewport,
trace step, and overflowing containers and save a diagnostic screenshot. To repeat
the check:

```sh
npm install --no-save playwright
npx playwright install chromium
node scripts/check_demo.mjs
```

`PLAYWRIGHT_MODULE`, `CHROMIUM_EXECUTABLE`, and `QA_OUTPUT` optionally select an
existing module, browser executable, and output directory. Browser evidence is
saved separately from the DOM-only logic report.
