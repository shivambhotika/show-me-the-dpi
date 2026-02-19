# Show Me the DPI — Agent Guide

## Project Name
Show Me the DPI

## Current Project Goal
Provide an analyst-focused Streamlit research tool for evaluating VC/PE fund performance using LP-disclosed data, with explicit source attribution, benchmark context, and a separate market-intelligence lens.

## Tech Stack
- Language: Python 3.9
- App framework: Streamlit
- Data processing: pandas, numpy
- Visualization: Plotly (`plotly.express`, `plotly.graph_objects`)
- Database: SQLite (`openlp.db`, fallback `openvc.db`) used as legacy/fallback in project context
- Data ingestion/parsing: `requests`, `beautifulsoup4`, `pdfplumber`
- Deployment: Streamlit Cloud / GitHub-based deploy flow

## Data Pipeline
`scrapers/*.py` -> source CSVs in `data/` -> `normalize.py` -> `data/unified_funds.csv` -> `app.py`

### Current normalize.py behavior
- Loads configured source files (CalPERS, CalSTRS, Oregon Treasury, WSIB, UTIMCO processed file, optional PSERS, UC Regents, Massachusetts PRIM, Florida SBA, Louisiana TRSL).
- Supports `--diagnose` mode to print per-file diagnostics and exit.
- Applies source mapping (explicit UTIMCO mapping + generic mapping), then derives missing `dpi`/`tvpi`.
- Uses dedup key: `fund_name + vintage_year + source + reporting_period`.
- Writes canonical output only to `data/unified_funds.csv` with schema:
  - `fund_name, vintage_year, capital_committed, capital_contributed, capital_distributed, nav, net_irr, tvpi, dpi, source, scraped_date, reporting_period`

## Current App State
- Top navigation tabs (left-to-right): `ABOUT`, `INSIGHTS`, `TOP FIRMS`, `FUND DATABASE`, `SOURCES`.
- Custom compact header/footer; no legacy static "PUBLIC LP DISCLOSURE RESEARCH · 2,730 FUNDS" text.

### Fund Database
- Unified table combining LP-disclosed data (`unified_funds.csv`) and market-intelligence rows (`gp_disclosed_funds.csv`).
- Market-intelligence context shown in collapsed explainer.
- Sorting emphasizes DPI, with pagination and source/source-type badges.

### Top Firms
- Driven by `vc_fund_master.csv` and augmented matching from unified data.
- Excludes Accel-KKR from Accel-focused coverage.
- Firm detail metrics and fund tables retained.

### Insights
- Uses `vc_fund_master.csv` + `ca_benchmarks.csv`.
- Includes benchmark overlays and market-intelligence vs LP comparison.
- `01 / FIRM LANDSCAPE` now stacks charts vertically for readability.
- Global chart readability improvements applied (axis spacing, automargins, legend placement, improved hover text).
- Includes developer expander for incomplete rows (missing vintage year or contributed capital) sourced from unified data.

### Sources
- Separates LP-disclosed source ledger from market-intelligence sources.
- Includes benchmark provenance section for CA-approximate benchmark dataset.

## Immediate Next Step
1. Improve entity matching quality for canonical GP assignment (reduce false positives/false negatives in coverage).
2. Improve UTIMCO/WSIB row-level enrichment for missing vintage/contribution fields.
3. Add lightweight automated validation checks for chart input completeness after normalization.

## Development Principles
- Keep UI minimal, legible, and analyst-oriented.
- Preserve unified schema contract and backward-compatible CSV outputs.
- Keep LP-disclosed and market-intelligence data clearly labeled and distinguishable in analysis.
- Favor deterministic transformations and explicit diagnostics over opaque heuristics.
- Make incremental changes; avoid routing/layout rewrites unless explicitly requested.

## Known Constraints
- Source disclosures vary by format, definitions, and reporting cadence.
- Same fund can differ across LP reporters due to valuation dates and accounting treatment.
- Market-intelligence records are directional and may include provenance uncertainty or selection bias.
- Missing vintage/contribution values are expected in some sources and should be surfaced, not silently dropped.
