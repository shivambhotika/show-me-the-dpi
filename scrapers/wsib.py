import requests
import pdfplumber
import pandas as pd
from bs4 import BeautifulSoup
from io import BytesIO
from datetime import date, datetime
import os

WSIB_REPORTS_URL = "https://www.sib.wa.gov/reports"

def get_latest_wsib_pdf_url():
    """Find the latest WSIB quarterly IRR report PDF."""
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    
    try:
        response = requests.get(WSIB_REPORTS_URL, headers=headers, timeout=30)
        soup = BeautifulSoup(response.content, "html.parser")
        
        for link in soup.find_all("a", href=True):
            href = link["href"]
            # IRR reports follow pattern ir[date].pdf
            if "/quarterly/ir" in href.lower() and ".pdf" in href.lower():
                if not href.startswith("http"):
                    href = "https://www.sib.wa.gov" + href
                return href
    except Exception as e:
        print(f"Could not auto-detect WSIB PDF URL: {e}")

    # Fallback — construct URL for most recent known quarter
    # Pattern: ir[MM][DD][YY].pdf — e.g. September 30 2024 = ir093024.pdf
    # Try the last few known quarters
    fallbacks = [
        "https://www.sib.wa.gov/docs/reports/quarterly/ir093024.pdf",  # Sep 2024
        "https://www.sib.wa.gov/docs/reports/quarterly/ir063024.pdf",  # Jun 2024
        "https://www.sib.wa.gov/docs/reports/quarterly/ir123124.pdf",  # Dec 2024
    ]
    
    for url in fallbacks:
        try:
            r = requests.head(url, headers=headers, timeout=10)
            if r.status_code == 200:
                print(f"Using WSIB fallback URL: {url}")
                return url
        except:
            continue
    
    return fallbacks[0]

def scrape_wsib():
    pdf_url = get_latest_wsib_pdf_url()
    print(f"WSIB PDF URL: {pdf_url}")

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        response = requests.get(pdf_url, headers=headers, timeout=60)
        response.raise_for_status()
    except Exception as e:
        print(f"WSIB PDF fetch failed: {e}")
        return None

    all_rows = []
    current_strategy = "unknown"

    with pdfplumber.open(BytesIO(response.content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            
            # Track strategy section (Buyout, Venture Capital, Growth Equity, etc.)
            for strategy_keyword in ["Venture Capital", "Growth Equity", "Buyout", 
                                      "Distressed", "Special Situations", "Credit"]:
                if strategy_keyword in text:
                    current_strategy = strategy_keyword
            
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row and any(cell for cell in row if cell):
                        all_rows.append(row + [current_strategy])

    if not all_rows:
        print("No tables extracted from WSIB PDF")
        return None

    max_cols = max(len(row) for row in all_rows)
    all_rows = [row + [None] * (max_cols - len(row)) for row in all_rows]
    df = pd.DataFrame(all_rows)

    # Detect header row
    for i, row in df.iterrows():
        row_str = " ".join([str(v).lower() for v in row if v])
        if "irr" in row_str or "committed" in row_str or "partnership" in row_str or "fund" in row_str:
            cols = df.iloc[i].tolist()
            cols[-1] = "strategy_type"
            df.columns = cols
            df = df.iloc[i+1:].reset_index(drop=True)
            break

    df.columns = [
        str(c).lower().strip().replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "").replace(".", "").replace(",", "")
        if c else f"col_{i}"
        for i, c in enumerate(df.columns)
    ]

    first_col = df.columns[0]
    df = df[df[first_col].notna()]
    df = df[~df[first_col].astype(str).str.match(r'^\d+\.?\d*$', na=False)]
    df = df[df[first_col].astype(str).str.len() > 3]
    df = df[~df[first_col].astype(str).str.lower().str.contains("total|subtotal|partnership name|note|fund name", na=False)]

    df["source"] = "WSIB"
    df["scraped_date"] = str(date.today())
    df["reporting_period"] = pdf_url.split("/")[-1].replace(".pdf", "")

    os.makedirs("data", exist_ok=True)
    df.to_csv("data/wsib.csv", index=False)
    print(f"WSIB: saved {len(df)} rows to data/wsib.csv")
    return df

if __name__ == "__main__":
    scrape_wsib()
