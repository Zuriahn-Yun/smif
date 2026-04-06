from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import pandas as pd

from ..utils.cache import portfolio_cache, load_portfolio
from ..utils.cache import sector_info_cache

router = APIRouter()


def _get_last_price(stock_obj) -> float:
    close = stock_obj.data["Close"]
    val = close.iloc[-1]
    return float(val.iloc[0]) if isinstance(val, pd.Series) else float(val)


class TradeRequest(BaseModel):
    target_weights: dict[str, float]  # ticker -> weight (must sum to ~1.0)
    total_budget: float = 0.0         # optional override; defaults to current portfolio value


@router.get("/current_allocation")
def get_current_allocation():
    """Return current holdings with weights, prices, and sector labels."""
    if not portfolio_cache:
        return {"status": "loading", "message": "Portfolio data not yet loaded."}

    holdings = load_portfolio()
    ticker_meta = {h["ticker"]: h for h in holdings}

    rows = []
    total_value = 0.0

    for ticker, stock_obj in portfolio_cache.items():
        try:
            price = _get_last_price(stock_obj)
            value = price * stock_obj.shares
            total_value += value
            rows.append({"ticker": ticker, "price": price, "value": value})
        except Exception:
            continue

    if total_value == 0:
        return {"error": "Could not calculate portfolio value."}

    assets = []
    sector_totals: dict[str, float] = {}

    for row in rows:
        ticker = row["ticker"]
        info = sector_info_cache.get(ticker, {})
        sector = info.get("sector") or "Unknown"
        weight = round(row["value"] / total_value, 6)
        sector_totals[sector] = sector_totals.get(sector, 0) + weight
        assets.append({
            "ticker": ticker,
            "shares": portfolio_cache[ticker].shares,
            "price": round(row["price"], 2),
            "value": round(row["value"], 2),
            "current_weight": weight,
            "sector": sector,
            "description": ticker_meta.get(ticker, {}).get("description", ticker),
        })

    assets.sort(key=lambda x: x["value"], reverse=True)

    return {
        "assets": assets,
        "total_value": round(total_value, 2),
        "sector_weights": {k: round(v, 4) for k, v in sorted(sector_totals.items(), key=lambda x: x[1], reverse=True)},
    }


@router.post("/calculate_trades")
def calculate_trades(req: TradeRequest):
    """
    Given target weights (must sum to 1.0) and optionally a total budget,
    return the list of buy/sell trades needed to rebalance.
    """
    if not portfolio_cache:
        raise HTTPException(status_code=503, detail="Portfolio data not yet loaded.")

    weights = req.target_weights
    weight_sum = sum(weights.values())
    if abs(weight_sum - 1.0) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Target weights must sum to 1.0 (got {weight_sum:.4f})."
        )

    # Build current state
    rows = {}
    total_value = 0.0
    for ticker, stock_obj in portfolio_cache.items():
        try:
            close = stock_obj.data["Close"]
            val = close.iloc[-1]
            price = float(val.iloc[0]) if isinstance(val, pd.Series) else float(val)
            value = price * stock_obj.shares
            total_value += value
            rows[ticker] = {"price": price, "value": value, "shares": stock_obj.shares}
        except Exception:
            continue

    budget = req.total_budget if req.total_budget > 0 else total_value

    trades = []
    for ticker, target_w in weights.items():
        current_value = rows.get(ticker, {}).get("value", 0.0)
        current_w = current_value / total_value if total_value > 0 else 0.0
        price = rows.get(ticker, {}).get("price")

        if price is None or price == 0:
            continue

        target_value = target_w * budget
        delta_value = target_value - current_value
        delta_shares = int(delta_value / price)  # whole shares only

        action = "BUY" if delta_shares > 0 else ("SELL" if delta_shares < 0 else "HOLD")

        trades.append({
            "ticker": ticker,
            "action": action,
            "shares_delta": delta_shares,
            "current_shares": rows.get(ticker, {}).get("shares", 0),
            "target_shares": rows.get(ticker, {}).get("shares", 0) + delta_shares,
            "price": round(price, 2),
            "trade_value": round(abs(delta_shares * price), 2),
            "current_weight": round(current_w, 4),
            "target_weight": round(target_w, 4),
            "drift": round(current_w - target_w, 4),
        })

    trades.sort(key=lambda x: abs(x["drift"]), reverse=True)

    buys = sum(t["trade_value"] for t in trades if t["action"] == "BUY")
    sells = sum(t["trade_value"] for t in trades if t["action"] == "SELL")
    turnover_pct = round((buys + sells) / 2 / budget * 100, 2) if budget else 0

    return {
        "trades": trades,
        "summary": {
            "total_buys": round(buys, 2),
            "total_sells": round(sells, 2),
            "turnover_pct": turnover_pct,
            "portfolio_value": round(total_value, 2),
            "budget": round(budget, 2),
        },
    }


@router.get("/equal_weight_target")
def equal_weight_target():
    """Return equal-weight target allocation for all portfolio tickers."""
    holdings = load_portfolio()
    n = len(holdings)
    w = round(1.0 / n, 6)
    return {h["ticker"]: w for h in holdings}
