from fastapi import WebSocket, APIRouter
import pandas as pd
import yfinance as yf 
from pydantic import BaseModel
import numpy as np 
import plotly.express as px
import plotly.graph_objects as go

# https://www.cmor-faculty.rice.edu/~cox/stoch/dhigham.pdf

smifTickers = ['VSMAX', 'VFIAX', 'SSIFX', 'VIMAX', 'EEM', 'EFA', 'AGCO', 'ADBE', 'GOOG', 'AMGN', 'AAPL', 'BAC', 'BVNKF', 'BDX', 'BSX', 'BLDR', 'CAT', 'CHD', 'CI', 'CMCSA', 'GLW', 'WBD', 'ECL', 'EMBC', 'FFIV', 'FDX', 'FSUMF', 'GRAL', 'GBX', 'ILMN', 'IART', 'JPM', 'KLIC', 'LMNR', 'LKQ', 'MHH', 'MSFT', 'NGVC', 'NKE', 'NWPX', 'NVDA', 'PANW', 'SMG', 'EQNR', 'COHR', 'VKTX', 'SW', 'ORC', 'WY']

router = APIRouter()

class Stock(BaseModel):
    tickeer: str
    # Define a pandas df
    description: str |None = None


def get_data(ticker):
    return yf.download(str(ticker),period="max",interval="1d")

# N: Steps
# T: Time
# M: Paths
@router.post("/gbm")
def geometric_brownian_motion(ticker,M = 10,N=255,T=1):
    try:
        res = []
        data = get_data(ticker)
        close_data = data["Close"]
        
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
    fig.show()
    
@router.post("/generate_display")
def generate_display(ticker):
    paths = geometric_brownian_motion(ticker)
    plot_gbm(paths)
    
class stockData:
    def __init__(self, ticker, data):
        self.ticker = ticker
        self.data = data
        
    def addPaths(self,paths):
        self.paths = paths
        
@router.post("/smif_monte")
def generate_smif_simulations():
    all_paths = {}
    
    for ticker in smifTickers:
        try:
            data = get_data(ticker)
            stock = stockData(ticker, data)
            # Assuming paths is a 2D array [num_sims, steps]
            paths = geometric_brownian_motion(stock)
            
            # Use the mean of all simulations for a cleaner chart
            all_paths[ticker] = paths.mean(axis=0) 
        except Exception as e: 
            print(f"Error for {ticker}: {e}")
            continue

    # Convert the mean paths into a DataFrame for easy plotting
    df_plot = pd.DataFrame(all_paths)
    
    # Use Plotly Express for much cleaner syntax
    fig = px.line(df_plot, labels={'index': 'Time', 'value': 'Price'})
    
    fig.update_layout(title="SMIF Monte Carlo: Average Projected Paths")
    
    # Return JSON instead of .show() for web apps
    fig.show()
if __name__ == "__main__":
    generate_smif_simulations()