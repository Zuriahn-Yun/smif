import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .routers.monte import lifespan
from .routers import monte, data, sector, rebalance, fundamentals, screener, optimizer, backtest, factors, ai_research

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

app = FastAPI(
    title="SMIF Portfolio Tools",
    description="Student Managed Investment Fund — Analytics Platform",
    version="2.0.0",
    lifespan=lifespan,
)

# --- API Routers ---
app.include_router(data.router,         prefix="/data",         tags=["Data"])
app.include_router(monte.router,        prefix="/monte",        tags=["Monte Carlo"])
app.include_router(sector.router,       prefix="/sector",       tags=["Sector Analysis"])
app.include_router(rebalance.router,    prefix="/rebalance",    tags=["Rebalancing"])
app.include_router(fundamentals.router, prefix="/fundamentals", tags=["Fundamentals"])
app.include_router(screener.router,     prefix="/screener",     tags=["Stock Screener"])
app.include_router(optimizer.router,    prefix="/optimizer",    tags=["Portfolio Optimizer"])
app.include_router(backtest.router,     prefix="/backtest",     tags=["Backtesting"])
app.include_router(factors.router,      prefix="/factors",      tags=["Factor Analysis"])
app.include_router(ai_research.router,  prefix="/ai",           tags=["AI Research"])

# --- Health check ---
@app.get("/health")
async def health():
    return {"status": "ok"}

# --- Static frontend ---
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# --- Root: serve the SPA ---
@app.get("/")
async def root():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
