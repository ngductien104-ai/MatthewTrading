import sys
sys.path.insert(0, r'C:\Users\VVVZV\MatthewTrading\agent')
import pandas as pd
import numpy as np
pd.set_option('display.max_columns', 60)
pd.set_option('display.width', 240)
from vndata import fundamental as fd, price as px

print("=== BALANCE SHEET (quarter) - last 6, debt/cash cols ===")
bal_q = fd.wide('FPT', 'balance_sheet', period='quarter')
cols = ['BS_SHORT_TERM_BORROWINGS','BS_LONG_TERM_BORROWINGS','BS_CASH','BS_CASH_EQUIVALENTS',
        'BS_SHORT_TERM_INVESTMENTS','BS_EQUITY','BS_MINORITY_INTEREST','BS_TOTAL_ASSETS','BS_TOTAL_LIABILITIES']
print(bal_q[cols].tail(6).to_string())

print("\n=== CASH FLOW (quarter) - last 6, capex/D&A ===")
cf_q = fd.wide('FPT', 'cash_flow', period='quarter')
cols2 = ['CF_NET_CASH_FLOWS_FROM_OPERATING_ACTIVITIES','CF_PAYMENTS_FOR_FIXED_ASSETS',
         'CF_DEPRECIATION_AND_AMORTISATION','CF_INTEREST_PAID','CF_DIVIDENDS_PAID']
print(cf_q[cols2].tail(6).to_string())

print("\n=== Diluted shares check: BS treasury / charter capital latest ===")
print(bal_q[['BS_CHARTER_CAPITAL','BS_TREASURY_SHARES']].tail(4).to_string())

print("\n=== Weekly beta calc: FPT vs VNINDEX, 2Y lookback ===")
end = '2026-08-27'
start = '2024-08-27'
fpt = px.ohlcv('FPT', start, end)
fpt = px.to_vnd(fpt).reset_index()
fpt['trade_date'] = pd.to_datetime(fpt['trade_date'])
try:
    vni = px.ohlcv('VNINDEX', start, end)
    vni = vni.reset_index()
    vni['trade_date'] = pd.to_datetime(vni['trade_date'])
    print("VNINDEX rows:", len(vni), vni.columns.tolist())
except Exception as e:
    print("VNINDEX ohlcv failed:", e)
