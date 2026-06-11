---
name: candlestick
description: Candlestick pattern recognition engine, pure pandas vectorized implementation of 15 classic candlestick patterns (5 single-candle + 5 double-candle + 4 triple-candle + 1 trend confirmation), generating a composite signal from bullish/bearish pattern scores.
category: strategy
---
# Candlestick Pattern Recognition

## Purpose

Identifies 15 classic candlestick patterns and generates trading signals:

### Single-Candle Patterns (5)
| Pattern | Signal | Description |
|------|------|------|
| Hammer | Bullish | Long lower shadow with a small body at the top |
| Inverted Hammer | Bullish | Long upper shadow with a small body at the bottom |
| Shooting Star | Bearish | Long upper shadow with a small body at the bottom (appears after an uptrend) |
| Doji | Neutral | Open and close are nearly equal |
| Spinning Top | Neutral | Small body with roughly equal upper and lower shadows |

### Double-Candle Patterns (5)
| Pattern | Signal |
|------|------|
| Bullish Engulfing | Bullish |
| Bearish Engulfing | Bearish |
| Bullish Harami | Bullish |
| Bearish Harami | Bearish |
| Piercing Line | Bullish |
| Dark Cloud Cover | Bearish |

### Triple-Candle Patterns (4)
| Pattern | Signal |
|------|------|
| Morning Star | Bullish |
| Evening Star | Bearish |
| Three White Soldiers | Bullish |
| Three Black Crows | Bearish |

## Signal Logic

Bullish patterns score +1, bearish patterns score -1. Go long when the total score is > 0, go short when it is < 0, and stand aside when it equals 0.

## Parameters

| Parameter | Default | Description |
|------|--------|------|
| body_pct | 0.1 | Threshold for body-to-range ratio in a doji |
| shadow_ratio | 2.0 | Ratio of shadow length to body length |

## Dependencies

```bash
pip install pandas numpy requests
```

## Signal Convention

- `1` = long, `-1` = short, `0` = stand aside


## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)

1. **Không bịa/cook số liệu.** Mọi số tài chính phải có nguồn thật. Luôn **audit nhanh, cross-check tối thiểu 2 nguồn uy tín** (vd `cafef.vn`, `vietstock.vn`) — dùng **crawl4ai** cào số rồi đối chiếu; nếu nguồn lệch nhau thì nêu rõ, không chọn bừa.
2. **Nếu DataPro VÀ vnstock đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
