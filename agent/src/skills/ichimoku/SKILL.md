---
name: ichimoku
description: Ichimoku Kinko Hyo five-line system signal engine. A standalone Japanese technical-analysis school that generates trading signals from Tenkan/Kijun crossovers, cloud position, and Chikou confirmation. Pure pandas implementation.
category: strategy
---
# Ichimoku Kinko Hyo

## Purpose

A standalone Japanese technical analysis framework that uses a five-line system and the cloud to provide a complete trend-evaluation structure:

| Line | Japanese | Calculation | Meaning |
|----|------|------|------|
| Conversion line | Tenkan-sen | (9H+9L)/2 | Short-term trend |
| Base line | Kijun-sen | (26H+26L)/2 | Medium-term trend |
| Leading Span A | Senkou Span A | (Tenkan+Kijun)/2 shifted forward by 26 | Upper cloud boundary |
| Leading Span B | Senkou Span B | (52H+52L)/2 shifted forward by 26 | Lower cloud boundary |
| Lagging Span | Chikou Span | Closing price shifted backward by 26 | Trend confirmation |

## Signal Logic

Signals are triggered only on TK crossover events, with three filters:
- **Strong buy**: bullish TK cross + price above the cloud + bullish cloud (A > B)
- **Strong sell**: bearish TK cross + price below the cloud + bearish cloud (A < B)
- All other cases → stand aside

Warm-up requires 78 candles (52+26).

## Parameters

| Parameter | Default | Description |
|------|--------|------|
| tenkan_period | 9 | Tenkan-sen period |
| kijun_period | 26 | Kijun-sen period |
| senkou_b_period | 52 | Senkou Span B period |
| displacement | 26 | Forward/backward shift period |

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
