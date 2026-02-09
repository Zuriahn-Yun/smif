import pandas as pd
import yfinance as yf 
import plotly.express as px
from dash import Dash, dcc, html
import dash_bootstrap_components as dbc
import csv

# All the tickers we use, It cannot find "HWN" and "Walt"
ticker_list = ['VSMAX', 'VFIAX', 'SSIFX', 'VIMAX', 'EEM', 'EFA', 'AGCO', 'ADBE', 'GOOG', 'AMGN', 'AAPL', 'BAC', 'BVNKF', 'BDX', 'BSX', 'BLDR', 'CAT', 'CHD', 'CI', 'CMCSA', 'GLW', 'WBD', 'ECL', 'EMBC', 'FFIV', 'FDX', 'FSUMF', 'GRAL', 'GBX', 'ILMN', 'IART', 'JPM', 'KLIC', 'LMNR', 'LKQ', 'MHH', 'MSFT', 'NGVC', 'NKE', 'NWPX', 'NVDA', 'PANW', 'SMG', 'EQNR', 'COHR', 'VKTX', 'SW', 'ORC', 'WY']


time_period = "10y"
# Periods -> 1d, 5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max
data= yf.download(ticker_list, period=time_period)["Close"]


# Calculate returns, periods: Periods to shift for forming percent change.
daily_returns = data.pct_change(periods=1).dropna()


# Compute the Correlation Matrix using pearson correlation coefficient
# Pearson Correlation Coeffcient r = Σ(xi - x_mean)(Σyi - y_mean) / sqrt(Σ(xi - x_mean)^2 (Σ(yi - y_mean)^2))
correlation_matrix = daily_returns.corr()
correlation_matrix.to_csv('correlation.csv', index=False)
print(correlation_matrix.size)

print("Stock Correlation Matrix:")
print(correlation_matrix)

high_correlation = []

for index, row in correlation_matrix.iterrows():
    for column_name, value in row.items():
        print(f"Row Index: {index}, Column Title: {column_name}, Value: {value}")
        if float(value) >= 0.75:
            if index != column_name:   
                high_correlation.append([index,column_name,value])
            
print(high_correlation)

with open("high_correlation_tickers.csv", "w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(high_correlation)

# title = "Portfolio Correlation Matrix, Time Period: " + str(time_period)
# fig = px.imshow(
#     correlation_matrix,
#     text_auto=True,         
#     color_continuous_scale='portland',  
#     zmin=-1, zmax=1,        
#     title=title
# )
# fig.write_html("Correlation Matrix 10 Years.html")
# For normal Dashboard, local
#fig.show()
#write_html(fig)
