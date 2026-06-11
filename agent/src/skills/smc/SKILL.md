---
name: smc
description: Smart Money Concepts (ICT) signal engine. Uses the smartmoneyconcepts library to implement institutional-trading-school analysis of BOS, ChoCH, FVG, and order blocks (OB).
category: strategy
---
# Smart Money Concepts

## Purpose

The modern institutional trading school (ICT / Inner Circle Trader), built around the core idea of tracking the behavior of "smart money" (institutional capital):

| Concept | English | Meaning |
|------|------|------|
| Break of structure | BOS (Break of Structure) | Trend continuation signal |
| Change of character | ChoCH (Change of Character) | Trend reversal signal |
| Fair value gap | FVG (Fair Value Gap) | Price refill target |
| Order blocks | Order Blocks | Institutional order concentration zones |
| Liquidity | Liquidity | Stop-hunt target zones |

## Signal Logic

Direction from ChoCH + confirmation from BOS + filtering by FVG:
- **Long**: bullish ChoCH/BOS + bullish FVG exists
- **Short**: bearish ChoCH/BOS + bearish FVG exists
- **Stand aside**: no structural signal or conflicting directions

## Dependencies

```bash
pip install smartmoneyconcepts pandas numpy requests
```

## Parameters

| Parameter | Default | Description |
|------|--------|------|
| swing_length | 10 | Window for swing high/low detection |
| close_break | True | Whether BOS/ChoCH requires a closing-price break |

## Signal Convention

- `1` = long, `-1` = short, `0` = stand aside


## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)

1. **Không bịa/cook số liệu.** Mọi số tài chính phải có nguồn thật. Luôn **audit nhanh, cross-check tối thiểu 2 nguồn uy tín** (vd `cafef.vn`, `vietstock.vn`) — dùng **crawl4ai** cào số rồi đối chiếu; nếu nguồn lệch nhau thì nêu rõ, không chọn bừa.
2. **Nếu DataPro VÀ vnstock đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
