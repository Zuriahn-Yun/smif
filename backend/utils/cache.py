import json
import os
import time

# --- Shared in-memory caches ---
portfolio_cache = {}    # ticker -> stockData object (price history + metadata)
sector_info_cache = {}  # ticker -> dict from yf.Ticker.info
screener_cache = {}     # ticker -> {"data": {...}, "timestamp": float}

_PORTFOLIO_PATH = os.path.join(os.path.dirname(__file__), "..", "portfolio.json")
_SCREENER_TTL = 3600  # 1 hour


def load_portfolio() -> list[dict]:
    """Load holdings from portfolio.json. Single source of truth."""
    with open(_PORTFOLIO_PATH) as f:
        return json.load(f)


def get_portfolio_tickers() -> list[str]:
    return [h["ticker"] for h in load_portfolio()]


def get_screener_cached(ticker: str) -> dict | None:
    entry = screener_cache.get(ticker)
    if entry and (time.time() - entry["timestamp"]) < _SCREENER_TTL:
        return entry["data"]
    return None


def set_screener_cached(ticker: str, data: dict):
    screener_cache[ticker] = {"data": data, "timestamp": time.time()}
