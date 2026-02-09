import pandas as pd
import yfinance as yf 
import csv
import time 

# All the tickers we use, It cannot find "HWN" and "Walt"
TICKERS = ['VSMAX', 'VFIAX', 'SSIFX', 'VIMAX', 'EEM', 'EFA', 'AGCO', 'ADBE', 'GOOG', 'AMGN', 'AAPL', 'BAC', 'BVNKF', 'BDX', 'BSX', 'BLDR', 'CAT', 'CHD', 'CI', 'CMCSA', 'GLW', 'WBD', 'ECL', 'EMBC', 'FFIV', 'FDX', 'FSUMF', 'GRAL', 'GBX', 'ILMN', 'IART', 'JPM', 'KLIC', 'LMNR', 'LKQ', 'MHH', 'MSFT', 'NGVC', 'NKE', 'NWPX', 'NVDA', 'PANW', 'SMG', 'EQNR', 'COHR', 'VKTX', 'SW', 'ORC', 'WY']

OUTPUT_FILE = "portfolio_info.csv"
SLEEP_SECONDS = 1.5  

def get_basic_info(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}

        return {
            "ticker": ticker,
            "description": info.get("longBusinessSummary"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "country": info.get("country")
        }

    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return {
            "ticker": ticker,
            "description": None,
            "sector": None,
            "industry": None,
            "country": None
        }

# -----------------------------
# MAIN LOOP
# -----------------------------
rows = []

for t in TICKERS:
    print(f"Fetching {t}...")
    rows.append(get_basic_info(t))
    time.sleep(SLEEP_SECONDS)

# -----------------------------
# SAVE TO CSV
# -----------------------------
df = pd.DataFrame(rows)
df.to_csv(OUTPUT_FILE, index=False)

print(f"\nSaved to {OUTPUT_FILE}")