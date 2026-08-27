import sys
sys.path.insert(0, r'C:\Users\VVVZV\MatthewTrading\agent')
import pandas as pd
pd.set_option('display.max_colwidth', 200)
pd.set_option('display.width', 220)
from vndata import news

df = news.company_news('FPT')
print(df.shape)
print(df.columns.tolist())
df2 = df.copy()
# try to find a date column
for c in df2.columns:
    if 'date' in c.lower() or 'time' in c.lower():
        print("date col:", c)
print(df2.head(40).to_string())
