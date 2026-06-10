---
name: fundamental-filter
description: "Lọc cổ phiếu theo yếu tố cơ bản (ROE/biên LN/tăng trưởng/P-B) cho thị trường Việt Nam — dùng BCTC vnstock qua fundamental_fields + giá DataPro, tính tỷ số trong signal engine. Hỗ trợ value/growth screen cho backtest."
category: flow
---
# Lọc cổ phiếu theo yếu tố cơ bản (Việt Nam)

## Mục đích

Lọc cổ phiếu bằng dữ liệu cơ bản (ROE, biên lợi nhuận, tăng trưởng, P/B...) để tạo tín hiệu value/growth cho backtest. Trọng tâm thị trường Việt Nam.

## Đặc thù dữ liệu Việt Nam

| Việc cần | Nguồn | Cách lấy |
|------|------|------|
| BCTC (doanh thu, LN, vốn chủ, CFO) | **vnstock** | `fundamental_fields` trong config.json (an toàn point-in-time) |
| Giá / vốn hoá | **DataPro** | cột `close` (nghìn đồng) × `issue_share` |
| Số CP lưu hành | **vnstock** | `Company.overview().issue_share` — truyền vào engine, KHÔNG suy từ EPS |

> ⚠️ Khác Tushare/A-share: DataPro **KHÔNG** cấp sẵn `pe/pb/roe` theo ngày. Với VN phải **tự tính tỷ số** trong signal engine từ BCTC + giá. Endpoint `ratio()` của vnstock community không ổn định → đừng lấy trực tiếp.

## Logic tín hiệu

### Bộ lọc giá trị (mặc định) — tính từ BCTC, KHÔNG cần số CP
1. LN sau thuế > 0 (loại DN lỗ)
2. Doanh thu thuần > 0
3. **ROE = LN sau thuế / Vốn chủ × 100 > roe_min**
4. (tuỳ chọn) Biên ròng = LN sau thuế / Doanh thu thuần > margin_min
5. Đủ điều kiện → long (1/N), không thì flat (0)

### Bộ lọc định giá (tuỳ chọn) — cần `issue_share`
6. **P/B = (close × 1000 × issue_share) / Vốn chủ < pb_max**
   *(close DataPro tính bằng NGHÌN đồng nên ×1000 để ra đồng, khớp đơn vị BCTC)*
7. **P/E = (close × 1000 × issue_share) / LN sau thuế (TTM) < pe_max** và > 0

## Cách dùng cho VN (config.json)

```json
{
  "source": "datapro",
  "codes": ["VCB.VN", "FPT.VN", "HPG.VN"],
  "start_date": "2023-01-01",
  "end_date": "2025-12-31",
  "fundamental_fields": {
    "income": ["net_sales", "net_profit_loss_after_tax"],
    "balancesheet": ["owners_equity"]
  },
  "initial_cash": 1000000000,
  "commission": 0.0015
}
```

Runner sẽ truy vấn các bảng BCTC qua `VNStockFundamentalProvider` và gắn mỗi kỳ vào nến ngày **chỉ sau ngày công bố ước tính** (point-in-time). Cột BCTC được tiền tố theo tên bảng:

| Field yêu cầu | Cột trong SignalEngine |
|-----------------|---------------------|
| `income.net_sales` | `income_net_sales` |
| `income.net_profit_loss_after_tax` | `income_net_profit_loss_after_tax` |
| `balancesheet.owners_equity` | `balancesheet_owners_equity` |

Bộ lọc chất lượng cơ bản tiêu biểu:

```python
revenue = row.get("income_net_sales")
profit = row.get("income_net_profit_loss_after_tax")
equity = row.get("balancesheet_owners_equity")

passes = (
    revenue is not None and revenue > 0
    and profit is not None and profit > 0
    and equity is not None and equity > 0
    and (profit / equity * 100) >= 8.0   # ROE >= 8%
)
```

### Thêm bộ lọc P/B (cần issue_share)

```python
# shares: số CP lưu hành (issue_share) truyền vào engine theo từng mã
market_cap = row["close"] * 1000 * shares          # close (nghìn đồng) → đồng
pb = market_cap / equity                            # equity (đồng) từ BCTC
passes_pb = 0 < pb < pb_max
```

## Tham số

| Tham số | Mặc định | Mô tả |
|-----------|---------|------|
| roe_min | 8.0 | Sàn ROE (%), loại DN sinh lời thấp |
| pb_max | 3.0 | Trần P/B |
| pe_max | 20.0 | Trần P/E (loại định giá cao) |
| margin_min | 0.0 | Sàn biên ròng (%) (tuỳ chọn) |
| shares_map | {} | `{mã: issue_share}` — cần cho lọc P/B, P/E |

## Lỗi thường gặp

- Cột `fundamental_fields` bị NaN trước khi BCTC đầu tiên được công bố trong cửa sổ backtest → phải `dropna`/bỏ qua, KHÔNG forward-fill thủ công (loader đã đảm bảo point-in-time).
- **Đơn vị giá DataPro là NGHÌN đồng** (vd 61.7 = 61.700đ); BCTC vnstock là **đồng**. Tính vốn hoá phải ×1000 — đây là lỗi sai đơn vị phổ biến nhất.
- ROE tự tính = LN/Vốn chủ ×100; đừng kỳ vọng có cột `roe` sẵn như Tushare.
- `issue_share` thay đổi khi pha loãng (tăng vốn, cổ tức cổ phiếu) — lý tưởng là cập nhật theo kỳ; nếu dùng hằng số, nêu rõ giả định.
- Ngân hàng: `net_sales` thường rỗng (mẫu BCTC riêng) → lọc bằng ROE/LN sau thuế, không lọc bằng doanh thu/biên.
- Bản community vnstock chỉ ~4 kỳ năm gần nhất → mã backtest dài sẽ thiếu BCTC năm cũ.
- Danh mục N mã đạt lọc → mỗi mã trọng số 1/N.

## Phụ thuộc

```bash
pip install pandas numpy vnstock
```

## Quy ước tín hiệu

- `1/N` = được chọn long (N = số mã đạt lọc), `0` = không chọn.

> Ghi chú: bộ khung A-share (tushare `extra_fields`/`fundamental_fields`) và HK/US (yfinance `Ticker.info`) vẫn còn trong `example_signal_engine.py` để tương thích đa thị trường; với VN dùng nhánh BCTC vnstock ở trên.
