from datetime import date

import pandas as pd

from common import finalize_canonical, parse_multiple, parse_number, parse_percent


def ingest_founders_fund():
    # TODO: These rows are manually entered from the Founders Fund screenshot table.
    manual_rows = [
        {"fund_name": "FFI", "vintage_year": 2005, "fund_size": "$50M", "net_irr": "36%", "net_multiple": "7.8x", "dpi": "7.7x"},
        {"fund_name": "FFII", "vintage_year": 2007, "fund_size": "$227M", "net_irr": "31%", "net_multiple": "18.7x", "dpi": "18.6x"},
        {"fund_name": "FFIII", "vintage_year": 2010, "fund_size": "$250M", "net_irr": "25%", "net_multiple": "9.9x", "dpi": "6.0x"},
        {"fund_name": "FFIV", "vintage_year": 2011, "fund_size": "$625M", "net_irr": "33%", "net_multiple": "10.2x", "dpi": "6.2x"},
        {"fund_name": "FFV", "vintage_year": 2014, "fund_size": "$1.1B", "net_irr": "27%", "net_multiple": "4.0x", "dpi": "2.9x"},
        {"fund_name": "FFVI", "vintage_year": 2017, "fund_size": "$1.4B", "net_irr": "24%", "net_multiple": "3.1x", "dpi": "0.03x"},
        {"fund_name": "FFVII", "vintage_year": 2020, "fund_size": "$1.5B", "net_irr": "13%", "net_multiple": "1.5x", "dpi": "-"},
        {"fund_name": "FFVIII", "vintage_year": 2023, "fund_size": "$979M", "net_irr": "47%", "net_multiple": "1.3x", "dpi": "-"},
        {"fund_name": "FF Growth I", "vintage_year": 2020, "fund_size": "$1.7B", "net_irr": "7%", "net_multiple": "1.2x", "dpi": "-"},
        {"fund_name": "FF Growth II", "vintage_year": 2023, "fund_size": "$3.4B", "net_irr": "7%", "net_multiple": "1.0x", "dpi": "-"},
    ]

    df = pd.DataFrame(manual_rows)
    normalized = pd.DataFrame(
        {
            "fund_name": df["fund_name"],
            "gp_name": "Founders Fund",
            "vintage_year": df["vintage_year"],
            "committed": df["fund_size"].map(parse_number),
            "cash_in": None,
            "cash_out": None,
            "remaining_value": None,
            "total_value": None,
            "tvpi": df["net_multiple"].map(parse_multiple),
            "dpi": df["dpi"].map(parse_multiple),
            "rvpi": None,
            "net_irr": df["net_irr"].map(parse_percent),
            "source": "Founders Fund (manual)",
            "as_of_date": str(date.today()),
        }
    )

    result = finalize_canonical(normalized, source="Founders Fund (manual)", as_of_date=str(date.today()))
    output_path = "data/ingested_founders_fund.csv"
    result.to_csv(output_path, index=False)
    print(f"[Founders Fund] Extracted rows: {len(result)}")
    print(f"[Founders Fund] Skipped rows: 0")
    print(f"[Founders Fund] Saved: {output_path}")
    return result


if __name__ == "__main__":
    ingest_founders_fund()
