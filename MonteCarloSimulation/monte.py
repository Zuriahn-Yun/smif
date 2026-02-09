from fastapi import FastAPI, WebSocket
from concurrent.futures import ProcessPoolExecutor
import asyncio
# https://israeldi.github.io/bookdown/_book/monte-carlo-simulation-of-stock-portfolio-in-r-matlab-and-python.html
app = FastAPI()
executor = ProcessPoolExecutor() # For the Monte Carlo math

def run_monte_carlo(data):
    # Your heavy math here
    return result

@app.websocket("/ws/finance")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        # 1. Get data from yfinance (Use a wrapper or cache)
        # 2. Offload math to separate CPU core
        loop = asyncio.get_event_loop()
        sim_result = await loop.run_in_executor(executor, run_monte_carlo, raw_data)
        
        # 3. Send to Plotly frontend
        await websocket.send_json({"plot": sim_result})
        await asyncio.sleep(1) # Respect rate limits!