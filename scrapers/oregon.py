import requests
import pdfplumber
import pandas as pd
from bs4 import BeautifulSoup
from io import BytesIO
from datetime import date, datetime
import os

OREGON_INDEX_URL = "https://www.oregon.gov/treasury/invested-for-oregon/pages/performance-holdings.aspx"

def get_latest_oregon_pdf_url():
    """Dynamically find the latest OPERF Private Equity quarterly PDF."""
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    
    try:
        response = requests.get(OREGON_INDEX_URL, headers=headers, timeout=30)
        soup = BeautifulSoup(response.content, "html.parser")
        
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "private_equity" in href.lower() or "privateequity" in href.lower() or \
               ("operf" in href.lower() and "private" in href.lower()):
                if ".pdf" in href.lower():
                    if not href.startswith("http"):
                        href = "https://www.oregon.gov" + href
                    return href
    except Exception as e:
        print(f"Could not auto-detect Oregon PDF URL: {e}")

    # Fallback — construct URL for most recent known quarter
    year = datetime.now().year
    quarter = ((datetime.now().month - 1) // 3)  # Current quarter minus 1 for lag
    if quarter == 0:
        quarter = 4
        year -= 1
    
    fallback = (
        f"https://www.oregon.gov/treasury/invested-for-oregon/Documents/"
        f"Invested-for-OR-Performance-and-Holdings/{year}/"
        f"OPERF_Private_Equity_Portfolio_-_Quarter_{quarter}_{year}.pdf"
    )
    print(f"Using fallback Oregon URL: {fallback}")
    return fallback

def scrape_oregon():
    pdf_url = get_latest_oregon_pdf_url()
    print(f"Oregon PDF URL: {pdf_url}")

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        response = requests.get(pdf_url, headers=headers, timeout=60)
        response.raise_for_status()
    except Exception as e:
        print(f"Oregon PDF fetch failed: {e}")
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
        print("No tables extracted from Oregon PDF")
        return None

    max_cols = max(len(row) for row in all_rows)
    all_rows = [row + [None] * (max_cols - len(row)) for row in all_rows]
    df = pd.DataFrame(all_rows)

    # Detect header row — Oregon PDFs typically have Fund Name, Vintage, Committed, TVPI, IRR
    for i, row in df.iterrows():
        row_str = " ".join([str(v).lower() for v in row if v])
        if "vintage" in row_str or "tvpi" in row_str or "irr" in row_str:
            df.columns = df.iloc[i]
            df = df.iloc[i+1:].reset_index(drop=True)
            break

    df.columns = [
        str(c).lower().strip().replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "").replace(".", "")
        if c else f"col_{i}"
        for i, c in enumerate(df.columns)
    ]

    # Oregon marks non-meaningful values as "NM" — keep those rows, just flag them
    first_col = df.columns[0]
    df = df[df[first_col].notna()]
    df = df[~df[first_col].astype(str).str.match(r'^\d+\.?\d*$', na=False)]
    df = df[df[first_col].astype(str).str.len() > 3]
    df = df[~df[first_col].astype(str).str.lower().str.contains("total|fund name|partnership|note|warning", na=False)]

    df["source"] = "Oregon OPERF"
    df["scraped_date"] = str(date.today())
    df["reporting_period"] = pdf_url.split("/")[-1].replace(".pdf", "").replace("_", " ")

    os.makedirs("data", exist_ok=True)
    df.to_csv("data/oregon.csv", index=False)
    print(f"Oregon: saved {len(df)} rows to data/oregon.csv")
    return df

if __name__ == "__main__":
    scrape_oregon()
