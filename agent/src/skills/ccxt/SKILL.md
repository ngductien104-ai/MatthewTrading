---
name: ccxt
category: data-source
description: CCXT unified crypto exchange library (100+ exchanges). Free public market data. Fallback when OKX is unavailable.
---

## Overview

CCXT is a unified cryptocurrency exchange trading library supporting 100+ exchanges including Binance, Bybit, OKX, Coinbase, Kraken, and more. Public market data (OHLCV, tickers, order books) requires no API key.

- GitHub: https://github.com/ccxt/ccxt (35k+ stars)
- Install: `pip install ccxt`

## Quick Start

```python
import ccxt

exchange = ccxt.binance({"enableRateLimit": True})

# Fetch daily OHLCV
ohlcv = exchange.fetch_ohlcv("BTC/USDT", "1d", limit=100)
# Returns: [[timestamp, open, high, low, close, volume], ...]

# Fetch ticker
ticker = exchange.fetch_ticker("ETH/USDT")
print(f"ETH price: {ticker['last']}")
```

## Key Methods

| Method | Description | Returns |
|--------|-------------|---------|
| `fetch_ohlcv(symbol, timeframe, since, limit)` | Historical candles | `[[ts, o, h, l, c, v], ...]` |
| `fetch_ticker(symbol)` | Latest quote | `{last, bid, ask, volume, ...}` |
| `fetch_tickers(symbols)` | Batch quotes | `{symbol: ticker}` |
| `fetch_order_book(symbol, limit)` | Order book | `{bids, asks, timestamp}` |
| `fetch_trades(symbol, since, limit)` | Recent trades | `[{price, amount, side, timestamp}, ...]` |

## Timeframes

`1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `6h`, `12h`, `1d`, `1w`, `1M`

Note: not all exchanges support all timeframes. Use `exchange.timeframes` to check.

## Symbol Format

CCXT uses slash format: `BTC/USDT`, `ETH/BTC`, `SOL/USDT`

The project's DataLoader automatically converts `BTC-USDT` (hyphen) to `BTC/USDT` (slash).

## Exchange Selection

Set via environment variable: `CCXT_EXCHANGE=binance` (default)

Popular exchanges: `binance`, `bybit`, `okx`, `coinbase`, `kraken`, `bitget`, `gate`

## Built-in Loader

The project has a built-in CCXT DataLoader at `backtest/loaders/ccxt_loader.py`. It serves as a fallback when the OKX loader is unavailable.

## Pagination

For long history, CCXT paginates via the `since` parameter (millisecond timestamp). The built-in loader handles this automatically (up to 200 pages).


## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)

1. **Không bịa/cook số liệu.** Mọi số tài chính phải có nguồn thật. Luôn **audit nhanh, cross-check tối thiểu 2 nguồn uy tín** (vd `cafef.vn`, `vietstock.vn`) — dùng **crawl4ai** cào số rồi đối chiếu; nếu nguồn lệch nhau thì nêu rõ, không chọn bừa.
2. **Nếu DataPro VÀ vnstock đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
