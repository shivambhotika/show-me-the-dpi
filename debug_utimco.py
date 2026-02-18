import requests, pdfplumber
from io import BytesIO

url = 'https://www.utimco.org/media/vpofvif4/2025-investment-performance.pdf'
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
r = requests.get(url, headers=headers, timeout=60)

with pdfplumber.open(BytesIO(r.content)) as pdf:
    print(f'Total pages: {len(pdf.pages)}')
    for i in range(min(3, len(pdf.pages))):
        print(f'\n--- PAGE {i+1} RAW TEXT ---')
        print(pdf.pages[i].extract_text()[:3000])
