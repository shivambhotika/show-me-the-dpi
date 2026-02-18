import requests
import pdfplumber
import pandas as pd
from bs4 import BeautifulSoup
from io import BytesIO
from datetime import date
import os

def get_latest_utimco_pdf_url():
    """Find the latest UTIMCO performance summary PDF."""
    index_url = "https://www.utimco.org/reports/investment-performance-statistics/"
    
    try:
        response = requests.get(index_url, timeout=30)
        soup = BeautifulSoup(response.content, "html.parser")
        
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if ".pdf" in href.lower() and "performance" in href.lower():
                if not href.startswith("http"):
                    href = "https://www.utimco.org" + href
                return href
    except Exception as e:
        print(f"Could not auto-detect UTIMCO PDF URL: {e}")
    
    # Fallback to known recent URL
    return "https://www.utimco.org/media/4479/202411-monthly-performance-summary-final.pdf"

def scrape_utimco():
    pdf_url = get_latest_utimco_pdf_url()
    print(f"UTIMCO PDF URL: {pdf_url}")
    
    try:
        response = requests.get(pdf_url, timeout=60)
        response.raise_for_status()
    except Exception as e:
        print(f"UTIMCO PDF fetch failed: {e}")
        return None

    all_rows = []
    current_section = "unknown"
    
    with pdfplumber.open(BytesIO(response.content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            
            # Track whether we're in Active or Inactive section
            if "Active Relationships" in text:
                current_section = "active"
            elif "Inactive Relationships" in text:
                current_section = "inactive"
            
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row and any(cell for cell in row if cell):
                        row_with_meta = row + [current_section]
                        all_rows.append(row_with_meta)

    if not all_rows:
        print("No tables found in UTIMCO PDF")
        return None

    max_cols = max(len(row) for row in all_rows)
    all_rows = [row + [None] * (max_cols - len(row)) for row in all_rows]
    
    df = pd.DataFrame(all_rows)
    
    # Detect header row
    for i, row in df.iterrows():
        row_str = " ".join([str(v).lower() for v in row if v])
        if "invested" in row_str or "returned" in row_str or "irr" in row_str:
            df.columns = df.iloc[i].tolist()[:-1] + ["relationship_status"]
            df = df.iloc[i+1:].reset_index(drop=True)
            break
    
    df.columns = [str(c).lower().strip().replace(" ", "_").replace("/", "_") if c else f"col_{i}"
                  for i, c in enumerate(df.columns)]
    
    # Filter out blank or header-repeat rows
    # UTIMCO rows have fund names in first column — remove rows where it's blank or numeric
    first_col = df.columns[0]
    df = df[df[first_col].notna()]
    df = df[~df[first_col].astype(str).str.match(r'^\d+\.?\d*$', na=False)]
    df = df[df[first_col].astype(str).str.len() > 3]
    
    df["source"] = "UTIMCO"
    df["scraped_date"] = str(date.today())
    df["reporting_period"] = pdf_url.split("/")[-1].replace("-monthly-performance-summary-final.pdf", "")
    
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/utimco.csv", index=False)
    print(f"UTIMCO: saved {len(df)} rows to data/utimco.csv")
    return df

if __name__ == "__main__":
    scrape_utimco()
