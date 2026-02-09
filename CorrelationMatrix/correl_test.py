import pandas as pd
import yfinance as yf


# Correlation matrix for two stock

# Must be in the same order as the original DF
tickers = ['VFIAX','VSMAX']

# #Periods -> 1d, 5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max
# df_multi = yf.download(tickers, period='5y')


# df_multi.to_csv("VSMAX_VFIAX_5YR.csv")

titles = ["Price","Close","High","Low","Volume"]

# should this take in the df, or the tickerrr?????????? where should it put the infooooo
def ticker_data(df,ticker,ticker_dictionary):
    ticker_index = ticker_dictionary[ticker]
    if ticker_index == 0:
        res = df[titles]
    else:
        new_titles = []
        for title in titles:
            if title == "Price":
                new_titles.append(title)
            else:
                new_titles.append(title + "." + str(ticker_index))    
        print(new_titles)
        res = df[new_titles]
    return res

# Takes in a single tickers data and calculates returns
def calculate_returns(ticker_data):
    return
if __name__ == "__main__":
    ticker_dictionary = {}
    for i in range(len(tickers)):
        ticker_dictionary[tickers[i]] = i
    
    df = pd.read_csv("VSMAX_VFIAX_5YR.csv") 
    print(df)
    vsmax = ticker_data(df,"VSMAX",ticker_dictionary)
    print(df)
    print(vsmax)