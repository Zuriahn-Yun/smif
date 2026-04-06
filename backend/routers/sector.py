from fastapi import APIRouter
import plotly.graph_objects as go
import plotly.express as px

from ..utils.cache import portfolio_cache, load_portfolio
from ..utils.yfinance_helpers import get_info, safe_float

router = APIRouter()


def _get_last_price(stock_obj) -> float:
    import pandas as pd
    close = stock_obj.data["Close"]
    val = close.iloc[-1]
    return float(val.iloc[0]) if isinstance(val, pd.Series) else float(val)


@router.get("/exposure")
def get_sector_exposure():
    """
    Returns three Plotly figures:
      - treemap: sector -> ticker, sized by portfolio weight
      - pie: asset class breakdown (ETF, equity, other)
      - bar: top sectors by weight
    """
    holdings = load_portfolio()
    ticker_meta = {h["ticker"]: h for h in holdings}

    # Build value-weighted data
    rows = []
    total_value = 0.0

    for ticker, stock_obj in portfolio_cache.items():
        try:
            price = _get_last_price(stock_obj)
            shares = stock_obj.shares
            value = price * shares
            total_value += value
            rows.append({"ticker": ticker, "value": value})
        except Exception:
            continue

    if not rows or total_value == 0:
        return {"error": "Portfolio data not yet loaded."}

    # Enrich with sector info (use cached info, don't block if not yet fetched)
    from ..utils.cache import sector_info_cache
    enriched = []
    for row in rows:
        ticker = row["ticker"]
        info = sector_info_cache.get(ticker, {})
        sector = info.get("sector") or "Unknown"
        quote_type = info.get("quoteType", "").upper()
        if quote_type in ("ETF", "MUTUALFUND"):
            asset_class = "Fund/ETF"
        elif sector != "Unknown":
            asset_class = "Equity"
        else:
            asset_class = "Other"
        enriched.append({
            "ticker": ticker,
            "sector": sector,
            "asset_class": asset_class,
            "value": row["value"],
            "weight_pct": round(row["value"] / total_value * 100, 2),
            "description": ticker_meta.get(ticker, {}).get("description", ticker),
        })

    # --- Figure 1: Treemap by sector/ticker ---
    labels, parents, values, texts = [], [], [], []
    sector_totals = {}
    for row in enriched:
        sector_totals[row["sector"]] = sector_totals.get(row["sector"], 0) + row["value"]

    # Root
    labels.append("Portfolio")
    parents.append("")
    values.append(total_value)
    texts.append(f"Total: ${total_value:,.0f}")

    # Sectors
    for sector, val in sector_totals.items():
        labels.append(sector)
        parents.append("Portfolio")
        values.append(val)
        texts.append(f"{sector}: {val/total_value*100:.1f}%")

    # Tickers
    for row in enriched:
        labels.append(row["ticker"])
        parents.append(row["sector"])
        values.append(row["value"])
        texts.append(f"{row['ticker']}: {row['weight_pct']}%<br>${row['value']:,.0f}")

    treemap_fig = go.Figure(go.Treemap(
        labels=labels, parents=parents, values=values,
        text=texts, textinfo="label+text",
        hovertemplate="%{text}<extra></extra>",
    ))
    treemap_fig.update_layout(title="Portfolio by Sector", margin=dict(t=40, l=0, r=0, b=0))

    # --- Figure 2: Pie by asset class ---
    ac_totals = {}
    for row in enriched:
        ac_totals[row["asset_class"]] = ac_totals.get(row["asset_class"], 0) + row["value"]

    pie_fig = go.Figure(go.Pie(
        labels=list(ac_totals.keys()),
        values=[round(v, 2) for v in ac_totals.values()],
        hole=0.4,
    ))
    pie_fig.update_layout(title="Asset Class Breakdown")

    # --- Figure 3: Bar chart top sectors ---
    sorted_sectors = sorted(sector_totals.items(), key=lambda x: x[1], reverse=True)
    bar_fig = go.Figure(go.Bar(
        x=[s[0] for s in sorted_sectors],
        y=[round(s[1] / total_value * 100, 2) for s in sorted_sectors],
        marker_color="#005A9C",
    ))
    bar_fig.update_layout(
        title="Sector Weights (%)",
        xaxis_title="Sector", yaxis_title="Weight (%)",
        xaxis_tickangle=-30,
    )

    return {
        "treemap": treemap_fig.to_json(),
        "pie": pie_fig.to_json(),
        "bar": bar_fig.to_json(),
        "holdings": enriched,
        "total_value": round(total_value, 2),
        "info_loaded": len(sector_info_cache),
        "total_tickers": len(rows),
    }


@router.post("/fetch_info")
async def fetch_sector_info():
    """
    Background endpoint: populates sector_info_cache for all portfolio tickers.
    Call once after startup. Returns number of tickers enriched.
    """
    import asyncio
    from ..utils.cache import sector_info_cache
    holdings = load_portfolio()
    loaded = 0
    for h in holdings:
        ticker = h["ticker"]
        if ticker not in sector_info_cache:
            try:
                get_info(ticker)
                loaded += 1
                await asyncio.sleep(0.4)
            except Exception as e:
                print(f"Info fetch failed for {ticker}: {e}")
    return {"fetched": loaded, "total_cached": len(sector_info_cache)}
