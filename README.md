# show-me-the-dpi
Venture fund returns basis open available data

## Deployment

This repo now includes two app entrypoints:

- `app.py`: Flask app for Vercel. Vercel should detect the top-level `app` variable automatically.
- `streamlit_app.py`: legacy Streamlit app for Streamlit Community Cloud or local Streamlit runs. Use `requirements-streamlit.txt` for that version.

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

`approve` only creates an immutable snapshot when the audit has no critical findings. There is no scheduled auto-publish workflow.
