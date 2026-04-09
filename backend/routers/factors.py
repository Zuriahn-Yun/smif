from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ..utils.cache import portfolio_cache
from ..utils.yfinance_helpers import get_historical

router = APIRouter()

_ff_cache: dict = {}  # keyed by month: YYYYMM


class FactorRequest(BaseModel):
    lookback_years: int = 3


class RollingRequest(BaseModel):
    window_months: int = 12
    lookback_years: int = 3


def _get_ff_daily() -> pd.DataFrame | None:
    """Download Fama-French 3-factor daily data. Cached monthly."""
    from datetime import date
    cache_key = date.today().strftime("%Y%m")
    if cache_key in _ff_cache:
        return _ff_cache[cache_key]

    try:
        import pandas_datareader.data as web
        raw = web.DataReader("F-F_Research_Data_Factors_daily", "famafrench")[0]
        # Columns: Mkt-RF, SMB, HML, RF (in percent)
        raw = raw / 100.0
        raw.index = pd.to_datetime(raw.index, format="%Y%m%d")
        _ff_cache[cache_key] = raw
        return raw
    except Exception as e:
        print(f"Fama-French download failed: {e}")
        return None


def _get_portfolio_returns(lookback_years: int) -> pd.Series | None:
    """Value-weighted daily portfolio returns using cached price data."""
    if not portfolio_cache:
        return None

    period = f"{lookback_years}y"
    frames = {}
    for ticker, stock_obj in portfolio_cache.items():
        try:
            close = stock_obj.data["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
            frames[ticker] = (close, stock_obj.shares)
        except Exception:
            continue

    if not frames:
        return None

    # Align all price series
    price_df = pd.DataFrame({t: s for t, (s, _) in frames.items()}).dropna()
    weights = {}
    for ticker, (series, shares) in frames.items():
        if ticker in price_df.columns:
            last_price = float(price_df[ticker].iloc[-1])
            weights[ticker] = last_price * shares

    total_w = sum(weights.values())
    if total_w == 0:
        return None

    port_ret = pd.Series(0.0, index=price_df.index)
    for ticker in price_df.columns:
        w = weights.get(ticker, 0) / total_w
        ret = price_df[ticker].pct_change()
        port_ret += w * ret

    # Trim to lookback
    cutoff = port_ret.index[-1] - pd.DateOffset(years=lookback_years)
    port_ret = port_ret[port_ret.index >= cutoff].dropna()
    return port_ret


@router.post("/fama_french")
def fama_french_regression(req: FactorRequest):
    """OLS regression of portfolio returns on 3-factor Fama-French model."""
    import statsmodels.api as sm

    port_ret = _get_portfolio_returns(req.lookback_years)
    if port_ret is None or port_ret.empty:
        raise HTTPException(status_code=503, detail="Portfolio price data not yet loaded.")

    ff = _get_ff_daily()
    if ff is None:
        raise HTTPException(status_code=503,
                            detail="Could not download Fama-French data. The Ken French library may be temporarily unavailable.")

    # Align
    aligned = pd.concat([port_ret.rename("R_port"), ff], axis=1).dropna()
    if len(aligned) < 60:
        raise HTTPException(status_code=400, detail="Insufficient overlapping data for regression.")

    Y = aligned["R_port"] - aligned["RF"]
    X = aligned[["Mkt-RF", "SMB", "HML"]]
    X = sm.add_constant(X)

    model = sm.OLS(Y, X).fit()

    alpha_daily = float(model.params.get("const", 0))
    alpha_annual = float((1 + alpha_daily) ** 252 - 1)

    # Bar chart of factor loadings
    factors = ["Mkt-RF", "SMB", "HML"]
    betas = [float(model.params.get(f, 0)) for f in factors]
    tvals = [float(model.tvalues.get(f, 0)) for f in factors]
    colors = ["#005A9C" if b > 0 else "#d9534f" for b in betas]

    fig = go.Figure(go.Bar(
        x=["Market (Mkt-RF)", "Size (SMB)", "Value (HML)"],
        y=betas, marker_color=colors,
        text=[f"β={b:.3f}<br>t={t:.2f}" for b, t in zip(betas, tvals)],
        textposition="outside",
    ))
    fig.update_layout(
        title="Fama-French 3-Factor Loadings",
        yaxis_title="Beta", xaxis_title="Factor",
    )

    return {
        "figure": fig.to_json(),
        "alpha_daily": round(alpha_daily, 6),
        "alpha_annualized": round(alpha_annual, 4),
        "r_squared": round(float(model.rsquared), 4),
        "factor_loadings": {
            "Mkt-RF": {"beta": round(betas[0], 4), "t_stat": round(tvals[0], 3), "p_value": round(float(model.pvalues.get("Mkt-RF", 1)), 4)},
            "SMB":    {"beta": round(betas[1], 4), "t_stat": round(tvals[1], 3), "p_value": round(float(model.pvalues.get("SMB", 1)), 4)},
            "HML":    {"beta": round(betas[2], 4), "t_stat": round(tvals[2], 3), "p_value": round(float(model.pvalues.get("HML", 1)), 4)},
        },
        "observations": int(len(aligned)),
        "period": f"{aligned.index[0].date()} to {aligned.index[-1].date()}",
        "note": "Alpha is relative to the 3-factor model. Positive alpha suggests outperformance after controlling for market, size, and value exposure.",
    }


@router.post("/rolling_betas")
def rolling_betas(req: RollingRequest):
    """Compute rolling 12-month Fama-French market beta."""
    import statsmodels.api as sm

    port_ret = _get_portfolio_returns(req.lookback_years)
    if port_ret is None or port_ret.empty:
        raise HTTPException(status_code=503, detail="Portfolio price data not yet loaded.")

    ff = _get_ff_daily()
    if ff is None:
        raise HTTPException(status_code=503, detail="Could not download Fama-French data.")

    aligned = pd.concat([port_ret.rename("R_port"), ff], axis=1).dropna()
    Y = aligned["R_port"] - aligned["RF"]
    X = aligned[["Mkt-RF", "SMB", "HML"]]

    window = req.window_months * 21  # approximate trading days
    if len(aligned) < window + 10:
        raise HTTPException(status_code=400, detail="Not enough data for rolling window.")

    dates, mkt_betas, smb_betas, hml_betas = [], [], [], []
    for i in range(window, len(aligned)):
        y_w = Y.iloc[i - window:i]
        x_w = sm.add_constant(X.iloc[i - window:i])
        try:
            m = sm.OLS(y_w, x_w).fit()
            dates.append(aligned.index[i])
            mkt_betas.append(float(m.params.get("Mkt-RF", np.nan)))
            smb_betas.append(float(m.params.get("SMB", np.nan)))
            hml_betas.append(float(m.params.get("HML", np.nan)))
        except Exception:
            continue

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=mkt_betas, mode="lines", name="Market Beta", line=dict(color="#005A9C")))
    fig.add_trace(go.Scatter(x=dates, y=smb_betas, mode="lines", name="Size Beta (SMB)", line=dict(color="#f0ad4e")))
    fig.add_trace(go.Scatter(x=dates, y=hml_betas, mode="lines", name="Value Beta (HML)", line=dict(color="#5cb85c")))
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    fig.add_hline(y=1, line_dash="dot", line_color="#005A9C", opacity=0.3)
    fig.update_layout(
        title=f"Rolling {req.window_months}-Month Factor Betas",
        xaxis_title="Date", yaxis_title="Beta",
        hovermode="x unified",
    )

    return {
        "figure": fig.to_json(),
        "window_months": req.window_months,
        "current_betas": {
            "Mkt-RF": round(mkt_betas[-1], 4) if mkt_betas else None,
            "SMB": round(smb_betas[-1], 4) if smb_betas else None,
            "HML": round(hml_betas[-1], 4) if hml_betas else None,
        },
    }
