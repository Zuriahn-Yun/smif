from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import yfinance as yf
import time

from ..utils.cache import get_screener_cached, set_screener_cached

router = APIRouter()

_MAX_TICKERS = 100

_SCREENER_INFO_KEYS = [
    "longName", "sector", "industry", "country", "quoteType",
    "marketCap", "trailingPE", "forwardPE", "priceToBook",
    "revenueGrowth", "earningsGrowth", "profitMargins",
    "returnOnEquity", "dividendYield", "trailingEps", "currentPrice",
    "fiftyTwoWeekHigh", "fiftyTwoWeekLow",
]


class ScreenerRequest(BaseModel):
    tickers: list[str]
    sector: str | None = None
    min_market_cap: float | None = None     # in dollars
    max_market_cap: float | None = None
    min_pe: float | None = None
    max_pe: float | None = None
    min_revenue_growth: float | None = None  # decimal, e.g. 0.05 = 5%
    max_pe_forward: float | None = None
    min_roe: float | None = None             # decimal


def _fetch_metrics(ticker: str) -> dict | None:
    cached = get_screener_cached(ticker)
    if cached:
        return cached

    try:
        time.sleep(0.3)
        info = yf.Ticker(ticker).info
        data = {k: info.get(k) for k in _SCREENER_INFO_KEYS}
        data["ticker"] = ticker
        set_screener_cached(ticker, data)
        return data
    except Exception as e:
        print(f"Screener fetch error for {ticker}: {e}")
        return None


def _passes_filter(m: dict, req: ScreenerRequest) -> bool:
    def f(val): return val is not None

    if req.sector and (m.get("sector") or "").lower() != req.sector.lower():
        return False
    cap = m.get("marketCap")
    if req.min_market_cap and (not f(cap) or cap < req.min_market_cap):
        return False
    if req.max_market_cap and (not f(cap) or cap > req.max_market_cap):
        return False
    pe = m.get("trailingPE")
    if req.min_pe and (not f(pe) or pe < req.min_pe):
        return False
    if req.max_pe and (not f(pe) or pe > req.max_pe):
        return False
    fpe = m.get("forwardPE")
    if req.max_pe_forward and (not f(fpe) or fpe > req.max_pe_forward):
        return False
    rg = m.get("revenueGrowth")
    if req.min_revenue_growth and (not f(rg) or rg < req.min_revenue_growth):
        return False
    roe = m.get("returnOnEquity")
    if req.min_roe and (not f(roe) or roe < req.min_roe):
        return False
    return True


@router.post("/screen")
def screen_stocks(req: ScreenerRequest):
    tickers = [t.upper().strip() for t in req.tickers if t.strip()]

    if len(tickers) > _MAX_TICKERS:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {_MAX_TICKERS} tickers per request. Submitted {len(tickers)}."
        )

    results = []
    errors = []

    for ticker in tickers:
        metrics = _fetch_metrics(ticker)
        if metrics is None:
            errors.append(ticker)
            continue
        if _passes_filter(metrics, req):
            # Format for display
            cap = metrics.get("marketCap")
            results.append({
                "ticker": ticker,
                "name": metrics.get("longName", ticker),
                "sector": metrics.get("sector", "N/A"),
                "industry": metrics.get("industry", "N/A"),
                "price": metrics.get("currentPrice"),
                "market_cap": cap,
                "market_cap_fmt": (
                    f"${cap/1e12:.2f}T" if cap and cap >= 1e12
                    else f"${cap/1e9:.2f}B" if cap and cap >= 1e9
                    else f"${cap/1e6:.0f}M" if cap else "N/A"
                ),
                "trailing_pe": metrics.get("trailingPE"),
                "forward_pe": metrics.get("forwardPE"),
                "price_to_book": metrics.get("priceToBook"),
                "revenue_growth_pct": round(metrics.get("revenueGrowth", 0) * 100, 2) if metrics.get("revenueGrowth") is not None else None,
                "roe_pct": round(metrics.get("returnOnEquity", 0) * 100, 2) if metrics.get("returnOnEquity") is not None else None,
                "profit_margin_pct": round(metrics.get("profitMargins", 0) * 100, 2) if metrics.get("profitMargins") is not None else None,
                "dividend_yield_pct": round(metrics.get("dividendYield", 0) * 100, 2) if metrics.get("dividendYield") is not None else None,
                "52w_high": metrics.get("fiftyTwoWeekHigh"),
                "52w_low": metrics.get("fiftyTwoWeekLow"),
                "eps": metrics.get("trailingEps"),
            })

    return {
        "results": results,
        "total_screened": len(tickers),
        "total_passed": len(results),
        "errors": errors,
    }
