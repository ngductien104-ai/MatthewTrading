---
name: fundamental-filter
description: "Lọc cổ phiếu theo yếu tố cơ bản (ROE/biên LN/định giá) cho thị trường Việt Nam — TRUY VẤN TRỰC TIẾP chỉ số từ vnstock (bảng ratio, nguồn KBS) qua fundamental_fields, không cần tự tính. Hỗ trợ value/growth screen cho backtest."
category: flow
---
# Lọc cổ phiếu theo yếu tố cơ bản (Việt Nam)

## Mục đích

Lọc cổ phiếu bằng dữ liệu cơ bản (ROE, biên lợi nhuận, định giá...) để tạo tín hiệu value/growth cho backtest. Trọng tâm thị trường Việt Nam.

## Đặc thù dữ liệu Việt Nam — chỉ số có SẴN, không cần tự tính

| Việc cần | Nguồn | Cách lấy |
|------|------|------|
| **Chỉ số tài chính** (ROE, ROA, P/E, P/B, biên LN, EV/EBITDA, beta, tăng trưởng) | **vnstock — bảng `ratio` (nguồn KBS)** | `fundamental_fields: {"ratio": [...]}` — gắn sẵn point-in-time |
| BCTC thô (doanh thu, LN, vốn chủ, CFO) | **vnstock — `income/balancesheet/cashflow`** | `fundamental_fields` |
| Giá / khối lượng / khối ngoại | **DataPro** | cột `close` (nghìn đồng), `volume`... |

> ✅ vnstock **nguồn KBS** trả chỉ số SẠCH theo `item_id` (vd `roe`, `pe_ratio`, `pb_ratio`, `net_margin`, `ev_ebitda`, `beta`; ngân hàng có `net_interest_margin_nim`). KHÔNG cần tự tính như trước. *(Lưu ý: nguồn VCI cho `ratio()` trả layout kỳ lỗi — loader đã tự chuyển bảng `ratio` sang KBS.)*

## item_id chỉ số thường dùng (bảng `ratio`, KBS)

`roe`, `roa`, `roce` (return on capital employed) · `pe_ratio`, `pb_ratio`, `ps_ratio`, `ev_ebit`, `ev_ebitda` · `gross_margin`, `ebit_margin`, `net_margin` · `beta`, `dividend_yield` · tăng trưởng: `net_revenue`, `profit_before_tax`, `owners_equity` · thanh khoản: `cash_ratio`, `quick_ratio`. Ngân hàng còn có `net_interest_margin_nim`, `net_interest_income`.
*(Xem toàn bộ: `Finance(source="kbs", symbol="X").ratio(period="year")["item_id"]`.)*

## Cách dùng cho VN (config.json)

```json
{
  "source": "datapro",
  "codes": ["VCB.VN", "FPT.VN", "HPG.VN"],
  "start_date": "2023-01-01",
  "end_date": "2025-12-31",
  "fundamental_fields": {
    "ratio": ["roe", "pe_ratio", "pb_ratio", "net_margin"]
  },
  "initial_cash": 1000000000,
  "commission": 0.0015
}
```

Runner gắn mỗi kỳ vào nến ngày **chỉ sau ngày công bố ước tính** (point-in-time). Cột được tiền tố theo tên bảng:

| Field yêu cầu | Cột trong SignalEngine |
|-----------------|---------------------|
| `ratio.roe` | `ratio_roe` |
| `ratio.pe_ratio` | `ratio_pe_ratio` |
| `ratio.pb_ratio` | `ratio_pb_ratio` |
| `ratio.net_margin` | `ratio_net_margin` |

## Logic tín hiệu — query trực tiếp

```python
roe = row.get("ratio_roe")          # %, vd 23.59
pe  = row.get("ratio_pe_ratio")     # vd 15.91
pb  = row.get("ratio_pb_ratio")     # vd 3.73

passes = (
    roe is not None and roe >= roe_min          # vd ROE >= 8%
    and pe is not None and 0 < pe < pe_max
    and pb is not None and pb < pb_max
)
```

## Tham số

| Tham số | Mặc định | Mô tả |
|-----------|---------|------|
| roe_min | 8.0 | Sàn ROE (%) |
| pe_max | 20.0 | Trần P/E (>0) |
| pb_max | 3.0 | Trần P/B |
| margin_min | 0.0 | Sàn biên ròng (%) (`ratio_net_margin`) |

## Lưu ý

- **P/E, P/B từ bảng `ratio` là tại NGÀY BÁO CÁO** (giá cuối kỳ), không phải giá realtime — phù hợp lọc cơ bản PIT. Nếu cần định giá theo giá hiện tại, tính từ `close` (DataPro, **đơn vị nghìn đồng → ×1000**) × `issue_share` (`Company.overview().issue_share`).
- Chỉ số chất lượng/tăng trưởng (ROE, biên, growth) ổn định theo kỳ → dùng trực tiếp tốt nhất.
- Cột `fundamental_fields` bị NaN trước kỳ công bố đầu tiên trong cửa sổ backtest → `dropna`/bỏ qua, KHÔNG forward-fill (loader đã đảm bảo point-in-time).
- Ngân hàng: dùng `roe`, `net_interest_margin_nim`, `pb_ratio` (không dùng biên doanh thu kiểu phi tài chính).
- vnstock KBS trả ~4 kỳ năm gần nhất (bản community) → mã backtest dài thiếu chỉ số năm cũ.
- Danh mục N mã đạt lọc → mỗi mã trọng số 1/N.

## Phụ thuộc

```bash
pip install pandas numpy vnstock
```

## Quy ước tín hiệu

- `1/N` = được chọn long (N = số mã đạt lọc), `0` = không chọn.

> Ghi chú: `example_signal_engine.py` ưu tiên cột `ratio_*` (query trực tiếp), tự lùi về tính tay từ BCTC (`income_*`/`balancesheet_*`) hoặc cột pe/pb/roe (A-share tushare / US-HK yfinance) để tương thích đa thị trường.


## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)

1. **Không bịa/cook số liệu.** Mọi số tài chính phải có nguồn thật. Luôn **audit nhanh, cross-check tối thiểu 2 nguồn uy tín** (vd `cafef.vn`, `vietstock.vn`) — dùng **crawl4ai** cào số rồi đối chiếu; nếu nguồn lệch nhau thì nêu rõ, không chọn bừa.
2. **Nếu DataPro VÀ vnstock đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
