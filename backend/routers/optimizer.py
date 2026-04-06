from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from scipy.optimize import minimize

from ..utils.yfinance_helpers import get_historical

router = APIRouter()

_RISK_FREE_RATE = 0.045  # ~4.5% annualized T-bill rate
_optimizer_cache: dict = {}


class OptRequest(BaseModel):
    tickers: list[str]
    lookback_years: int = 2
    num_portfolios: int = 500


def _get_returns(tickers: list[str], lookback_years: int) -> pd.DataFrame:
    period = f"{lookback_years}y"
    frames = {}
    for ticker in tickers:
        data = get_historical(ticker, period)
        if data.empty:
            continue
        close = data["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        frames[ticker] = close
    if not frames:
        return pd.DataFrame()
    prices = pd.DataFrame(frames).dropna()
    return prices.pct_change().dropna()


def _portfolio_stats(weights: np.ndarray, mean_returns: np.ndarray,
                     cov_matrix: np.ndarray, trading_days: int = 252):
    ret = float(np.dot(weights, mean_returns) * trading_days)
    vol = float(np.sqrt(np.dot(weights.T, np.dot(cov_matrix * trading_days, weights))))
    sharpe = (ret - _RISK_FREE_RATE) / vol if vol > 0 else 0.0
    return ret, vol, sharpe


@router.post("/efficient_frontier")
def efficient_frontier(req: OptRequest):
    tickers = [t.upper() for t in req.tickers[:20]]  # cap at 20
    num_p = min(req.num_portfolios, 1000)

    cache_key = (tuple(sorted(tickers)), req.lookback_years)
    if cache_key in _optimizer_cache:
        cached = _optimizer_cache[cache_key]
        mean_returns = cached["mean_returns"]
        cov_matrix = cached["cov_matrix"]
        valid_tickers = cached["tickers"]
    else:
        returns = _get_returns(tickers, req.lookback_years)
        if returns.empty or len(returns.columns) < 2:
            raise HTTPException(status_code=400, detail="Need at least 2 tickers with data.")
        valid_tickers = list(returns.columns)
        mean_returns = returns.mean().values
        cov_matrix = returns.cov().values
        _optimizer_cache[cache_key] = {
            "mean_returns": mean_returns,
            "cov_matrix": cov_matrix,
            "tickers": valid_tickers,
        }

    n = len(valid_tickers)
    rets, vols, sharpes, weights_list = [], [], [], []

    for _ in range(num_p):
        w = np.random.dirichlet(np.ones(n))
        r, v, s = _portfolio_stats(w, mean_returns, cov_matrix)
        rets.append(r)
        vols.append(v)
        sharpes.append(s)
        weights_list.append(w.tolist())

    sharpes_arr = np.array(sharpes)
    max_idx = int(np.argmax(sharpes_arr))
    min_idx = int(np.argmin(vols))

    hover = [
        "<br>".join(f"{valid_tickers[i]}: {w[i]*100:.1f}%" for i in range(n))
        for w in weights_list
    ]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=vols, y=rets, mode="markers",
        marker=dict(color=sharpes, colorscale="Viridis", showscale=True,
                    colorbar=dict(title="Sharpe"), size=5, opacity=0.7),
        text=hover, hovertemplate="Return: %{y:.1%}<br>Vol: %{x:.1%}<br>%{text}<extra></extra>",
        name="Portfolios",
    ))
    fig.add_trace(go.Scatter(
        x=[vols[max_idx]], y=[rets[max_idx]], mode="markers",
        marker=dict(color="red", size=12, symbol="star"),
        name=f"Max Sharpe ({sharpes[max_idx]:.2f})",
        hovertemplate=f"Max Sharpe<br>Return: {rets[max_idx]:.1%}<br>Vol: {vols[max_idx]:.1%}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[vols[min_idx]], y=[rets[min_idx]], mode="markers",
        marker=dict(color="green", size=12, symbol="diamond"),
        name="Min Variance",
        hovertemplate=f"Min Variance<br>Return: {rets[min_idx]:.1%}<br>Vol: {vols[min_idx]:.1%}<extra></extra>",
    ))
    fig.update_layout(
        title="Efficient Frontier",
        xaxis_title="Annualized Volatility",
        yaxis_title="Annualized Return",
        xaxis=dict(tickformat=".0%"),
        yaxis=dict(tickformat=".0%"),
    )

    return {
        "figure": fig.to_json(),
        "max_sharpe": {
            "weights": {valid_tickers[i]: round(weights_list[max_idx][i], 4) for i in range(n)},
            "return": round(rets[max_idx], 4),
            "volatility": round(vols[max_idx], 4),
            "sharpe": round(sharpes[max_idx], 4),
        },
        "min_variance": {
            "weights": {valid_tickers[i]: round(weights_list[min_idx][i], 4) for i in range(n)},
            "return": round(rets[min_idx], 4),
            "volatility": round(vols[min_idx], 4),
            "sharpe": round(sharpes[min_idx], 4),
        },
        "tickers": valid_tickers,
    }


@router.post("/max_sharpe")
def max_sharpe(req: OptRequest):
    """Exact max-Sharpe via scipy SLSQP optimizer."""
    tickers = [t.upper() for t in req.tickers[:20]]
    returns = _get_returns(tickers, req.lookback_years)
    if returns.empty or len(returns.columns) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 tickers with data.")

    valid_tickers = list(returns.columns)
    n = len(valid_tickers)
    mean_r = returns.mean().values
    cov = returns.cov().values

    def neg_sharpe(w):
        r, v, s = _portfolio_stats(w, mean_r, cov)
        return -s

    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    bounds = [(0.0, 1.0)] * n
    w0 = np.ones(n) / n

    result = minimize(neg_sharpe, w0, method="SLSQP", bounds=bounds, constraints=constraints,
                      options={"maxiter": 500, "ftol": 1e-9})

    w_opt = result.x
    r_opt, v_opt, s_opt = _portfolio_stats(w_opt, mean_r, cov)

    return {
        "weights": {valid_tickers[i]: round(float(w_opt[i]), 4) for i in range(n)},
        "annualized_return": round(r_opt, 4),
        "annualized_volatility": round(v_opt, 4),
        "sharpe_ratio": round(s_opt, 4),
        "risk_free_rate": _RISK_FREE_RATE,
        "tickers": valid_tickers,
        "success": result.success,
    }
