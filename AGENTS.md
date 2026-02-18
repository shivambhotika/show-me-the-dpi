# Show Me the DPI — Agent Guide

## Project Name
Show Me the DPI

## Current Project Goal
Provide an analyst-focused Streamlit research tool for exploring LP-disclosed venture/private equity fund performance with consistent fund-level metrics, benchmark context, and source transparency.

## Tech Stack
- Language: Python 3.9
- App framework: Streamlit
- Data processing: pandas
- Visualization: Plotly (`plotly.graph_objects`)
- Database: SQLite (`openlp.db`, fallback `openvc.db`)
- Data ingestion: `pdfplumber`, `beautifulsoup4`, `requests`, regex/text parsing
- Deployment: Streamlit Cloud

## Data Pipeline
`scrapers/*.py` → source CSVs in `data/` → `normalize.py` → `data/unified_funds.csv` → `app.py`

## Current App State
- Sidebar navigation uses non-radio section selection: `OVERVIEW`, `FUND DATABASE`, `FIRMS & FUND FAMILIES`, `SOURCES`, `ABOUT`.
- `OVERVIEW` provides only summary metrics: total funds, funds with DPI available, target firms covered, and data source count.
- `FUND DATABASE` is the raw analyst table with source and vintage filters.
- `FIRMS & FUND FAMILIES` is the primary workflow: target-firm matching from `metadata/target_firms.csv`, canonical GP selection, heuristic fund-family grouping, fund selection, and full metric/benchmark/chart/insight rendering.
- The Firms page includes a coverage strength indicator (`Strong`/`Moderate`/`Thin`) based on matched fund count and LP source breadth.
- `SOURCES` contains source inventory and concise LP disclosure caveats.
- `ABOUT` contains the canonical explanatory copy under a single heading.

## Immediate Next Step
Add a maintained `data/source_metadata.csv` process so the Sources page can be fully data-driven and consistently updated with reporting periods.

## Development Principles
- Keep UI minimal, clean, and analyst-oriented.
- Preserve schema and ingestion contracts.
- Keep metric, benchmark, and chart logic stable unless explicitly requested.
- Target firms should drive fund visibility in research flows.
- Make incremental, low-risk structural changes.

## Known Constraints
- Public LP disclosures vary in format, definitions, and reporting cadence.
- Different LPs may report different values for the same fund/vintage/date window.
- Coverage filtering and fund-family grouping depend on deterministic pattern heuristics in `metadata/target_firms.csv`.
