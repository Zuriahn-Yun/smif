from fastapi import APIRouter, HTTPException
import yfinance as yf
import pandas as pd

from ..utils.cache import portfolio_cache, load_portfolio, sector_info_cache
from ..utils.yfinance_helpers import get_info, safe_float

router = APIRouter()

# Metrics to extract from .info
_VALUATION_KEYS = [
    ("trailingPE", "Trailing P/E"),
    ("forwardPE", "Forward P/E"),
    ("priceToBook", "Price/Book"),
    ("enterpriseToEbitda", "EV/EBITDA"),
    ("debtToEquity", "Debt/Equity"),
    ("returnOnEquity", "Return on Equity"),
    ("returnOnAssets", "Return on Assets"),
    ("revenueGrowth", "Revenue Growth (YoY)"),
    ("earningsGrowth", "Earnings Growth (YoY)"),
    ("profitMargins", "Profit Margin"),
    ("operatingMargins", "Operating Margin"),
    ("marketCap", "Market Cap"),
    ("trailingEps", "Trailing EPS"),
    ("forwardEps", "Forward EPS"),
    ("dividendYield", "Dividend Yield"),
]

_PORTFOLIO_TICKERS = None


def _get_portfolio_tickers():
    global _PORTFOLIO_TICKERS
    if _PORTFOLIO_TICKERS is None:
        _PORTFOLIO_TICKERS = set(h["ticker"] for h in load_portfolio())
    return _PORTFOLIO_TICKERS


def _check_ticker(ticker: str):
    if ticker not in _get_portfolio_tickers():
        raise HTTPException(status_code=404, detail=f"{ticker} is not in the SMIF portfolio.")


@router.get("/{ticker}/overview")
def get_overview(ticker: str):
    ticker = ticker.upper()
    _check_ticker(ticker)
    info = get_info(ticker)
    return {
        "ticker": ticker,
        "name": info.get("longName") or info.get("shortName", ticker),
        "summary": info.get("longBusinessSummary", "No description available."),
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        "country": info.get("country", "N/A"),
        "website": info.get("website", ""),
        "employees": info.get("fullTimeEmployees"),
        "quote_type": info.get("quoteType", ""),
    }


@router.get("/{ticker}/valuation")
def get_valuation(ticker: str):
    ticker = ticker.upper()
    _check_ticker(ticker)
    info = get_info(ticker)

    metrics = []
    for key, label in _VALUATION_KEYS:
        val = info.get(key)
        fmt_val = None
        if val is not None:
            try:
                fv = float(val)
                if key in ("revenueGrowth", "earningsGrowth", "profitMargins",
                           "operatingMargins", "dividendYield", "returnOnEquity",
                           "returnOnAssets"):
                    fmt_val = f"{fv * 100:.2f}%"
                elif key == "marketCap":
                    if fv >= 1e12:
                        fmt_val = f"${fv/1e12:.2f}T"
                    elif fv >= 1e9:
                        fmt_val = f"${fv/1e9:.2f}B"
                    else:
                        fmt_val = f"${fv/1e6:.2f}M"
                else:
                    fmt_val = f"{fv:.2f}"
            except (TypeError, ValueError):
                fmt_val = str(val)
        metrics.append({"key": key, "label": label, "raw": val, "formatted": fmt_val})

    return {"ticker": ticker, "metrics": metrics}


@router.get("/{ticker}/financials")
def get_financials(ticker: str):
    ticker = ticker.upper()
    _check_ticker(ticker)

    try:
        t = yf.Ticker(ticker)
        fin = t.financials  # annual income statement

        if fin is None or fin.empty:
            return {"ticker": ticker, "annual": [], "quarterly": [], "note": "No financial data available (common for ETFs/funds)."}

        def df_to_rows(df: pd.DataFrame, limit: int = 4) -> list[dict]:
            df = df.iloc[:, :limit]
            result = []
            for label in ["Total Revenue", "Net Income", "Gross Profit", "Operating Income", "EBITDA"]:
                if label in df.index:
                    row = {"label": label, "values": {}}
                    for col in df.columns:
                        val = df.loc[label, col]
                        row["values"][str(col.date() if hasattr(col, 'date') else col)] = (
                            None if pd.isna(val) else int(val)
                        )
                    result.append(row)
            return result

        annual_rows = df_to_rows(fin)

        quarterly = t.quarterly_financials
        quarterly_rows = df_to_rows(quarterly, limit=6) if quarterly is not None and not quarterly.empty else []

        return {"ticker": ticker, "annual": annual_rows, "quarterly": quarterly_rows}

    except Exception as e:
        return {"ticker": ticker, "annual": [], "quarterly": [], "error": str(e)}
