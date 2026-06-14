---
name: volatility
description: "Chiến lược biến động (volatility) cho TTCK VN. Giao dịch hồi quy về trung bình dựa trên xếp hạng phân vị của biến động lịch sử (HV). Dùng được cho mọi dữ liệu OHLCV (cổ phiếu .VN, chỉ số VN-Index/VN30)."
category: strategy
---
# Chiến lược biến động (Việt Nam)

## Mục đích

Dùng xếp hạng phân vị của biến động lịch sử (HV) để bắt hồi quy về trung bình của biến động: mở vị thế trong vùng biến động thấp và chờ biến động mở rộng, thoát hoặc đảo chiều trong vùng biến động cao để bắt pha co lại.

## Logic tín hiệu

1. **Tính HV**: độ lệch chuẩn của lợi suất theo năm trong `hv_window` phiên gần nhất
2. **Xếp hạng phân vị**: vị trí phân vị của HV trong `lookback` phiên gần nhất (0–100)
3. **Sinh tín hiệu**:
   - Phân vị < `low_pct` → mở mua (biến động thấp, chờ mở rộng)
   - Phân vị > `high_pct` → thoát / đảo chiều (biến động cao, chờ co lại)
   - Vùng giữa → giữ nguyên vị thế hiện tại

## Chi tiết triển khai then chốt

- HV = `returns.rolling(hv_window).std() * sqrt(252)` (quy năm)
- Phân vị = `hv.rolling(lookback).rank(pct=True) * 100`
- Hệ số quy năm: **252** phiên cho cổ phiếu/chỉ số VN

## Tham số

| Tham số | Mặc định | Mô tả |
|------|--------|------|
| hv_window | 20 | Cửa sổ tính biến động lịch sử |
| lookback | 120 | Kỳ nhìn lại để xếp hạng phân vị |
| low_pct | 20.0 | Ngưỡng biến động thấp (phân vị) |
| high_pct | 80.0 | Ngưỡng biến động cao (phân vị) |
| annualize | 252 | Hệ số quy năm (252 cho cổ phiếu VN) |

## Lỗi thường gặp

- Trước khi cửa sổ `lookback` được lấp đầy, chưa đủ dữ liệu để tính phân vị → tín hiệu nên đặt 0 (`fillna`)
- Biến động KHÔNG phải hướng giá. Mua trong vùng biến động thấp không bảo đảm giá tăng; chỉ nghĩa là biến động có xác suất mở rộng cao hơn về mặt thống kê
- **Lưu ý TTCK VN**: biên độ trần/sàn (HOSE ±7%, HNX ±10%, UPCoM ±15%) chặn đuôi biến động — HV của mã VN bị "ép trần" trong các phiên kịch biên, nên phân vị biến động có thể bị nén so với thị trường không có biên độ. Cẩn trọng khi diễn giải mã hay nằm sàn/trần.

## Phụ thuộc

```bash
pip install pandas numpy
```

## Quy ước tín hiệu

- `1` = mua (vùng biến động thấp), `-1` = đảo chiều/thoát (vùng biến động cao), `0` = đứng ngoài


## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)

1. **Không bịa/cook số liệu.** Mọi số tài chính phải có nguồn thật. Luôn **audit nhanh, cross-check tối thiểu 2 nguồn uy tín** (vd `cafef.vn`, `vietstock.vn`) — dùng **crawl4ai** cào số rồi đối chiếu; nếu nguồn lệch nhau thì nêu rõ, không chọn bừa.
2. **Nếu DataPro VÀ vnstock đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
