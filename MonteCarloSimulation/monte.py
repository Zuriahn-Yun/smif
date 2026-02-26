from fastapi import WebSocket, APIRouter,FastAPI
from contextlib import asynccontextmanager
import pandas as pd
import yfinance as yf 
from pydantic import BaseModel
import numpy as np 
import plotly.express as px
import plotly.graph_objects as go

# https://www.cmor-faculty.rice.edu/~cox/stoch/dhigham.pdf

smifTickers = ['VSMAX', 'VFIAX', 'SSIFX', 'VIMAX', 'EEM', 'EFA', 'AGCO', 'ADBE', 'GOOG', 'AMGN', 'AAPL', 'BAC', 'BVNKF', 'BDX', 'BSX', 'BLDR', 'CAT', 'CHD', 'CI', 'CMCSA', 'GLW', 'WBD', 'ECL', 'EMBC', 'FFIV', 'FDX', 'FSUMF', 'GRAL', 'GBX', 'ILMN', 'IART', 'JPM', 'KLIC', 'LMNR', 'LKQ', 'MHH', 'MSFT', 'NGVC', 'NKE', 'NWPX', 'NVDA', 'PANW', 'SMG', 'EQNR', 'COHR', 'VKTX', 'SW', 'ORC', 'WY']

portfolio_cache = {}

# To hold our Stock Data for each ticker 
class stockData:
    def __init__(self, ticker, data):
        self.ticker = ticker
        self.data = data
        
    def addPaths(self,paths,mean_path):
        self.paths = paths
        self.mean_path = mean_path
        
    # Calculate new estimated amount
    def estimate_holdings(amount_held):
        return amount_held

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Fetching Portfolio Data")
    
    for ticker in smifTickers:
        try:
            data = get_data(ticker)
    
            stock_obj = stockData(ticker, data) 
            
            # Store the object in the cache dictionary using the ticker as the key
            portfolio_cache[ticker] = stock_obj
            print(f"Successfully loaded {ticker}")
            
        except Exception as e:
            print(f"{ticker} Not Found: {e}")
            
    print("Data Loaded.")
    
    yield
    
    # After the Server Has been Shut Down
    print("Shutting down and clearing cache.")
    portfolio_cache.clear()

router = APIRouter()

def get_data(ticker):
    return yf.download(str(ticker),period="max",interval="1d")


# This is assuming that we have not retrived the data yet
# N: Steps
# T: Time
# M: Paths
# @router.post("/gbm")
# def geometric_brownian_motion(ticker,M = 10,N=255,T=1):
#     try:
#         res = []
#         data = get_data(ticker)
#         close_data = data["Close"]
        
#         # Most Recent Price
#         S0 = close_data.iloc[-1].iloc[0]
        
#         dt = T/N
        
#         # close data updated to exclude most recent day
#         close_data = close_data[:-1]
#         #print("Most Recent Close: ", St)
#         last_year = close_data.tail(252)
        
#         log_returns = []
#         for i in range(1,len(last_year)):
#             r = np.log(last_year.iloc[i].iloc[0] / last_year.iloc[i-1].iloc[0])
#             log_returns.append(r)
            
#         log_returns = pd.Series(log_returns)
#         u = log_returns.mean()
#         print("Mean: ", u)
#         # sig = volatility
#         sig = np.std(log_returns)
#         print("Volatility: ", sig)

#         for j in range(M):        
#             current_path = [S0]
#             St = S0
#             for step in range(N):   
#                 # Z = Random noise
#                 Z = np.random.normal(loc=0.0,scale=1.0)
#                 # Discrete Time Solution
#                 curr = St * np.exp((u - (sig**2/2)) * (dt) + sig * np.sqrt(dt) * Z)
#                 current_path.append(curr)
#                 St = curr
#             res.append(current_path)
#         # Res will have M many different Paths
#         return res
#     except Exception as e:
#         print("Exception: ", e)

# Get geometric brownian motion when we already have the data
def gbm(data,M = 10,N=255,T=1):
    try:
        close_data = data["Close"]
        res = []
        # Most Recent Price
        S0 = close_data.iloc[-1].iloc[0]
            
        dt = T/N
            
        # close data updated to exclude most recent day
        close_data = close_data[:-1]
        #print("Most Recent Close: ", St)
        last_year = close_data.tail(252)
            
        log_returns = []
        for i in range(1,len(last_year)):
            r = np.log(last_year.iloc[i].iloc[0] / last_year.iloc[i-1].iloc[0])
            log_returns.append(r)
            u = np.mean(log_returns)
            print("Mean: ", u)
            # sig = volatility
            sig = np.std(log_returns)
            print("Volatility: ", sig)

            for j in range(M):        
                current_path = [S0]
                St = S0
                for step in range(N):   
                    # Z = Random noise
                    Z = np.random.normal(loc=0.0,scale=1.0)
                    # Discrete Time Solution
                    curr = St * np.exp((u - (sig**2/2)) * (dt) + sig * np.sqrt(dt) * Z)
                    current_path.append(curr)
                    St = curr
                res.append(current_path)
        # Res will have M many different Paths
        return res
    except Exception as e:
        print("Exception: ", e)
    
        
@router.post("/plot_gbm")
def plot_gbm(paths):
    df = pd.DataFrame(paths).T
    row_means = df.mean(axis=1, numeric_only=True)
    fig = px.line(df,title="Geometric Brownian Motion")
    
    fig.update_layout(showlegend=False,xaxis_title="Days",yaxis_title="Price",)

    fig.add_trace(
    go.Scatter(
        y=row_means, 
        mode='lines', 
        line=dict(color='black', width=3), 
        name='Expected Mean'
        )
    )
    return fig.to_json()
    
@router.post("/generate_display")
def generate_display(ticker):
    if ticker not in portfolio_cache:
        return {"error": "Ticker not found in cache."}
    
    stock_obj = portfolio_cache[ticker]
    
    # Check if we've already done the GBM math for this stock
    if stock_obj.paths is None:
        print(f"Calculating GBM for {ticker}...")
        paths = gbm(stock_obj.data)
        
        if not paths:
            return {"error": "Failed to calculate GBM paths."}
            
        # Save the calculation back to the object so we never have to run it again
        df = pd.DataFrame(paths)
        mean_path = df.mean(axis=0, numeric_only=True).tolist()
        stock_obj.addPaths(paths, mean_path)
    
    # Return the plot using the cached paths
    return plot_gbm(stock_obj.paths) 

# This is not very useful
@router.post("/smif_monte")
def generate_smif_simulations():
    all_paths = {}
    all_stockData = []
    
    for obj in portfolio_cache:
        try:
            # Assuming paths is a 2D array [num_sims, steps]
            paths = gbm(obj.data)          
            if not paths:
                continue
            
            df = pd.DataFrame(paths)
            all_paths[obj.ticker] = df.mean(axis=0,numeric_only=False)
            
        except Exception as e: 
            print(f"Error for {obj.ticker}: {e}")
            continue

    # Convert the mean paths into a DataFrame for easy plotting
    df_plot = pd.DataFrame(all_paths)
    
    # Use Plotly Express for much cleaner syntax
    fig = px.line(df_plot, labels={'index': 'Time', 'value': 'Price'})
    
    fig.update_layout(title="SMIF Monte Carlo: Average Projected Paths")
    
    # Return JSON instead of .show() for web apps
    return fig.to_json()

def main():
    # Testing Box
    print("Testing")

if __name__ == "__main__":
    main()