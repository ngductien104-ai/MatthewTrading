import sys
sys.path.insert(0, r'C:\Users\VVVZV\MatthewTrading\agent')
import pandas as pd
pd.set_option('display.max_columns', 50)
pd.set_option('display.width', 220)
pd.set_option('display.float_format', lambda x: f'{x:,.1f}')
from vndata import fundamental as fd

inc = fd.wide('FPT', 'income_statement', period='year')
bal = fd.wide('FPT', 'balance_sheet', period='year')
cf  = fd.wide('FPT', 'cash_flow', period='year')
rat = fd.ratios_wide('FPT', period='year')
der = fd.derived('FPT', period='year')

inc_q = fd.wide('FPT', 'income_statement', period='quarter')
rat_q = fd.ratios_wide('FPT', period='quarter')
bal_q = fd.wide('FPT', 'balance_sheet', period='quarter')
cf_q  = fd.wide('FPT', 'cash_flow', period='quarter')

df = pd.DataFrame(index=inc.index)
df['Revenue'] = inc['IS_NET_REVENUE']
df['RevGrowth%'] = df['Revenue'].pct_change()*100
df['GrossProfit'] = inc['IS_GROSS_PROFIT']
df['GrossMargin%'] = df['GrossProfit']/df['Revenue']*100
df['SG&A'] = inc['IS_GENERAL_AND_ADMINISTRATIVE_EXPENSES'] + inc['IS_SELLING_EXPENSES']
df['SGA_%Rev'] = -df['SG&A']/df['Revenue']*100
df['OperatingProfit'] = inc['IS_OPERATING_PROFIT']
df['OpMargin%'] = df['OperatingProfit']/df['Revenue']*100
df['FinIncome'] = inc['IS_FINANCIAL_INCOME']
df['FinExpense'] = inc['IS_FINANCIAL_EXPENSES']
df['InterestExpense'] = inc['IS_INTEREST_EXPENSES']
df['OtherIncome'] = inc['IS_OTHER_INCOME']
df['OtherExpense'] = inc['IS_OTHER_EXPENSES']
df['OtherProfit'] = inc['IS_OTHER_PROFIT']
df['PretaxProfit'] = inc['IS_PROFIT_BEFORE_TAX']
df['NetProfit_total'] = inc['IS_NET_PROFIT_AFTER_TAX']
df['NPATMI_parent'] = inc['IS_PROFIT_AFTER_TAX_FOR_SHAREHOLDERS_OF_PARENT_COMPANY']
df['NetMargin%_parent'] = df['NPATMI_parent']/df['Revenue']*100
df['MinorityInterest'] = der['minority_interest']
df['EPS_basic'] = inc['IS_BASIC_EARNINGS_PER_SHARE']

df['OCF'] = cf['CF_NET_CASH_FLOWS_FROM_OPERATING_ACTIVITIES']
df['Capex'] = cf['CF_PAYMENTS_FOR_FIXED_ASSETS']
df['FCF'] = df['OCF'] + df['Capex']  # capex already negative
df['OCF/NetProfit'] = df['OCF']/df['NetProfit_total']
df['FCFMargin%'] = df['FCF']/df['Revenue']*100
df['CapexIntensity%'] = -df['Capex']/df['Revenue']*100

