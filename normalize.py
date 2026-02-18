import pandas as pd
import os

def normalize_calpers(df):
    """Map CalPERS columns to unified schema."""
    col_map = {}
    for col in df.columns:
        col_l = col.lower()
        if "fund" in col_l and "name" in col_l:
            col_map[col] = "fund_name"
        elif "vintage" in col_l:
            col_map[col] = "vintage_year"
        elif "irr" in col_l:
            col_map[col] = "net_irr"
        elif "multiple" in col_l or "tvpi" in col_l or "investment_multiple" in col_l:
            col_map[col] = "tvpi"
        elif "committed" in col_l:
            col_map[col] = "capital_committed"
        elif "distributed" in col_l or "cash_out" in col_l:
            col_map[col] = "capital_distributed"
        elif "contributed" in col_l or "cash_in" in col_l:
            col_map[col] = "capital_contributed"
    
    df = df.rename(columns=col_map)
    df["dpi"] = None  # CalPERS doesn't report DPI directly
    return df

def normalize_calstrs(df):
    """Map CalSTRS columns to unified schema."""
    col_map = {}
    for col in df.columns:
        col_l = col.lower()
        if "fund" in col_l or "manager" in col_l or "name" in col_l:
            col_map[col] = "fund_name"
        elif "vintage" in col_l:
            col_map[col] = "vintage_year"
        elif "irr" in col_l:
            col_map[col] = "net_irr"
        elif "committed" in col_l:
            col_map[col] = "capital_committed"
        elif "distributed" in col_l:
            col_map[col] = "capital_distributed"
        elif "contributed" in col_l:
            col_map[col] = "capital_contributed"
        elif "market" in col_l or "value" in col_l or "nav" in col_l:
            col_map[col] = "nav"
    
    df = df.rename(columns=col_map)
    df["tvpi"] = None
    df["dpi"] = None
    return df

def normalize_utimco(df):
    """Map UTIMCO columns to unified schema."""
    col_map = {}
    for col in df.columns:
        col_l = col.lower()
        if "fund" in col_l or "name" in col_l or "manager" in col_l:
            if col_map.get("fund_name") is None:
                col_map[col] = "fund_name"
        elif "invested" in col_l:
            col_map[col] = "capital_contributed"
        elif "returned" in col_l:
            col_map[col] = "capital_distributed"
        elif "value" in col_l or "nav" in col_l:
            col_map[col] = "nav"
        elif "cash" in col_l and "cash" in col_l:
            col_map[col] = "tvpi"
        elif "irr" in col_l:
            col_map[col] = "net_irr"
    
    df = df.rename(columns=col_map)
    df["vintage_year"] = None  # UTIMCO doesn't always report vintage per fund
    df["dpi"] = None
    return df

def normalize_psers(df):
    col_map = {}
    for col in df.columns:
        col_l = col.lower()
        if ("fund" in col_l or "partnership" in col_l or "manager" in col_l) and "name" in col_l:
            col_map[col] = "fund_name"
        elif col_l == col_l and "fund" in col_l and col_map.get("fund_name") is None:
            col_map[col] = "fund_name"
        elif "vintage" in col_l:
            col_map[col] = "vintage_year"
        elif "irr" in col_l:
            col_map[col] = "net_irr"
        elif "tvpi" in col_l or "multiple" in col_l:
            col_map[col] = "tvpi"
        elif "dpi" in col_l:
            col_map[col] = "dpi"
        elif "committed" in col_l:
            col_map[col] = "capital_committed"
        elif "contributed" in col_l or "called" in col_l or "drawn" in col_l:
            col_map[col] = "capital_contributed"
        elif "distributed" in col_l:
            col_map[col] = "capital_distributed"
        elif "market" in col_l or "nav" in col_l or "value" in col_l:
            col_map[col] = "nav"
    df = df.rename(columns=col_map)
    return df

def normalize_oregon(df):
    col_map = {}
    for col in df.columns:
        col_l = col.lower()
        if "fund" in col_l or "partnership" in col_l:
            col_map[col] = "fund_name"
        elif "vintage" in col_l:
            col_map[col] = "vintage_year"
        elif "tvpi" in col_l:
            col_map[col] = "tvpi"
        elif "dpi" in col_l:
            col_map[col] = "dpi"
        elif "irr" in col_l:
            col_map[col] = "net_irr"
        elif "committed" in col_l:
            col_map[col] = "capital_committed"
        elif "contributed" in col_l or "called" in col_l:
            col_map[col] = "capital_contributed"
        elif "distributed" in col_l:
            col_map[col] = "capital_distributed"
        elif "market" in col_l or "value" in col_l:
            col_map[col] = "nav"
    df = df.rename(columns=col_map)
    return df

def normalize_wsib(df):
    col_map = {}
    for col in df.columns:
        col_l = col.lower()
        if "partnership" in col_l or ("fund" in col_l and "name" in col_l):
            col_map[col] = "fund_name"
        elif "vintage" in col_l:
            col_map[col] = "vintage_year"
        elif "irr" in col_l:
            col_map[col] = "net_irr"
        elif "tvpi" in col_l or "multiple" in col_l:
            col_map[col] = "tvpi"
        elif "dpi" in col_l:
            col_map[col] = "dpi"
        elif "committed" in col_l:
            col_map[col] = "capital_committed"
        elif "contributed" in col_l or "called" in col_l or "funded" in col_l:
            col_map[col] = "capital_contributed"
        elif "distributed" in col_l:
            col_map[col] = "capital_distributed"
        elif "value" in col_l or "nav" in col_l:
            col_map[col] = "nav"
    df = df.rename(columns=col_map)
    return df

def build_unified_dataset():
    unified_cols = [
        "fund_name", "vintage_year", "capital_committed", 
        "capital_contributed", "capital_distributed", "nav",
        "net_irr", "tvpi", "dpi", "source", "scraped_date", "reporting_period"
    ]
    
    frames = []
    
    sources = {
        "data/calpers.csv": normalize_calpers,
        "data/calstrs.csv": normalize_calstrs,
        "data/utimco.csv": normalize_utimco,
        "data/psers.csv": normalize_psers,
        "data/oregon.csv": normalize_oregon,
        "data/wsib.csv": normalize_wsib,
    }
    
    for filepath, normalizer in sources.items():
        if os.path.exists(filepath):
            df = pd.read_csv(filepath)
            df = normalizer(df)
            
            # Add any missing unified columns
            for col in unified_cols:
                if col not in df.columns:
                    df[col] = None
            
            frames.append(df[unified_cols])
            print(f"Loaded {len(df)} rows from {filepath}")
        else:
            print(f"Warning: {filepath} not found — skipping")
    
    if not frames:
        print("No data files found. Run scrapers first.")
        return
    
    combined = pd.concat(frames, ignore_index=True)
    
    # Basic deduplication — same fund name + vintage + source
    combined = combined.drop_duplicates(subset=["fund_name", "vintage_year", "source"])
    
    # Sort by vintage year descending
    combined = combined.sort_values("vintage_year", ascending=False, na_position="last")
    
    os.makedirs("data", exist_ok=True)
    combined.to_csv("data/unified_funds.csv", index=False)
    print(f"\nUnified dataset: {len(combined)} total fund entries")
    print(f"Sources: {combined['source'].value_counts().to_dict()}")
    print("Saved to data/unified_funds.csv")

if __name__ == "__main__":
    build_unified_dataset()
