# show-me-the-dpi
Venture fund returns basis open available data

## Deployment

The supported product is the Flask app deployed on Vercel. `app.py` is the
single production entrypoint and `vercel.json` makes the Python runtime and
catch-all route explicit. The former Streamlit implementation is not part of
the Vercel build or refresh workflow and is intentionally left untouched.

Local smoke test:

```bash
python3 -m unittest discover -s tests -v
python3 -m flask --app app run
```

Firm logos use logo.dev. The Vercel app includes a publishable fallback key, and you can override it with:

```bash
LOGO_DEV_PUBLIC_KEY=your_logo_dev_publishable_key
```

Do not commit secret `sk_` tokens to GitHub. Secret tokens are only supported via `LOGO_DEV_TOKEN` for the optional `/logo/...` proxy.

## Data Ingestion Pipeline
Run the full ingestion + load process with:

```bash
python data_pipeline/build_db.py
```

What it does:
- Ingests CalPERS from the provided local HTML file.
- Ingests PSERS from the provided local PDF file using `pdfplumber` table extraction.
- Ingests Founders Fund rows from a manual inline table (no OCR).
- Normalizes all sources into a canonical dataframe.
- Writes canonical output to `data/unified_funds.csv`.
- Upserts into the existing SQLite `funds` table with de-duplication on `fund_name + vintage_year + source`.

Expected outputs:
- `data/ingested_calpers.csv`
- `data/ingested_psers.csv`
- `data/ingested_founders_fund.csv`
- `data/unified_funds.csv`
- Updated rows in `openlp.db` (or `openvc.db` if present)

## Integrity and manual refresh

Run the reproducible audit before publishing a data change:

```bash
python3 scripts/audit_data.py
```

The audit writes a dated row-level report under `data/audits/`. Reported source values are preserved; basis mismatches and impossible relationships are surfaced for review.

Manual refresh commands:

```bash
python3 scripts/refresh.py check
python3 scripts/refresh.py audit
python3 scripts/refresh.py approve
```

`check` also probes the configured benchmark/source pages and writes a dated
source report plus a row-level new/changed/removed diff. Use
`--skip-source-check` only for offline development. Benchmark observations in
`data/benchmark_observations.csv` are context-only and are never merged into
the verified fund-level dataset.

The Insights page supports venture filters for vintage, fund sequence, stage,
geography, fund-size band, source type, and verification state. It keeps
fund-weighted medians, capital-weighted averages, percentile ranges, and
source-specific observations visibly separate.

`approve` only creates an immutable snapshot when the audit has no blocking
schema or calculation failures. Documented source-basis disputes remain
visible, are excluded from verified rankings, and are carried into the
snapshot report. There is no scheduled auto-publish workflow.

## Vercel-only operating model

- Deploy from the repository root using the Flask entrypoint.
- Use `/healthz` as the deployment smoke check.
- Do not install Streamlit or run the old Streamlit entrypoints.
- Run refresh, audit, review, and approval manually; a deployment never
  mutates the data snapshot.
