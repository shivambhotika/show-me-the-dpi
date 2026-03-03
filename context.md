# Show Me the DPI - Full Project Context

Last updated: 2026-03-04 (local snapshot)

## 1. What this project is
Show Me the DPI is an analyst-oriented Streamlit application for evaluating VC/PE fund outcomes using public LP disclosures plus clearly-labeled market-intelligence records.

Primary question: how much cash has actually been returned to LPs?

Primary metric: DPI (Distributed to Paid-In).

Core product principle: DPI first (realized cash), TVPI and IRR as context.

## 2. What is in this repo (and what is not)
This repository is `show-me-the-dpi`.

It is not the `under-the-hood` repo/tool-intelligence app.

Key files:
- `app.py`: entire Streamlit app (routing, views, charts, styling, logic).
- `normalize.py`: source CSV normalization into canonical LP dataset.
- `data/`: source and normalized datasets.
- `scrapers/`: source ingestion scripts.
- `metadata/target_firms.csv`: GP matching patterns.
- `AGENTS.md`: current high-level project guidance.

## 3. Data flow end-to-end
Pipeline:
1. Scrapers populate source CSVs in `data/`.
2. `normalize.py` standardizes columns and derives missing metrics.
3. Output is written to `data/unified_funds.csv`.
4. App loads `data/vc_fund_master.csv` as primary modeled dataset.
5. App optionally merges selected columns from `data/unified_funds.csv` into master.
6. App renders tabs: ABOUT, INSIGHTS, TOP FIRMS, FUND DATABASE, SOURCES.

## 4. Canonical schema and keys
`normalize.py` canonical output schema (`UNIFIED_COLUMNS`):
- `fund_name`
- `vintage_year`
- `capital_committed`
- `capital_contributed`
- `capital_distributed`
- `nav`
- `net_irr`
- `tvpi`
- `dpi`
- `source`
- `scraped_date`
- `reporting_period`

Dedup key used in normalization:
- `fund_name + vintage_year + source + reporting_period`

## 5. Metric formulas and transformations

### 5.1 Normalization math (`normalize.py`)
- DPI derive when missing:
  - `dpi = capital_distributed / capital_contributed` (when contributed > 0)
- TVPI derive when missing:
  - `tvpi = (capital_distributed + nav) / capital_contributed` (when contributed > 0)
- NAV fallback when missing:
  - `nav = total_value - capital_distributed` (if both exist)
- IRR scale normalization:
  - if median IRR looks percentage-scale (`>1.5`), divide by 100.
- Vintage fallback:
  - inferred from fund name using year regex if missing.

### 5.2 App-level data logic (`app.py`)
Main loader `load_data()`:
- Reads `data/vc_fund_master.csv`.
- Drops `Accel-KKR` rows.
- Drops `fund_category == 'PE'` rows from aggregate views.
- Requires valid `vintage_year`.
- Left-joins some fields from `data/unified_funds.csv` on `fund_name + vintage_year`.
- Re-derives missing `dpi` and `tvpi` from contributed/distributed/nav if needed.
- CalPERS cleanup: `net_irr == 1.0` treated as placeholder -> null.

## 6. Source universe and classifications

### 6.1 LP-disclosed source config (`SOURCES_CONFIG`)
- CalPERS
- CalSTRS
- Oregon Treasury
- WSIB
- UC Regents
- Massachusetts PRIM
- Florida SBA
- Louisiana TRSL
- UTIMCO

### 6.2 Market-intelligence source config (`GP_SOURCES_CONFIG`)
- a16z Firm Disclosure
- Founders Fund Firm Disclosure
- Social Capital Firm Disclosure

## 7. GP matching and category logic

### 7.1 GP mapping
The app builds a focus universe via:
- `metadata/target_firms.csv` patterns (if present), plus
- hardcoded `FOCUS_FIRM_SPECS` regex-like include patterns.

Matching function:
- First pass: deterministic substring/token checks.
- Fallback: strict fuzzy match (`SequenceMatcher`) only for hard misses.

### 7.2 Fund category inference (`_infer_category_from_name`)
Name-based heuristic:
- contains `opportun` -> Opportunities
- contains `growth` -> Growth
- contains PE-like terms (`buyout`, `credit`, `distress`, `special situations`, `structured`) -> PE
- else -> Venture

## 8. App routes and what each tab does

### 8.1 ABOUT
- Explains project framing, methodology, and limitations.
- Reinforces DPI-first interpretation.

### 8.2 INSIGHTS
Data basis:
- LP slice: `data_source_type == 'LP-Disclosed'`.
- Uses benchmark file `ca_benchmarks.csv` for context bands (approximate).

Hero stats logic:
- Funds indexed: `len(df_master)`.
- Post-2017 drought: percent of LP funds with `vintage_year >= 2017` and `dpi < 0.5`.
- Highest LP-disclosed DPI: top LP fund by DPI.
- a16z fee-drag tile: hardcoded `4.4x` narrative for Fund III.

Sections/charts:
1. DPI by Vintage:
   - bar = median DPI by vintage.
   - dotted line = median TVPI by vintage.
   - filtered to years 2007..2022 and at least 3 funds per year.
2. Cash Return Leaders:
   - top 10 LP funds by DPI (table style leaderboard).
3. Paper vs Cash:
   - stacked bars: median DPI + unrealized component (`TVPI - DPI`) by vintage.
4. Gross-Net Gap (a16z):
   - hardcoded fund list comparing gross TVPI, net TVPI, net DPI.
