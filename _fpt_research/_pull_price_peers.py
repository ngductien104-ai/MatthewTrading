import sys
sys.path.insert(0, r'C:\Users\VVVZV\MatthewTrading\agent')
import pandas as pd
pd.set_option('display.max_columns', 50)
pd.set_option('display.width', 220)
from vndata import fundamental as fd, price as px

print("=== FPT recent price (last 15 sessions) ===")
df = px.ohlcv('FPT', '2026-07-01', '2026-08-27')
df = px.to_vnd(df)
print(df.tail(15).to_string())

print("\n=== FPT year-end closes (2018-2025), for historical multiple reconstruction ===")
full = px.ohlcv('FPT', '2018-01-01', '2026-08-27')
full = px.to_vnd(full)
full = full.reset_index()
full['trade_date'] = pd.to_datetime(full['trade_date'])
full['year'] = full['trade_date'].dt.year
yearend = full.sort_values('trade_date').groupby('year').tail(1)
print(yearend[['trade_date','close','listed_shares']].to_string())

print("\n=== Reference: try symbols_by_industry for tech/IT peers ===")
try:
    from vndata import reference as ref
    peers = ref.symbols_by_industry('FPT')
    print(peers)
except Exception as e:
    print("reference module/method failed:", e)

print("\n=== Try company overview for FPT (industry / is_bank) ===")
try:
    ov = fd.wide  # placeholder check
except Exception as e:
    pass

for sym in ['CMG', 'ELC', 'ITD', 'SAM']:
    try:
        r = fd.ratios_wide(sym, period='year')
        print(f"\n--- {sym} ratios tail ---")
        print(r.tail(3).to_string())
    except Exception as e:
        print(f"{sym} failed: {e}")
