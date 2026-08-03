---
name: yfinance
description: "yfinance global market data interface — OHLCV, financials, insider transactions, institutional holdings for US/HK stocks, ETFs and indices. Với người dùng VN: đây là nguồn dữ liệu NGOẠI BIÊN (DXY, lợi suất Mỹ, vàng, dầu, USD/VND, peer EM) — KHÔNG dùng cho cổ phiếu VN. Free, no API key."
category: data-source
---
# yfinance

## Overview

yfinance is an open-source Python wrapper for Yahoo Finance, providing global market data (US stocks, HK stocks, ETFs, indices) including historical and real-time quotes. **Completely free, no registration or API key required.**

The project has a built-in yfinance DataLoader (`backtest/loaders/yfinance_loader.py`). When backtesting, set `source: "yfinance"` or `source: "auto"` to invoke it automatically.

> ### ⚠️ Với thị trường Việt Nam — đọc trước khi dùng
>
> **yfinance KHÔNG phải nguồn dữ liệu cổ phiếu VN.** Yahoo Finance không có dữ liệu ổn định, đáng tin cậy cho cổ phiếu niêm yết HOSE/HNX/UPCoM và VN-Index. Chuỗi định tuyến của dự án đã cấu hình sẵn: `vn_equity → ["datapro", "vnstock"]` (xem `backtest/loaders/registry.py`). Đừng lách bằng cách tra ticker VN trên Yahoo — dữ liệu thiếu, sai điều chỉnh giá và không có giá tham chiếu.
>
> **Vai trò của yfinance trong phân tích VN là lấy các chuỗi vĩ mô ngoại biên** làm đầu vào cho khung `global-macro`, `macro-analysis`, `commodity-analysis`: DXY, lợi suất TPCP Mỹ, vàng, dầu, đồng, USD/VND, USD/CNY, USD/JPY và rổ tiền tệ EM châu Á để so sánh chéo với VND. Xem mục [Chuỗi vĩ mô cho phân tích VN](#chuỗi-vĩ-mô-cho-phân-tích-vn) bên dưới.

## Quick Start

```bash
pip install yfinance pandas
```

```python
import yfinance as yf

# Apple daily bars for the past year
df = yf.download("AAPL", start="2025-01-01", end="2026-01-01", progress=False)
print(df.head())

# Tencent (HK-listed)
df = yf.download("0700.HK", start="2025-01-01", end="2026-01-01", progress=False)
print(df.head())
```

## Ticker Format Conversion

The project uses a unified ticker format. The DataLoader automatically converts to yfinance format:

| Project Format | yfinance Format | Market |
|---------------|----------------|--------|
| `AAPL.US` | `AAPL` | US stock |
| `MSFT.US` | `MSFT` | US stock |
| `700.HK` | `0700.HK` | HK stock |
| `9988.HK` | `9988.HK` | HK stock |
| `SPY.US` | `SPY` | US ETF |

**Rules:**
- US stocks: strip the `.US` suffix → use the raw ticker
- HK stocks: keep `.HK`, pad the number to 4 digits (`700` → `0700`)

## Supported Data Types

### 1. Historical OHLCV

```python
import yfinance as yf
import pandas as pd

# Single stock
df = yf.download("AAPL", start="2025-01-01", end="2026-01-01", progress=False)

# Batch download
df = yf.download(["AAPL", "MSFT", "GOOGL"], start="2025-01-01", end="2026-01-01", progress=False)

# Specific interval
df = yf.download("AAPL", start="2026-03-01", end="2026-03-30",
                 interval="1h", progress=False)  # 1m/5m/15m/30m/1h/1d/1wk/1mo
```

**Supported intervals:**
- Minute-level: `1m`, `2m`, `5m`, `15m`, `30m`, `60m`, `90m`
- Hourly: `1h`
- Daily and above: `1d`, `5d`, `1wk`, `1mo`, `3mo`

**Minute data limits:**
- `1m`: up to 7 days of history
- `2m/5m/15m/30m/60m/90m`: up to 60 days
- `1h`: up to 730 days
- `1d` and above: unlimited

### 2. Company Info

```python
ticker = yf.Ticker("AAPL")

info = ticker.info
print(f"Company: {info.get('longName')}")
print(f"Industry: {info.get('industry')}")
print(f"Market cap: {info.get('marketCap')}")
print(f"PE: {info.get('trailingPE')}")
print(f"EPS: {info.get('trailingEps')}")
print(f"Dividend yield: {info.get('dividendYield')}")
```

### 3. Financial Statements

```python
ticker = yf.Ticker("AAPL")

# Income statement (annual)
income = ticker.financials
# Income statement (quarterly)
income_q = ticker.quarterly_financials

# Balance sheet
balance = ticker.balance_sheet

# Cash flow statement
cashflow = ticker.cashflow

# Earnings data
earnings = ticker.earnings
```

### 4. Dividends and Splits

```python
ticker = yf.Ticker("AAPL")

# Dividend history
dividends = ticker.dividends

# Stock split history
splits = ticker.splits

# All corporate actions
actions = ticker.actions
```

### 5. Institutional Holdings

```python
ticker = yf.Ticker("AAPL")

# Institutional holders
holders = ticker.institutional_holders

# Major holders summary
major = ticker.major_holders

# Insider transactions
insider = ticker.insider_transactions
```

### 6. Indices and ETFs

```python
# Major indices
sp500 = yf.download("^GSPC", start="2025-01-01", end="2026-01-01", progress=False)  # S&P 500
nasdaq = yf.download("^IXIC", start="2025-01-01", end="2026-01-01", progress=False)  # NASDAQ
hsi = yf.download("^HSI", start="2025-01-01", end="2026-01-01", progress=False)      # Hang Seng Index

# ETFs
spy = yf.download("SPY", start="2025-01-01", end="2026-01-01", progress=False)
qqq = yf.download("QQQ", start="2025-01-01", end="2026-01-01", progress=False)
```

### 7. FX Rates

```python
# Currency pairs
usdcny = yf.download("CNY=X", start="2025-01-01", end="2026-01-01", progress=False)
usdhkd = yf.download("HKD=X", start="2025-01-01", end="2026-01-01", progress=False)
eurusd = yf.download("EURUSD=X", start="2025-01-01", end="2026-01-01", progress=False)
```

## Chuỗi vĩ mô cho phân tích VN

Đây là phần dùng nhiều nhất của skill này khi phân tích TTCK Việt Nam: lấy **biến ngoại biên** để đưa vào khung `global-macro` (truyền dẫn Fed → DXY → USD/VND → dòng vốn ngoại) và `commodity-analysis` (giá đầu vào nhập khẩu, giá nông sản xuất khẩu).

```python
import yfinance as yf

macro = yf.download(
    ["DX-Y.NYB", "^TNX", "GC=F", "BZ=F", "VND=X", "CNY=X"],
    start="2024-01-01", end="2026-01-01", progress=False,
)
```

| Ticker | Chuỗi | Vì sao quan trọng với VN |
|--------|------|------|
| `DX-Y.NYB` | Chỉ số USD (DXY) | Biến ngoại biên số 1 — quyết định áp lực USD/VND và dòng vốn ngoại HOSE |
| `^TNX` / `^TYX` / `^FVX` | Lợi suất TPCP Mỹ 10Y / 30Y / 5Y (đơn vị %) | Neo định giá toàn cầu; chênh lệch với lợi suất TPCP VN |
| `^VIX` | Chỉ số biến động Mỹ | Khẩu vị rủi ro toàn cầu — dẫn báo bán ròng khối ngoại |
| `VND=X` | USD/VND (tham khảo Yahoo) | **Chỉ dùng nhìn xu hướng.** Số chính thức phải lấy tỷ giá trung tâm SBV + tỷ giá niêm yết NHTM; Yahoo không có tỷ giá liên ngân hàng lẫn tỷ giá tự do |
| `CNY=X` | USD/CNY | CNY yếu ⇒ áp lực phá giá VND (cạnh tranh XK + đầu vào nhập từ TQ) |
| `JPY=X` | USD/JPY | Nợ ODA của VN nặng JPY — JPY mạnh làm phình nghĩa vụ trả nợ công |
| `THB=X`, `IDR=X`, `PHP=X`, `MYR=X`, `INR=X` | Rổ tiền tệ EM châu Á | **So sánh chéo với VND** — tách vấn đề nội tại khỏi chuyện của đồng USD |
| `GC=F` | Vàng tương lai COMEX | Neo cho giá vàng trong nước; chênh SJC – thế giới là chỉ báo cầu USD ngầm |
| `BZ=F` / `CL=F` | Dầu Brent / WTI | Đầu vào giá xăng dầu điều hành → CPI; biên của BSR, PLX, GAS |
| `NG=F` | Khí tự nhiên | Tham chiếu chi phí đầu vào urê (DPM, DCM) và nhiệt điện khí |
| `HG=F` | Đồng | Phong vũ biểu chu kỳ công nghiệp toàn cầu |
| `ZC=F`, `ZM=F` | Ngô, khô đậu tương | Giá thức ăn chăn nuôi → biên của DBC, BAF, HAG (độ trễ 1-2 quý) |
| `ZR=F` | Lúa gạo (rough rice, CBOT) | Tham chiếu xu hướng; **không thay được** giá gạo 5% tấm xuất khẩu VN (lấy từ VFA) |
| `KC=F` | Cà phê Arabica | ⚠️ VN sản xuất **Robusta**, hợp đồng Robusta (ICE Europe) **không có trên Yahoo** — dùng KC=F chỉ để nhìn xu hướng ngành, giá robusta phải crawl từ nguồn chuyên ngành |
| `VNM` | VanEck Vietnam ETF (niêm yết Mỹ) | Proxy khả dụng cho khẩu vị của nhà đầu tư nước ngoài với VN; **không thay VN-Index** — VN-Index lấy từ vnstock/DataPro |

**Không có trên Yahoo (đừng cố tra, phải crawl hoặc dùng nguồn khác):** giá thép HRC/quặng sắt nội địa, giá heo hơi, giá lúa/gạo xuất khẩu VN, giá cà phê robusta nhân xô, giá vàng SJC/nhẫn, lãi suất liên ngân hàng VND, lợi suất TPCP VN, tỷ giá tự do.

## Popular Ticker Reference

### US Stocks

| Ticker | Company |
|--------|---------|
| AAPL | Apple |
| MSFT | Microsoft |
| GOOGL | Alphabet (Google) |
| AMZN | Amazon |
| NVDA | NVIDIA |
| META | Meta Platforms |
| TSLA | Tesla |
| BRK-B | Berkshire Hathaway |

### HK Stocks

| Project Format | yfinance Format | Company |
|---------------|----------------|---------|
| 700.HK | 0700.HK | Tencent |
| 9988.HK | 9988.HK | Alibaba |
| 9618.HK | 9618.HK | JD.com |
| 3690.HK | 3690.HK | Meituan |
| 1810.HK | 1810.HK | Xiaomi |
| 2318.HK | 2318.HK | Ping An |

### Major Indices

| Ticker | Index |
|--------|-------|
| ^GSPC | S&P 500 |
| ^DJI | Dow Jones Industrial Average |
| ^IXIC | NASDAQ Composite |
| ^HSI | Hang Seng Index |
| ^N225 | Nikkei 225 |
| ^FTSE | FTSE 100 |

### Sector ETFs

| Ticker | Sector |
|--------|--------|
| XLK | Technology |
| XLF | Financials |
| XLE | Energy |
| XLV | Healthcare |
| XLY | Consumer Discretionary |
| XLP | Consumer Staples |
| XLI | Industrials |
| XLU | Utilities |

## Backtest Usage

### config.json Example

```json
{
  "source": "yfinance",
  "codes": ["AAPL.US", "MSFT.US"],
  "start_date": "2020-01-01",
  "end_date": "2026-03-30",
  "initial_cash": 1000000,
  "commission": 0.001,
  "extra_fields": null
}
```

### Cross-Market Auto Mode

```json
{
  "source": "auto",
  "codes": ["000001.SZ", "AAPL.US", "700.HK", "BTC-USDT"],
  "start_date": "2024-01-01",
  "end_date": "2026-03-30",
  "initial_cash": 1000000,
  "commission": 0.001,
  "extra_fields": null
}
```

`source: "auto"` routes automatically by ticker format: **VN equities (`.VN`) → datapro, fallback vnstock**; A-shares → tushare; HK/US stocks → yfinance; crypto → OKX. Xem `FALLBACK_CHAINS` trong `backtest/loaders/registry.py`.

### Ví dụ backtest có mã VN

```json
{
  "source": "auto",
  "codes": ["HPG.VN", "FPT.VN", "AAPL.US"],
  "start_date": "2024-01-01",
  "end_date": "2026-03-30",
  "initial_cash": 1000000000,
  "commission": 0.0015,
  "extra_fields": null
}
```

Mã `.VN` sẽ đi qua datapro/vnstock, không chạm yfinance. Lưu ý phí: giao dịch VN có phí môi giới ~0,15% mỗi chiều **cộng thuế TNCN 0,1% trên giá bán**, và engine VN áp biên độ trần/sàn theo giá tham chiếu — khác hẳn giả định của thị trường Mỹ.

## Notes

- **Free, no API key**: yfinance scrapes Yahoo Finance public data — no registration needed
- **Rate limits**: high-frequency requests may trigger temporary Yahoo bans — prefer batch downloads over per-ticker loops
- **Minute data range**: limited by Yahoo Finance (see table above)
- **HK tickers**: Yahoo Finance uses 4-digit numbers + `.HK`; pad with leading zeros where needed
- **Adjustment**: `auto_adjust=True` (default) returns forward-adjusted prices; the project loader uses `auto_adjust=False`
- **Timezone**: returned data includes timezone info; the DataLoader strips it automatically
- **extra_fields not supported**: yfinance via the backtest loader returns OHLCV only; PE/PB and other fundamentals require separate `yf.Ticker().info` calls
- **Comparison with Tushare**: Tushare covers deep A-share data (financials, fund flows, block trades, etc.); yfinance covers global markets but with less depth
- **Không dùng cho cổ phiếu VN**: dữ liệu mã VN trên Yahoo thiếu và không đáng tin — dùng DataPro (chính) / vnstock (dự phòng). Riêng dòng tiền khối ngoại chỉ có ở DataPro, và trường `foreign` tính bằng **nghìn VND**
- **`VND=X` không phải tỷ giá chính thức**: đây là tỷ giá tham khảo của Yahoo. Tỷ giá trung tâm và biên ±5% lấy từ SBV; tỷ giá giao dịch lấy từ niêm yết NHTM; tỷ giá tự do phải crawl. Đừng dùng `VND=X` để tính vị trí trong biên
- **Hàng hóa đặc thù VN không có trên Yahoo** (robusta, heo hơi, gạo XK, thép nội địa, vàng SJC) — xem bảng ở mục Chuỗi vĩ mô cho phân tích VN


## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)

1. **Không bịa/cook số liệu.** Mọi số tài chính phải có nguồn thật. Luôn **audit nhanh, cross-check tối thiểu 2 nguồn uy tín** (vd `cafef.vn`, `vietstock.vn`) — dùng **crawl4ai** cào số rồi đối chiếu; nếu nguồn lệch nhau thì nêu rõ, không chọn bừa.
2. **Nếu DataPro VÀ vnstock đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
