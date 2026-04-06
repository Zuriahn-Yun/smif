from fastapi import APIRouter
from contextlib import asynccontextmanager
from fastapi import FastAPI
import pandas as pd
import yfinance as yf
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from ..utils.cache import portfolio_cache, load_portfolio

# https://www.cmor-faculty.rice.edu/~cox/stoch/dhigham.pdf

router = APIRouter()


class stockData:
    def __init__(self, ticker: str, data, shares: int, description: str):
        self.ticker = ticker
        self.data = data
        self.shares = shares
        self.description = description
        self.paths = None
        self.mean_path = None

    def addPaths(self, paths, mean_path):
        self.paths = paths
        self.mean_path = mean_path


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Fetching Portfolio Data...")
    holdings = load_portfolio()

    for holding in holdings:
        ticker = holding["ticker"]
        shares = holding.get("shares", 0)
        description = holding.get("description", "")
        try:
            data = yf.download(ticker, period="2y", interval="1d",
                               auto_adjust=True, progress=False)
            stock_obj = stockData(ticker, data, shares, description)
            portfolio_cache[ticker] = stock_obj
            print(f"  Loaded {ticker}")
        except Exception as e:
            print(f"  {ticker} failed: {e}")

    print(f"Data loaded: {len(portfolio_cache)} tickers.")
    yield

    print("Shutting down — clearing cache.")
    portfolio_cache.clear()


def _get_last_price(stock_obj) -> float:
    close = stock_obj.data["Close"]
    val = close.iloc[-1]
    return float(val.iloc[0]) if isinstance(val, pd.Series) else float(val)


def gbm(data: pd.DataFrame, M: int = 10, N: int = 255, T: float = 1.0) -> list:
    try:
        close = data["Close"]
        if isinstance(close, pd.DataFrame):
            prices = close.iloc[:, 0]
        else:
            prices = close

        S0 = float(prices.iloc[-1])
        dt = T / N

        last_year = prices.iloc[:-1].tail(252)
        log_returns = np.log(last_year / last_year.shift(1)).dropna()

        if len(log_returns) < 10:
            return []

        u = float(log_returns.mean())
        sig = float(log_returns.std())

        res = []
        for _ in range(M):
            path = [S0]
            St = S0
            for _ in range(N):
                Z = np.random.normal(0.0, 1.0)
                St = St * np.exp((u - sig ** 2 / 2) * dt + sig * np.sqrt(dt) * Z)
                path.append(St)
            res.append(path)
        return res
    except Exception as e:
        print(f"GBM error: {e}")
        return []


@router.get("/portfolio_overview")
def get_portfolio_overview():
    if not portfolio_cache:
        return {"status": "loading", "message": "Backend is still fetching market data..."}

    overview_data = []
    total_fund_value = 0.0

    for ticker, stock_obj in portfolio_cache.items():
        try:
            last_price = _get_last_price(stock_obj)
            estimated_value = last_price * stock_obj.shares
            total_fund_value += estimated_value
            overview_data.append({
                "ticker": ticker,
                "shares": stock_obj.shares,
                "last_price": round(last_price, 2),
                "estimated_value": round(estimated_value, 2),
                "description": stock_obj.description,
            })
        except Exception as e:
            print(f"Overview error for {ticker}: {e}")

    overview_data.sort(key=lambda x: x["estimated_value"], reverse=True)
    return {"status": "success", "total_value": round(total_fund_value, 2), "assets": overview_data}


@router.post("/plot_gbm")
def plot_gbm(paths: list):
    df = pd.DataFrame(paths).T
    row_means = df.mean(axis=1, numeric_only=True)
    fig = px.line(df, title="Geometric Brownian Motion")
    fig.update_layout(showlegend=False, xaxis_title="Days", yaxis_title="Price")
    fig.add_trace(go.Scatter(
        y=row_means, mode="lines",
        line=dict(color="black", width=3), name="Expected Mean"
    ))
    return fig.to_json()


@router.post("/generate_display")
def generate_display(ticker: str):
    if ticker not in portfolio_cache:
        return {"error": "Ticker not found in cache."}

    stock_obj = portfolio_cache[ticker]

    if stock_obj.paths is None:
        paths = gbm(stock_obj.data)
        if not paths:
            return {"error": "Failed to calculate GBM paths."}
        df = pd.DataFrame(paths)
        mean_path = df.mean(axis=0, numeric_only=True).tolist()
        stock_obj.addPaths(paths, mean_path)

    return plot_gbm(stock_obj.paths)


@router.post("/smif_monte")
def generate_smif_simulations():
    all_paths = {}
    for ticker, obj in portfolio_cache.items():
        try:
            paths = gbm(obj.data)
            if not paths:
                continue
            df = pd.DataFrame(paths)
            all_paths[ticker] = df.mean(axis=0, numeric_only=True)
        except Exception as e:
            print(f"Monte error for {ticker}: {e}")

    if not all_paths:
        return {"error": "No simulation data available."}

    df_plot = pd.DataFrame(all_paths)
    fig = px.line(df_plot, labels={"index": "Days", "value": "Price"})
    fig.update_layout(title="SMIF Monte Carlo: Average Projected Paths")
    return fig.to_json()
