import pandas as pd
import yfinance as yf 
import csv
import time 
from fastapi import WebSocket, APIRouter

smifTickers = ['VSMAX', 'VFIAX', 'SSIFX', 'VIMAX', 'EEM', 'EFA', 'AGCO', 'ADBE', 'GOOG', 'AMGN', 'AAPL', 'BAC', 'BVNKF', 'BDX', 'BSX', 'BLDR', 'CAT', 'CHD', 'CI', 'CMCSA', 'GLW', 'WBD', 'ECL', 'EMBC', 'FFIV', 'FDX', 'FSUMF', 'GRAL', 'GBX', 'ILMN', 'IART', 'JPM', 'KLIC', 'LMNR', 'LKQ', 'MHH', 'MSFT', 'NGVC', 'NKE', 'NWPX', 'NVDA', 'PANW', 'SMG', 'EQNR', 'COHR', 'VKTX', 'SW', 'ORC', 'WY']

router = APIRouter()


# POST SMIF DATA
@router.post("/smifData")
def getSmifTickers():
    return smifTickers
