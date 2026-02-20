# Insights Page: Technical Documentation & Data Architecture

This document provides a comprehensive overview of the **Insights** page, its underlying data sources, code structure, and analytical logic.

## 1. Objective
The Insights page is designed to surface high-level trends, manager performance benchmarks, and realization data across the venture capital and private equity landscape. It emphasizes **DPI (Distributed-to-Paid-In)** as the primary metric for measuring realized cash outcomes.

---

## 2. Data Sources
The page aggregates data from four primary layers:

1.  **Unified LP Disclosures (`data/unified_funds.csv`)**:
    *   **Sources**: Public pension systems (CalPERS, CalSTRS, WSIB, Florida SBA, etc.) and endowments (UTIMCO, UC Regents).
    *   **Reliability**: High. These figures are reported under legal obligation (FOIA) and reflect actual cash flows to institutional investors.
2.  **Market Intelligence (`gp_disclosed_funds.csv`)**:
    *   **Firms**: a16z, Founders Fund, Social Capital, etc.
    *   **Context**: Circulated through secondary markets or investor channels. Labeled as "unverified" because they are not independently reported by public LPs.
3.  **CA Benchmarks (`ca_benchmarks.csv`)**:
    *   **Origin**: Approximated from public filings and academic literature.
    *   **Usage**: Provides Q1 (Top Quartile) and Median reference lines for IRR and TVPI vs. vintage year.
4.  **Target Firm Patterns (`target_firm_patterns.csv`)**:
    *   Used for canonicalizing GP names (e.g., mapping "Union Square Ventures" and "USV" to the same entity).

---

## 3. Code Architecture (`app.py`)

The logic resides primarily in the `render_insights()` function.

### A. Data Preparation
The function performs the following steps before rendering:
*   **Filtering**: Excludes "meaningless" data (e.g., very recent funds where IRR/DPI is essentially zero or placeholder).
*   **Normalization**: Standardizes IRR percentages and DPI multiples.
*   **Categorization**: Groups funds by strategy (Venture, Growth, PE, etc.).

### B. Visual Components

#### Section 01: Firm Landscape (Bubble Chart)
*   **Logic**: Each bubble is a manager (Canonical GP).
*   **X-Axis**: Number of funds with meaningful data.
*   **Y-Axis**: Median Net DPI across those funds.
*   **Size**: Bubble size corresponds to the total capital (AUM-proxy) represented in the dataset.
*   **Color**: Slate for LP-Disclosed; Orange for Market Intelligence.

#### Section 02: Fund Coverage Timeline (Square Grid)
*   **Logic**: Every fund is a square.
*   **X-Axis**: Vintage Year.
*   **Y-Axis**: Manager Name.
*   **Colors**:
    *   **Orange**: 2.0x+ DPI (Strong Realization)
    *   **Green**: 1.0x - 2.0x DPI (Capital Returned)
    *   **Yellow**: 0.1x - 1.0x DPI (Early distributions)
    *   **Gray**: < 0.1x DPI (Cash-light)

#### Section 03: Returns vs. Benchmarks (Scatter)
*   **Logic**: Plots individual fund IRRs against Cambridge Associates (approximate) benchmark bands.
*   **Highlight**: Identifies "Benchmark Beaters" (funds significantly above the green Q1 band).

#### Section 04: Cash Returned by Strategy (Bar Chart)
*   **Logic**: Aggregates data by fund category (e.g., Early Stage VC, Buyout).
*   **Metric**: Capital-weighted average DPI (larger funds have more influence on the average).

#### Section 05: GP Performance Trajectories (Line Chart)
*   **Logic**: Tracks the IRR and DPI of specific managers over time (e.g., Sequoia Fund I -> Fund II -> Fund III).
*   **Requirement**: Only shows managers with 3+ funds in the dataset to show a meaningful trend.

---

## 4. Key Logic & Analytical Findings
The page surfaces several hardcoded "Key Findings" that are verifiable in the data:
*   **Drought**: Recent vintages (2017+) show almost zero DPI despite high unrealized marks.
*   **Outliers**: Identification of legendary funds like USV 2012 (22.8x DPI) which are visible in LP records.
*   **Selection Bias**: Observation that market-intelligence data tends to cluster above benchmarks compared to FOIA data.

---

## 5. Styling Utility: `style_chart_readability()`
This helper function ensures a consistent professional look across all Plotly charts:
*   **Typography**: Uses "Inter" and "IBM Plex Mono".
*   **Interaction**: Configures `hovermode="closest"` and removes redundant Plotly modebar tools for a cleaner UI.
*   **Margins**: Dynamically calculates spacing to prevent axis title cutoffs.
