import yfinance as yf
import pandas as pd
import time
from .cache import portfolio_cache, sector_info_cache


def get_historical(ticker: str, period: str = "2y") -> pd.DataFrame:
    """Return historical OHLCV data, using portfolio_cache when available."""
    if ticker in portfolio_cache and portfolio_cache[ticker].data is not None:
        return portfolio_cache[ticker].data
    return yf.download(str(ticker), period=period, interval="1d",
                       auto_adjust=True, progress=False)


def get_info(ticker: str) -> dict:
    """Return yfinance .info dict, using sector_info_cache when available."""
    if ticker in sector_info_cache:
        return sector_info_cache[ticker]
    time.sleep(0.4)
    info = yf.Ticker(ticker).info
    sector_info_cache[ticker] = info
    return info


def safe_float(val, default=None):
    """Convert a value to float, returning default on failure."""
    try:
        return float(val) if val is not None else default
    except (TypeError, ValueError):
        return default