5. Within-Manager Variance:
   - UTIMCO-only manager IRR min-max ranges (managers with >=2 funds).

### 8.3 TOP FIRMS
- Uses focus-master dataset (master + mapped LP additions).
- Grid cards per GP with median DPI, vintage span, AUM/founded/hq metadata.
- Detail panel per selected GP:
  - LP managers: median TVPI, median DPI, best IRR, funds tracked.
  - MI managers: gross/net variants when available.
  - Fund-level table with meaningful/too-early status.

### 8.4 FUND DATABASE
- Builds a combined display from:
  - LP table conversion (`_to_database_lp_df`) and
  - MI conversion (`_to_database_market_intel_df`).
- Filters: search, source, vintage.
- Sort: DPI desc, then TVPI desc.
- Pagination: 25 rows/page.

### 8.5 SOURCES
- Methodology narrative.
- LP source ledger table with configured coverage percentages.
- Market-intel source ledger with separate treatment.
- Benchmark provenance and cautions.
- Data quality notes.

## 9. Current dataset snapshot (from local files)
Computed from current local files on 2026-03-04.

### 9.1 Raw files
- `data/vc_fund_master.csv`: 196 rows raw.
- After app loader filters (drop Accel-KKR, drop PE, require vintage): 179 rows.
- `data/unified_funds.csv`: 2,801 rows.
- `gp_disclosed_funds.csv`: 24 rows.
- `ca_benchmarks.csv`: 24 rows (vintages 2000-2023).

### 9.2 Master mix and coverage
- Firms tracked (filtered master): 38.
- Source-type mix in filtered master:
  - LP-Disclosed: 155
  - GP-Disclosed: 24
- Top source counts in filtered master:
  - UTIMCO: 56
  - UC Regents: 49
  - CalPERS: 39
  - Founders Fund Firm Disclosure: 10
  - a16z Firm Disclosure: 9
  - Oregon Treasury: 7
  - Social Capital Firm Disclosure: 5

### 9.3 Unified coverage quality
- Rows with DPI: 2,284
- Rows with TVPI: 2,289
- Rows with IRR: 2,485
- Duplicate rows on dedup key: 0

Rows per source in `data/unified_funds.csv`:
- WSIB: 464
- CalPERS: 448
- Oregon Treasury: 440
- Florida SBA: 433
- CalSTRS: 376
- Massachusetts PRIM: 219
- Louisiana TRSL: 202
- UC Regents: 148
- UTIMCO: 71

### 9.4 Insights-level outputs (current)
- Post-2017 LP drought metric: 95% (`dpi < 0.5x`), sample size 91.
- Top LP DPI fund currently:
  - Union Square Ventures 2012 Fund L.P. at 22.86x DPI.

Top LP DPI examples:
- Union Square Ventures 2012 Fund L.P. (22.86x)
- Founders Fund II (18.6x)
- Union Square Ventures 2004 L.P. (13.82x)
- Founders Fund I (7.7x)
- Founders Fund IV (6.2x)

## 10. Known logic gaps and risks (important for next agent)

1. Source-type label mismatch
- Data has `GP-Disclosed` in master.
- Multiple UI branches check for `Market Intelligence` exactly.
- Effect: `load_market_intel()` currently returns zero rows; some MI-specific UI paths can under-render.

2. Fund Database feed duplication risk
- `load_unified()` is an alias to `load_data()` (master-like table), not raw `data/unified_funds.csv`.
- Then `_to_database_lp_df` marks that full frame as LP and concatenates MI frame again.
- This can blur LP vs MI boundaries in the database tab.

3. Dual sources of truth
- `gp_disclosed_funds.csv` exists but the app primarily reads `data/vc_fund_master.csv`.
- If these diverge, UI behavior follows master, not the standalone MI csv.

4. Hardcoded narrative constants
- a16z fee-drag hero uses fixed value `4.4x` and a hardcoded fund list.
- If source data changes, narrative can drift from dataset.

5. Matching sensitivity
- GP mapping uses pattern heuristics plus fuzzy fallback.
- False positives/negatives remain possible (already noted in AGENTS immediate next steps).

## 11. How to run and regenerate

### 11.1 Normalize LP data
- `python3 normalize.py`
- Diagnostics only: `python3 normalize.py --diagnose`

### 11.2 Run app
- `streamlit run app.py`

### 11.3 Optional audit screen
- App has `render_audit()` utility for validation checks, but it is not in top nav.

## 12. Where to change what
- Source mapping, derived metric logic, dedup: `normalize.py`
- UI pages, chart logic, routing, data loading: `app.py`
- GP matching patterns: `metadata/target_firms.csv` + `FOCUS_FIRM_SPECS` in `app.py`
- Benchmarks: `ca_benchmarks.csv`
- LP source datasets: `data/*.csv`
- Market-intel seed file: `gp_disclosed_funds.csv`

## 13. Practical handoff guidance for next agent
If a new agent needs to improve reliability fastest, do this order:
1. Unify `data_source_type` vocabulary (`GP-Disclosed` vs `Market Intelligence`) in one place.
2. Make `load_unified()` load true normalized LP file (not master alias).
3. Separate LP and MI data pipelines cleanly in Fund Database tab.
4. Add a small automated validation script that checks:
   - source-type values in master,
   - non-empty MI slice,
   - no duplicate dedup keys,
   - no impossible DPI > TVPI cases.

That sequence removes most confusion and makes charts/tables match analyst intent.
