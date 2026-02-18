import requests, pdfplumber, pandas as pd, re
from io import BytesIO
from datetime import date

url = 'https://www.calstrs.com/files/6765c6592/CalSTRSPrivateEquityPerformanceReportFYE2025.pdf'
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
r = requests.get(url, headers=headers, timeout=60)

rows = []
with pdfplumber.open(BytesIO(r.content)) as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        if not text:
            continue
        for line in text.split('\n'):
            match = re.match(
                r'^(.+?)\s+(\d{4})\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+|-)\s+([\-\d\.]+)$',
                line.strip()
            )
            if match:
                rows.append({
                    'fund_name': match.group(1).strip(),
                    'vintage_year': match.group(2),
                    'capital_committed': match.group(3).replace(',',''),
                    'capital_contributed': match.group(4).replace(',',''),
                    'capital_distributed': match.group(5).replace(',',''),
                    'nav': match.group(6).replace(',','').replace('-',''),
                    'net_irr': match.group(7),
                    'source': 'CalSTRS',
                    'scraped_date': str(date.today()),
                    'reporting_period': 'FYE June 30, 2025'
                })

df = pd.DataFrame(rows)
print(f'Rows extracted: {len(df)}')
print(df.head(5).to_string())
df.to_csv('data/calstrs.csv', index=False)
print('Saved to data/calstrs.csv')
