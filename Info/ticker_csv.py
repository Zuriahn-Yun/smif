import pandas as pd
import re
import csv

holdings = pd.read_csv("Excel--Schol Fund Holdings 11-30-24(Sheet1).csv")
tickers = []
for title in holdings["CBE Investment Management and Scholarship Fund"]:
    if type(title) == str:
        match = re.search(r"\(([^)]+)\)", title)
        if match:
            tickers.append(str(match.group(1)))
            
for tick in tickers:
    print(tick)
with open('tickers.csv','w',newline='') as csvfile:
    writer = csv.writer(csvfile)
    for tick in tickers:
        writer.writerow([tick])
    