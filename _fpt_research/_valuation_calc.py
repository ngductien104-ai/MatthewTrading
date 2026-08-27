import sys
sys.path.insert(0, r'C:\Users\VVVZV\MatthewTrading\agent')
import pandas as pd
import numpy as np
pd.set_option('display.max_columns', 60)
pd.set_option('display.width', 240)
from vndata import fundamental as fd, price as px

# ---------- 1. Annual data ----------
inc_y = fd.wide('FPT', 'income_statement', period='year')
bal_y = fd.wide('FPT', 'balance_sheet', period='year')
cf_y = fd.wide('FPT', 'cash_flow', period='year')
rat_y = fd.ratios_wide('FPT', period='year')

debt_cols = ['BS_SHORT_TERM_BORROWINGS','BS_LONG_TERM_BORROWINGS','BS_CASH','BS_CASH_EQUIVALENTS',
             'BS_SHORT_TERM_INVESTMENTS','BS_EQUITY','BS_MINORITY_INTEREST']
print("=== Annual BS debt/cash ===")
print(bal_y[debt_cols].to_string())

print("\n=== Annual: NI parent, capex, D&A, CFO, FCF ===")
tab = pd.DataFrame({
    'NI_parent': inc_y['IS_PROFIT_AFTER_TAX_FOR_SHAREHOLDERS_OF_PARENT_COMPANY'],
    'Interest_exp': inc_y['IS_INTEREST_EXPENSES'],
    'CFO': cf_y['CF_NET_CASH_FLOWS_FROM_OPERATING_ACTIVITIES'],
    'Capex': cf_y['CF_PAYMENTS_FOR_FIXED_ASSETS'],
    'DA': cf_y['CF_DEPRECIATION_AND_AMORTISATION'],
})
tab['FCF'] = tab['CFO'] + tab['Capex']  # capex already negative
print(tab.to_string())

print("\n=== Effective cost of debt (interest exp / avg total debt) ===")
debt = bal_y['BS_SHORT_TERM_BORROWINGS'] + bal_y['BS_LONG_TERM_BORROWINGS']
avg_debt = (debt + debt.shift(1)) / 2
eff_kd = (-inc_y['IS_INTEREST_EXPENSES']) / avg_debt  # abs value; interest exp is negative
print(pd.DataFrame({'total_debt': debt, 'avg_debt': avg_debt, 'eff_cost_of_debt': eff_kd}).to_string())

# ---------- 2. Beta regression: weekly returns FPT vs VNINDEX, 2Y ----------
print("\n=== Beta regression (weekly, 2Y) ===")
start, end = '2024-08-20', '2026-08-27'
fpt = px.ohlcv('FPT', start, end)
fpt = px.to_vnd(fpt).reset_index()[['trade_date','close']].rename(columns={'close':'fpt'})
vni = px.ohlcv('VNINDEX', start, end).reset_index()[['trade_date','close']].rename(columns={'close':'vni'})
fpt['trade_date'] = pd.to_datetime(fpt['trade_date'])
vni['trade_date'] = pd.to_datetime(vni['trade_date'])
m = pd.merge(fpt, vni, on='trade_date', how='inner').sort_values('trade_date')
m = m.set_index('trade_date')
weekly = m.resample('W-FRI').last().dropna()
ret = weekly.pct_change().dropna()
cov = np.cov(ret['fpt'], ret['vni'])
beta = cov[0,1] / cov[1,1]
print(f"n_weeks={len(ret)}, beta_raw={beta:.3f}")
# adjusted beta (Bloomberg-style): 2/3*raw + 1/3*1.0
adj_beta = (2/3)*beta + (1/3)*1.0
print(f"adjusted_beta={adj_beta:.3f}")

# ---------- 3. Latest quarter snapshot (2026-Q2) for EV bridge ----------
print("\n=== Latest quarter (2026-Q2) BS snapshot ===")
bal_q = fd.wide('FPT', 'balance_sheet', period='quarter')
latest = bal_q[debt_cols].iloc[-1]
print(latest.to_string())

print("\n=== Current price & shares (today) ===")
today = px.ohlcv('FPT', '2026-08-20', '2026-08-27')
today = px.to_vnd(today)
print(today[['close','listed_shares']].tail(5).to_string())
