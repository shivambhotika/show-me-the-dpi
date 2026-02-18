# Show Me the DPI — Agent Guide

## Project Name
Show Me the DPI

## Current Project Goal
Provide an analyst-friendly Streamlit research tool for exploring LP-disclosed
venture/private equity fund performance data, with consistent fund-level metrics
(TVPI, DPI, RVPI, IRR), benchmark context, and clear source attribution.

## Tech Stack
- Language: Python 3.9
- App framework: Streamlit
- Data processing: pandas
- Visualization: Plotly (plotly.graph_objects)
- Database: SQLite (openlp.db, fallback openvc.db)
- Data ingestion: pdfplumber, beautifulsoup4, requests, regex text parsing
- Deployment: Streamlit Cloud
- Automation: intended via GitHub Actions (.github/workflows/scrape.yml), currently run manually.

## Data Pipeline
Individual scrapers in scrapers/ → source CSVs in data/ → normalize.py →
data/unified_funds.csv → app.py

### Scraper Status
| Source | Scraper File | Status | Raw Rows | Notes |
|--------|--------------|--------|----------|------|
| CalPERS | scrapers/calpers.py | Working | 448 | HTML table |
| CalSTRS | scrapers/calstrs.py | Working | 376 | PDF text parsing |
| Oregon Treasury | scrapers/oregon.py | Working | 440 | PDF parsing |
| WSIB | scrapers/wsib.py | Working | 468 | pdfplumber |
| UTIMCO | scrapers/utimco.py | Broken | 3 | wrong PDF |
| PSERS | scrapers/psers.py | Broken | 0 | manual download needed |

### normalize.py Status — ACTIVE BUGS
- Column mapping failures reduce rows drastically.
- DPI missing due to missing derived calculations.
- Dedup currently too aggressive.

### Unified Schema
fund_name, vintage_year, capital_committed, capital_contributed,
capital_distributed, nav, net_irr, tvpi, dpi, source, scraped_date, reporting_period

### Derived Rules
- dpi = capital_distributed / capital_contributed
- tvpi = (capital_distributed + nav) / capital_contributed
- Dedup key: fund_name + vintage_year + source + reporting_period

## Current App State
- Sidebar navigation: DATABASE / FUND DETAIL / ABOUT
- DATABASE tab has nested Fund Data + Resources
- FUND DETAIL metrics + quartiles + charts active
- ABOUT page canonical copy complete

## Immediate Next Steps
1. Fix normalize.py mapping issues
2. Fix UTIMCO source
3. Add PSERS local PDF parsing
4. Create data/source_metadata.csv
5. Replace hardcoded benchmarks with dataset quartiles

## Development Principles
- Keep UI minimal and analyst-oriented
- Preserve schema and ingestion contracts
- Safe numeric handling
- Source transparency everywhere
- Incremental changes only
