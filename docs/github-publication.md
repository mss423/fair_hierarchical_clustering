# Publish the refresh to the existing GitHub repository

Destination: https://github.com/mss423/fair_hierarchical_clustering (already public).
At preparation time, its main branch was at
`92214474ad1c63b8c4300b99a32244e67adbc90b` ("Added ms scripts"). All 30 upstream
source, data, license, and documentation files match the original-file hashes
preserved by this refresh. The remaining upstream files are OS metadata and
Python bytecode. Keep the original Git history when publishing.

Run these commands in a normal Terminal from this workspace's root (the same
directory used to run `node scripts/check_demo.mjs`). This workspace currently
has no `.git` directory. Stop if any command fails.

```sh
git init -b main
git remote add origin https://github.com/mss423/fair_hierarchical_clustering.git
git fetch origin main
git rev-parse origin/main
```

Check that the printed SHA matches the one above. If the remote has changed,
review those newer changes before proceeding. The next command attaches the
existing main history while leaving the refreshed working files in place:

```sh
git reset --mixed origin/main
git add -A
git diff --cached --stat
```

The staged changes should show historical root scripts/data moved under
`legacy/` and `data/`, the new `src/fair_hc/` package, tests, CI, documentation,
all measured results, and figures. Local `.venv/`, `node_modules/`, caches, and
`dist/` are ignored. Data and archived sources are marked to preserve their bytes.
The publication contains approximately 128 MiB of files before Git compression;
the largest individual file is about 4.4 MiB. No Git LFS setup is needed for these
files.

After reviewing the staged summary, commit and push:

```sh
git commit -m "Modernize fair hierarchical clustering with reproducible benchmarks"
git push -u origin main
```

The push uses your normal GitHub Git credentials. Do not force-push. If another
commit lands remotely in the meantime, a normal push will refuse to overwrite it.

After pushing, check the repository's Actions tab for the Python 3.11 and 3.13
jobs. Local Python tests, artifact checks, and external browser checks have
passed; GitHub-hosted CI remains to be observed.

## Serve the interactive walkthrough with GitHub Pages

The repository file view displays HTML as source. GitHub Pages serves it as a
webpage. The self-contained `docs/demo.html` needs no application server or build.

Push the Pages entry files and the updated README:

```sh
git add README.md docs/.nojekyll docs/index.html docs/github-publication.md
git commit -m "Prepare GitHub Pages hosting for the interactive walkthrough"
git push origin main
```

Then open the repository's [Pages settings](https://github.com/mss423/fair_hierarchical_clustering/settings/pages):

1. Under **Build and deployment**, set **Source** to **Deploy from a branch**.
2. Select branch **main** and folder **/docs**.
3. Click **Save** and wait for the Pages deployment to finish in the Actions tab.

The walkthrough URL will be
https://mss423.github.io/fair_hierarchical_clustering/demo.html.
The site root, https://mss423.github.io/fair_hierarchical_clustering/,
redirects to the same demo. Publishing from `/docs` means the URL does not include
`/docs/`. The `.nojekyll` marker keeps the HTML and other static assets unprocessed.
Subsequent pushes changing files in `docs/` update the published site automatically.

Source: [GitHub's publishing-source documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).
