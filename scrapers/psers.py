import requests
import pdfplumber
import pandas as pd
from bs4 import BeautifulSoup
from io import BytesIO
from datetime import date
import os

PSERS_ARCHIVE_URLS = [
    "https://www.psers.pa.gov/About/Investment/Archive/Pages/Fiscal-Year-2024-2025.aspx",
    "https://www.psers.pa.gov/About/Investment/Archive/Pages/Fiscal-Year-2023-2024.aspx",
    "https://www.psers.pa.gov/About/Investment/Archive/Pages/Fiscal-Year-2022-2023.aspx",
]

def get_latest_psers_pdf_url():
    """Find the most recent Private Equity performance PDF from PSERS archive pages."""
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    
    for archive_url in PSERS_ARCHIVE_URLS:
        try:
            response = requests.get(archive_url, headers=headers, timeout=30)
            soup = BeautifulSoup(response.content, "html.parser")
            
            for link in soup.find_all("a", href=True):
                href = link["href"]
                text = link.get_text().lower()
                if ".pdf" in href.lower() and "private equity" in text and "investment performance" in text:
                    if not href.startswith("http"):
                        href = "https://www.psers.pa.gov" + href
                    print(f"Found PSERS PDF: {href}")
                    return href
        except Exception as e:
            print(f"Could not fetch PSERS archive page {archive_url}: {e}")
            continue
    
    # Fallback to known URL pattern
    return "https://psers.pa.gov/About/Investment/Documents/performance/PMREreports/2024%203Q%20-%20PE%20Final.pdf"

def scrape_psers():
    pdf_url = get_latest_psers_pdf_url()
    print(f"PSERS PDF URL: {pdf_url}")
    
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        response = requests.get(pdf_url, headers=headers, timeout=60)
        response.raise_for_status()
    except Exception as e:
        print(f"PSERS PDF fetch failed: {e}")
        return None

    all_rows = []

    with pdfplumber.open(BytesIO(response.content)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row and any(cell for cell in row if cell):
                        all_rows.append(row)

    if not all_rows:
        print("No tables extracted from PSERS PDF")
        return None

    max_cols = max(len(row) for row in all_rows)
    all_rows = [row + [None] * (max_cols - len(row)) for row in all_rows]
    df = pd.DataFrame(all_rows)

    # Detect and set header row
    for i, row in df.iterrows():
        row_str = " ".join([str(v).lower() for v in row if v])
        if "vintage" in row_str or "irr" in row_str or "committed" in row_str or "fund" in row_str:
            df.columns = df.iloc[i]
            df = df.iloc[i+1:].reset_index(drop=True)
            break

    df.columns = [
        str(c).lower().strip().replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "")
        if c else f"col_{i}"
        for i, c in enumerate(df.columns)
    ]

    # Keep rows that look like fund data — first column should be a fund name (non-numeric, length > 3)
    first_col = df.columns[0]
    df = df[df[first_col].notna()]
    df = df[~df[first_col].astype(str).str.match(r'^\d+\.?\d*$', na=False)]
    df = df[df[first_col].astype(str).str.len() > 3]
    df = df[~df[first_col].astype(str).str.lower().str.contains("total|subtotal|note|fund name", na=False)]

    df["source"] = "PSERS"
    df["scraped_date"] = str(date.today())
    df["reporting_period"] = pdf_url.split("/")[-1].replace(".pdf", "").replace("%20", " ")

    os.makedirs("data", exist_ok=True)
    df.to_csv("data/psers.csv", index=False)
    print(f"PSERS: saved {len(df)} rows to data/psers.csv")
    return df

if __name__ == "__main__":
    scrape_psers()
