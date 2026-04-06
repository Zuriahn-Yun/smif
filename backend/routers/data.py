from fastapi import APIRouter
from ..utils.cache import load_portfolio

router = APIRouter()


@router.post("/smifData")
def get_smif_tickers():
    """Return the list of portfolio tickers from the canonical portfolio.json."""
    holdings = load_portfolio()
    return [h["ticker"] for h in holdings]