df['TotalAssets'] = bal['BS_TOTAL_ASSETS']
df['TotalLiab'] = bal['BS_TOTAL_LIABILITIES']
df['Equity'] = der['equity']
df['ShortTermBorrow'] = bal['BS_SHORT_TERM_BORROWINGS']
df['LongTermBorrow'] = bal['BS_LONG_TERM_BORROWINGS']
df['TotalBorrow'] = df['ShortTermBorrow'] + df['LongTermBorrow']
df['Cash'] = bal['BS_CASH_AND_PRECIOUS_METALS'] if 'BS_CASH_AND_PRECIOUS_METALS' in bal.columns else bal['BS_CASH']
df['CashEquiv'] = bal['BS_CASH_EQUIVALENTS']
df['CashTotal'] = df['Cash'] + df['CashEquiv']
df['NetDebt'] = df['TotalBorrow'] - df['CashTotal']
df['NetDebt/Equity'] = df['NetDebt']/df['Equity']
df['CurrentAssets'] = bal['BS_SHORT_TERM_ASSETS']
df['CurrentLiab'] = bal['BS_SHORT_TERM_LIABILITIES']
df['CurrentRatio'] = df['CurrentAssets']/df['CurrentLiab']
df['Receivables'] = bal['BS_SHORT_TERM_RECEIVABLES']
df['Inventory'] = bal['BS_INVENTORIES']
df['ARDays'] = df['Receivables']/df['Revenue']*365
df['InvDays'] = -df['Inventory']/inc['IS_COST_OF_GOODS_SOLD']*365
df['InterestCoverage'] = df['OperatingProfit']/(-df['InterestExpense'])

df['ROE%'] = rat['RT_PRT_ROE']
df['ROA%'] = rat['RT_PRT_ROA']
df['ROIC%'] = rat['RT_PRT_ROIC']
df['D/E_ratio'] = rat['RT_LEV_DE']
df['CurrentRatio_src'] = rat['RT_LQD_CR']
df['QuickRatio_src'] = rat['RT_LQD_QR']

print(df.T.to_string())

print("\n\n=== Quarterly YoY check (Q2 2025 vs Q2 2026) ===")
q_cols = ['IS_NET_REVENUE','IS_GROSS_PROFIT','IS_PROFIT_AFTER_TAX_FOR_SHAREHOLDERS_OF_PARENT_COMPANY','IS_NET_PROFIT_AFTER_TAX','IS_FINANCIAL_INCOME','IS_FINANCIAL_EXPENSES','IS_OTHER_INCOME']
print(inc_q[q_cols].tail(6).to_string())

print("\n=== Q2 2026 vs Q2 2025 YoY % ===")
q2_26 = inc_q.loc['2026-Q2']
q2_25 = inc_q.loc['2025-Q2']
for c in q_cols:
    try:
        chg = (q2_26[c]-q2_25[c])/abs(q2_25[c])*100
        print(f"{c}: 2025Q2={q2_25[c]:,.0f}  2026Q2={q2_26[c]:,.0f}  YoY={chg:.1f}%")
    except Exception as e:
        print(c, "error", e)

print("\n=== H1 2026 vs H1 2025 ===")
h1_26 = inc_q.loc[['2026-Q1','2026-Q2']].sum()
h1_25 = inc_q.loc[['2025-Q1','2025-Q2']].sum()
for c in q_cols:
    chg = (h1_26[c]-h1_25[c])/abs(h1_25[c])*100
    print(f"{c}: H1'25={h1_25[c]:,.0f}  H1'26={h1_26[c]:,.0f}  YoY={chg:.1f}%")

print("\n=== Q2 2026 balance sheet snapshot ===")
bcols = ['BS_TOTAL_ASSETS','BS_TOTAL_LIABILITIES','BS_EQUITY','BS_SHORT_TERM_BORROWINGS','BS_LONG_TERM_BORROWINGS','BS_CASH_AND_PRECIOUS_METALS','BS_CASH_EQUIVALENTS','BS_SHORT_TERM_RECEIVABLES','BS_INVENTORIES']
print(bal_q[bcols].tail(3).to_string())

print("\n=== Q2 2026 cash flow ===")
ccols = ['CF_NET_CASH_FLOWS_FROM_OPERATING_ACTIVITIES','CF_PAYMENTS_FOR_FIXED_ASSETS','CF_NET_CASH_FLOWS_FROM_INVESTING_ACTIVITIES']
print(cf_q[ccols].tail(3).to_string())

print("\n=== rat_q ROE/ROA/ROIC/D-E/current last 6 ===")
rcols = ['RT_PRT_ROE','RT_PRT_ROA','RT_PRT_ROIC','RT_LEV_DE','RT_LQD_CR']
print(rat_q[rcols].tail(6).to_string())
