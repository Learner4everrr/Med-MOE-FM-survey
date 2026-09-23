# Med-MoE-FM Evidence Map

An interactive companion website for the scoping review **Mixture-of-experts in medical foundation models**.

The site presents 90 included studies through searchable study cards, architecture filters, publication trends, application summaries, and evidence-maturity views. It is a static website designed for GitHub Pages and requires no server or database.

## Public website

After GitHub Pages is enabled, the site will be available at:

`https://learner4everrr.github.io/Med-MOE-FM-survey/`

## Repository structure

```text
index.html                     Website content
styles.css                    Visual design and responsive layout
app.js                        Charts, filters, and study explorer
data/studies.json             Copyright-clean public study-level data
scripts/build-public-data.mjs Reproducible CSV-to-JSON export
```

## Data scope

The public JSON contains bibliographic metadata and structured categorical or quantitative study characteristics. It intentionally excludes:

- article abstracts;
- full-text evidence excerpts;
- publisher PDFs;
- local workflow fields, file paths, and extraction diagnostics.

## Rebuild the public data

From the repository root:

```bash
node scripts/build-public-data.mjs /path/to/Supplementary_Material_2.csv data/studies.json
```

The export script explicitly selects the public fields, so private or copyrighted source-text columns are not carried into the website dataset.

## Local preview

Any static web server can be used. For example:

```bash
python -m http.server 8000
```

Then open `http://localhost:8000`.

## Citation and preservation

Citation metadata are provided in `CITATION.cff`. A versioned GitHub release can be archived through Zenodo to obtain a persistent DOI.

## Licenses

- Website source code: MIT License.
- Structured public dataset: CC BY 4.0; see `DATA_LICENSE.md`.
