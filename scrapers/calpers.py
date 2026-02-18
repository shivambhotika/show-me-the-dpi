import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import date
import os

def scrape_calpers():
    url = "https://www.calpers.ca.gov/investments/about-investment-office/investment-organization/pep-fund-performance-print"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"CalPERS fetch failed: {e}")
        return None

    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find("table")
    
    if not table:
        print("No table found on CalPERS page")
        return None

    df = pd.read_html(str(table))[0]
    
    # Flatten multi-level columns if they exist
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ['_'.join(col).strip() for col in df.columns]
    
    # Rename columns to standard names
    df.columns = [str(c).lower().strip().replace(" ", "_") for c in df.columns]
    
    # Add metadata
    df["source"] = "CalPERS"
    df["scraped_date"] = str(date.today())
    
    # Remove rows that are headers or footnotes repeated in body
    if "fund_name" in df.columns:
        df = df[df["fund_name"].notna()]
        df = df[~df["fund_name"].astype(str).str.contains("Fund Name|CalPERS|Total|Note|^1", na=True)]
    
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/calpers.csv", index=False)
    print(f"CalPERS: saved {len(df)} rows to data/calpers.csv")
    return df

if __name__ == "__main__":
    scrape_calpers()
