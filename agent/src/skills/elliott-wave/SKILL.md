---
name: elliott-wave
description: Elliott Wave Theory signal engine. Detects swing points through Zigzag, matches 5-wave impulse and 3-wave corrective structures, validates them with Fibonacci wave relationships, and generates trend-top / correction-complete signals. Pure in-house pandas implementation.
category: strategy
---
# Elliott Wave Theory

## Purpose

Classic wave theory based on the core assumption that markets move in fractal wave structures:

| Structure | Wave Count | Direction | Meaning |
|------|------|------|------|
| Impulse wave | 5 waves (1-2-3-4-5) | Trend-following | Main trend direction |
| Corrective wave | 3 waves (A-B-C) | Counter-trend | Pullback correction |

## Core Rules

### Three Iron Rules for Impulse Waves
1. Wave 2 cannot retrace beyond the start of wave 1
2. Wave 3 cannot be the shortest impulse wave
3. Wave 4 cannot enter the price territory of wave 1

### Fibonacci Relationships Between Waves
- Wave 2 retraces 0.5-0.618 of wave 1
- Wave 3 = wave 1 × 1.618 (most common)
- Wave 4 retraces 0.382 of wave 3
- Wave 5 ≈ the length of wave 1

## Signal Logic

- **5-wave advance completed** → sell (trend top)
- **ABC pullback completed** → buy (correction finished)
- **Wave 3 in progress** → stay with the trend (no reversal signal is generated)

## Parameters

| Parameter | Default | Description |
|------|--------|------|
| swing_window | 10 | Rolling window for swing-point detection |
| fib_tolerance | 0.15 | Tolerance for Fibonacci ratios |
| min_wave_bars | 5 | Minimum number of candles per wave |

## Notes

Wave theory is highly subjective, and automatic counting can yield multiple interpretations. This implementation uses a "simplest effective single interpretation" strategy and would rather miss signals than misclassify them.

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
