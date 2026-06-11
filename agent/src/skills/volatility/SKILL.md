---
name: volatility
description: Volatility strategy. Trades mean reversion based on percentile ranking of historical volatility (HV). Suitable for any OHLCV data.
category: strategy
---
# Volatility Strategy

## Purpose

Uses percentile ranking of historical volatility (HV) to capture volatility mean reversion: build positions in low-volatility regimes while waiting for volatility expansion, and exit or short in high-volatility regimes to capture contraction.

## Signal Logic

1. **Compute HV**: annualized standard deviation of returns over the past `hv_window` days
2. **Percentile ranking**: percentile position of HV within the past `lookback` days (0-100)
3. **Signal generation**:
   - Percentile < `low_pct` → go long (volatility is low, waiting for expansion)
   - Percentile > `high_pct` → exit / go short (volatility is high, waiting for contraction)
   - Middle region → keep the current position

## Key Implementation Details

- HV = `returns.rolling(hv_window).std() * sqrt(252)` (annualized)
- Percentile = `hv.rolling(lookback).rank(pct=True) * 100`
- For cryptocurrencies, use 365 instead of 252 as the annualization factor

## Parameters

| Parameter | Default | Description |
|------|--------|------|
| hv_window | 20 | Historical volatility calculation window |
| lookback | 120 | Lookback period for percentile ranking |
| low_pct | 20.0 | Low-volatility threshold (percentile) |
| high_pct | 80.0 | High-volatility threshold (percentile) |
| annualize | 252 | Annualization factor (252 for China A-shares, 365 for crypto) |

## Common Pitfalls

- Before the lookback window is filled, there is not enough data to compute percentiles, so the signal should be 0 (`fillna`)
- Volatility is not direction. Going long in low-volatility regimes does not guarantee price appreciation; it only means volatility expansion is statistically more likely
- Cryptocurrencies trade 7x24, so `annualize` should be set to 365

## Dependencies

```bash
pip install pandas numpy
```

## Signal Convention

- `1` = long (low-volatility regime), `-1` = short (high-volatility regime), `0` = stand aside


## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)

1. **Không bịa/cook số liệu.** Mọi số tài chính phải có nguồn thật. Luôn **audit nhanh, cross-check tối thiểu 2 nguồn uy tín** (vd `cafef.vn`, `vietstock.vn`) — dùng **crawl4ai** cào số rồi đối chiếu; nếu nguồn lệch nhau thì nêu rõ, không chọn bừa.
2. **Nếu DataPro VÀ vnstock đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
