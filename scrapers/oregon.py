import re
import requests
import pandas as pd
from io import BytesIO
import pdfplumber

def scrape_oregon():
    url = "https://www.oregon.gov/treasury/invested-for-oregon/Documents/Invested-for-OR-Performance-and-Holdings/2025/OPERF_Private_Equity_Portfolio_-_Quarter_3_2025.pdf"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)

    rows = []
    # Pattern: optional * | vintage year | fund name | 4 numbers | multiple | IRR
    pattern = re.compile(
        r'^\*?\s*(\d{4})\s+(.+?)\s+\$([\d,]+\.?\d*)\s+\$([\d,]+\.?\d*)\s+\$([\d,]+\.?\d*)\s+\$([\d,]+\.?\d*)\s+([\d.]+x)\s*([\d.\-]+%|n\.m\.)?'
    )

    with pdfplumber.open(BytesIO(r.content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            for line in text.split("\n"):
                line = line.strip()
                m = pattern.match(line)
                if not m:
                    continue
                vintage_year = m.group(1)
                fund_name    = m.group(2).strip()
                committed    = float(m.group(3).replace(",", ""))
                contributed  = float(m.group(4).replace(",", ""))
                distributed  = float(m.group(5).replace(",", ""))
                nav          = float(m.group(6).replace(",", ""))
                tvpi_raw     = m.group(7).replace("x", "")
                tvpi         = float(tvpi_raw) if tvpi_raw else None
                irr_raw      = m.group(8) if m.group(8) else None
                if irr_raw and irr_raw != "n.m.":
                    net_irr = float(irr_raw.replace("%", "")) / 100
                else:
                    net_irr = None

                rows.append({
                    "fund_name":          fund_name,
                    "vintage_year":       int(vintage_year),
                    "capital_committed":  committed,
                    "capital_contributed": contributed,
                    "capital_distributed": distributed,
                    "nav":                nav,
                    "tvpi":               tvpi,
                    "net_irr":            net_irr,
                    "source":             "Oregon Treasury",
                    "reporting_period":   "2025-Q3",
                    "scraped_date":       pd.Timestamp.today().date().isoformat(),
                })

    df = pd.DataFrame(rows)
    df.to_csv("data/oregon.csv", index=False)
    print(f"Oregon: saved {len(df)} rows to data/oregon.csv")

if __name__ == "__main__":
    scrape_oregon()
