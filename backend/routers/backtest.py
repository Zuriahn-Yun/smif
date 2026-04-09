from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

from ..utils.yfinance_helpers import get_historical

router = APIRouter()


class BacktestRequest(BaseModel):
    strategy: str = "equal_weight"   # equal_weight | momentum | current_portfolio
    tickers: list[str]
    start_date: str = "2020-01-01"
    end_date: str = "2024-12-31"
    rebalance_freq: str = "quarterly"  # monthly | quarterly | annually


def _load_prices(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    frames = {}
    for ticker in tickers:
        try:
            data = yf.download(ticker, start=start, end=end,
                               interval="1d", auto_adjust=True, progress=False)
            if data.empty:
                continue
            close = data["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
            frames[ticker] = close
        except Exception as e:
            print(f"Backtest data error for {ticker}: {e}")
    if not frames:
        return pd.DataFrame()
    return pd.DataFrame(frames).dropna()


def _rebalance_dates(prices: pd.DataFrame, freq: str) -> list:
    dates = prices.index.tolist()
    if freq == "monthly":
        rule = "MS"
    elif freq == "annually":
        rule = "YS"
    else:
        rule = "QS"
    rebal = pd.date_range(start=dates[0], end=dates[-1], freq=rule)
    # Find nearest actual trading day for each rebal date
    result = []
    for d in rebal:
        candidates = [x for x in dates if x >= d]
        if candidates:
            result.append(candidates[0])
    return list(set(result))


def _momentum_weights(prices: pd.DataFrame, lookback: int = 252) -> dict[str, float]:
    if len(prices) < lookback + 1:
        lookback = max(21, len(prices) - 1)
    window = prices.iloc[-lookback:]
    returns_12m = (window.iloc[-1] / window.iloc[0]) - 1
    positive = returns_12m[returns_12m > 0]
    if positive.empty:
        n = len(prices.columns)
        return {t: 1.0 / n for t in prices.columns}
    top_n = max(1, len(positive) // 3)
    top = positive.nlargest(top_n)
    total = top.sum()
    return {t: float(top[t] / total) for t in top.index}


def _run_strategy(prices: pd.DataFrame, strategy: str, rebalance_freq: str) -> pd.Series:
    n = len(prices.columns)
    tickers = list(prices.columns)
    rebal_dates = sorted(set(_rebalance_dates(prices, rebalance_freq)))

    nav = 1.0
    nav_series = {}
    # Start with equal weight
    weights = {t: 1.0 / n for t in tickers}
    prev_date = prices.index[0]

    for date in prices.index:
        if date in rebal_dates or date == prices.index[0]:
            if strategy == "equal_weight":
                weights = {t: 1.0 / n for t in tickers}
            elif strategy == "momentum":
                hist = prices.loc[:date]
                weights = _momentum_weights(hist)
            # current_portfolio: weights stay fixed from initial equal weight (no rebalance logic)

        # Compute 1-day portfolio return
        if prev_date != date:
            day_ret = 0.0
            for t, w in weights.items():
                if t in prices.columns:
                    p_today = prices.loc[date, t]
                    p_prev = prices.loc[prev_date, t]
                    if p_prev > 0:
                        day_ret += w * (p_today / p_prev - 1)
            nav *= (1 + day_ret)
        nav_series[date] = nav
        prev_date = date

    return pd.Series(nav_series)


def _compute_metrics(nav: pd.Series) -> dict:
    returns = nav.pct_change().dropna()
    total_return = float(nav.iloc[-1] / nav.iloc[0] - 1)
    n_years = (nav.index[-1] - nav.index[0]).days / 365.25
    cagr = float((nav.iloc[-1] / nav.iloc[0]) ** (1 / n_years) - 1) if n_years > 0 else 0.0
    vol = float(returns.std() * np.sqrt(252))
    sharpe = float((returns.mean() * 252 - 0.045) / (returns.std() * np.sqrt(252))) if returns.std() > 0 else 0.0
    rolling_max = nav.cummax()
    drawdown = (nav - rolling_max) / rolling_max
    max_dd = float(drawdown.min())
    calmar = cagr / abs(max_dd) if max_dd != 0 else 0.0
    return {
        "total_return": round(total_return, 4),
        "cagr": round(cagr, 4),
        "annualized_volatility": round(vol, 4),
        "sharpe_ratio": round(sharpe, 4),
        "max_drawdown": round(max_dd, 4),
        "calmar_ratio": round(calmar, 4),
    }


@router.post("/run")
def run_backtest(req: BacktestRequest):
    if req.strategy not in ("equal_weight", "momentum", "current_portfolio"):
        raise HTTPException(status_code=400, detail="strategy must be equal_weight, momentum, or current_portfolio")

    tickers = [t.upper() for t in req.tickers]
    prices = _load_prices(tickers, req.start_date, req.end_date)

    if prices.empty:
        raise HTTPException(status_code=400, detail="No price data for given tickers and date range.")

    # Run strategy
    nav = _run_strategy(prices, req.strategy, req.rebalance_freq)

    # Run SPY benchmark
    spy_prices = _load_prices(["SPY"], req.start_date, req.end_date)
    spy_nav = None
    spy_metrics = None
    if not spy_prices.empty:
        spy_raw = spy_prices["SPY"] / spy_prices["SPY"].iloc[0]
        spy_nav = spy_raw.reindex(nav.index, method="ffill")
        spy_metrics = _compute_metrics(spy_nav)

    metrics = _compute_metrics(nav)

    # Build Plotly figure
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=nav.index.tolist(), y=nav.values.tolist(),
        mode="lines", name=f"{req.strategy.replace('_', ' ').title()}",
        line=dict(color="#005A9C", width=2),
    ))
    if spy_nav is not None:
        fig.add_trace(go.Scatter(
            x=spy_nav.index.tolist(), y=spy_nav.values.tolist(),
            mode="lines", name="SPY Benchmark",
            line=dict(color="#aaa", width=1.5, dash="dot"),
        ))
    fig.update_layout(
        title=f"Backtest: {req.strategy.replace('_', ' ').title()} ({req.start_date} – {req.end_date})",
        xaxis_title="Date", yaxis_title="Portfolio NAV (normalized to 1.0)",
        hovermode="x unified",
    )

    return {
        "figure": fig.to_json(),
        "metrics": metrics,
        "benchmark_metrics": spy_metrics,
        "strategy": req.strategy,
        "tickers_used": list(prices.columns),
        "rebalance_freq": req.rebalance_freq,
    }
