from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import time
import yfinance as yf

router = APIRouter()

_call_timestamps: list[float] = []
_RATE_LIMIT = 10  # max calls per minute
_RATE_WINDOW = 60.0


def _check_rate_limit():
    now = time.time()
    # Remove timestamps older than window
    while _call_timestamps and now - _call_timestamps[0] > _RATE_WINDOW:
        _call_timestamps.pop(0)
    if len(_call_timestamps) >= _RATE_LIMIT:
        raise HTTPException(status_code=429,
                            detail="Rate limit reached (10 AI calls/minute). Please wait a moment.")
    _call_timestamps.append(now)


def _get_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503,
                            detail="AI research is not configured. ANTHROPIC_API_KEY environment variable is missing.")
    try:
        import anthropic
        return anthropic.Anthropic(api_key=api_key)
    except ImportError:
        raise HTTPException(status_code=503,
                            detail="anthropic package not installed. Add it to requirements.txt.")


def _get_ticker_context(ticker: str) -> str:
    try:
        t = yf.Ticker(ticker.upper())
        info = t.info
        news = t.news or []
        lines = [
            f"Company: {info.get('longName', ticker)}",
            f"Sector: {info.get('sector', 'N/A')} / {info.get('industry', 'N/A')}",
            f"Market Cap: {info.get('marketCap', 'N/A')}",
            f"Trailing P/E: {info.get('trailingPE', 'N/A')}",
            f"Revenue Growth: {info.get('revenueGrowth', 'N/A')}",
            f"Profit Margin: {info.get('profitMargins', 'N/A')}",
            f"52-Week High: {info.get('fiftyTwoWeekHigh', 'N/A')}",
            f"52-Week Low: {info.get('fiftyTwoWeekLow', 'N/A')}",
            "",
            f"Business Summary: {info.get('longBusinessSummary', 'Not available.')[:800]}",
            "",
            "Recent News Headlines:",
        ]
        for article in news[:5]:
            title = article.get("title", "")
            if title:
                lines.append(f"  - {title}")
        return "\n".join(lines)
    except Exception as e:
        return f"(Could not fetch data for {ticker}: {e})"


class SummarizeRequest(BaseModel):
    ticker: str
    query: str = "Summarize the investment thesis, key risks, and recent developments."


class CompareRequest(BaseModel):
    tickers: list[str]
    focus: str = "valuation and growth prospects"


@router.post("/summarize_ticker")
def summarize_ticker(req: SummarizeRequest):
    _check_rate_limit()
    client = _get_client()

    context = _get_ticker_context(req.ticker)
    prompt = (
        f"You are a financial analyst assistant for a student investment fund.\n\n"
        f"Here is data for {req.ticker.upper()}:\n{context}\n\n"
        f"User query: {req.query}\n\n"
        f"Provide a concise, analytical response (3-5 paragraphs). "
        f"Focus on investment-relevant insights. Avoid generic disclaimers."
    )

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )

    return {
        "ticker": req.ticker.upper(),
        "query": req.query,
        "response": message.content[0].text,
    }


@router.post("/compare_tickers")
def compare_tickers(req: CompareRequest):
    _check_rate_limit()
    client = _get_client()

    if len(req.tickers) < 2 or len(req.tickers) > 5:
        raise HTTPException(status_code=400, detail="Provide 2-5 tickers for comparison.")

    contexts = []
    for ticker in req.tickers[:5]:
        ctx = _get_ticker_context(ticker)
        contexts.append(f"=== {ticker.upper()} ===\n{ctx}")

    combined = "\n\n".join(contexts)
    prompt = (
        f"You are a financial analyst assistant for a student investment fund.\n\n"
        f"Compare the following companies with focus on: {req.focus}\n\n"
        f"{combined}\n\n"
        f"Provide a structured comparison covering: "
        f"(1) relative valuation, (2) growth outlook, (3) key risks, (4) investment recommendation. "
        f"Be concise and analytical."
    )

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )

    return {
        "tickers": [t.upper() for t in req.tickers],
        "focus": req.focus,
        "response": message.content[0].text,
    }
