import sys
sys.path.insert(0, r'C:\Users\VVVZV\MatthewTrading\agent')
import pandas as pd
pd.set_option('display.max_columns', 50)
pd.set_option('display.width', 220)
from vndata import fundamental as fd, price as px

print("=== INCOME STATEMENT (year) ===")
inc_y = fd.wide('FPT', 'income_statement', period='year')
print(inc_y.to_string())

print("\n=== BALANCE SHEET (year) ===")
bal_y = fd.wide('FPT', 'balance_sheet', period='year')
print(bal_y.to_string())

print("\n=== CASH FLOW (year) ===")
cf_y = fd.wide('FPT', 'cash_flow', period='year')
print(cf_y.to_string())

print("\n=== RATIOS (year) ===")
rat_y = fd.ratios_wide('FPT', period='year')
print(rat_y.to_string())

print("\n=== DERIVED (year) ===")
der_y = fd.derived('FPT', period='year')
print(der_y.to_string())

print("\n=== INCOME STATEMENT (quarter) - last 6 ===")
inc_q = fd.wide('FPT', 'income_statement', period='quarter')
print(inc_q.tail(6).to_string())

print("\n=== RATIOS (quarter) - last 6 ===")
rat_q = fd.ratios_wide('FPT', period='quarter')
print(rat_q.tail(6).to_string())

print("\nColumns income_y:", list(inc_y.columns))
print("Columns bal_y:", list(bal_y.columns))
print("Columns cf_y:", list(cf_y.columns))
print("Columns rat_y:", list(rat_y.columns))
