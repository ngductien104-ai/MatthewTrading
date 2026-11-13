---
name: fundamental-filter
description: "Lọc cổ phiếu theo yếu tố cơ bản (ROE/biên LN/định giá) cho thị trường Việt Nam — lấy chỉ số từ VNDIRECT MCP (FINFO_API__get_ratios / get_latest_ratios), lọc cắt ngang hoặc ghi CSV point-in-time cho backtest. Hỗ trợ value/growth screen."
category: flow
---
# Lọc cổ phiếu theo yếu tố cơ bản (Việt Nam)

## Mục đích

Lọc cổ phiếu bằng dữ liệu cơ bản (ROE, biên lợi nhuận, định giá...) để tạo tín hiệu value/growth. Trọng tâm thị trường Việt Nam.

## Nguồn dữ liệu Việt Nam (từ 13/11/2026)

| Việc cần | Nguồn | Cách lấy |
|------|------|------|
| **Chỉ số tài chính mới nhất** (ROE, P/E, P/B, biên, tăng trưởng) | **VNDIRECT MCP** | `FINFO_API__get_latest_ratios` |
| Chỉ số lịch sử (≤5 năm, theo kỳ) | **VNDIRECT MCP** | `FINFO_API__get_ratios` |
| Vũ trụ lọc theo ngành / rổ | **VNDIRECT** (snapshot) | `vndata.reference.classification()` / `symbols_by_group("VN30")` |
| Giá / khối lượng / khối ngoại | **DataPro** | cột `close` (nghìn đồng), `volume`... |

Mã chỉ tiêu hay dùng: định giá `PRICE_TO_EARNINGS`, `PRICE_TO_BOOK`,
`PRICE_TO_SALES`, `MARKETCAP`, `DIVIDEND_YIELD`; sinh lời `ROAE_TR_AVG4Q`,
`ROAA_TR_AVG4Q`, `ROIC_TR_AVG4Q`, `GROSS_MARGIN_TR`, `NET_MARGIN_TR`; tăng trưởng
`NET_SALES_TR_GRYOY`, `NET_PROFIT_TR_GRYOY`, `EPS_TR_GRYOY`.

> ⚠️ **Đơn vị:** VNDIRECT trả tỷ lệ dạng **phân số** (ROAE 0,195 = 19,5%). Lọc
> `ROE >= 8` phải so với `0.08`, hoặc nhân 100 trước — screen trả rỗng bất
> thường thì kiểm đơn vị đầu tiên. Thiếu số giữ là thiếu, **không `fillna(0)`**.

## Lọc cắt ngang (hôm nay)

```text
get_latest_ratios(
    filter="ratioCode:ROAE_TR_AVG4Q,PRICE_TO_EARNINGS,PRICE_TO_BOOK,NET_MARGIN_TR",
    where="code:VCB,FPT,HPG,...",          # vũ trụ từ snapshot VN30 / ICB
    order="reportDate")
```

Pivot `code × ratioCode` rồi áp ngưỡng ở bảng Tham số.

## Backtest (point-in-time)

Runner **không** còn gắn `fundamental_fields` cho mã `.VN` (Python không gọi được
VNDIRECT — runner báo lỗi rõ thay vì chạy chiến lược chỉ-giá). Quy trình:

1. Kéo `get_ratios(q="code:<mã>~ratioCode:<...>~reportDate:gte:<đầu kỳ>", size=300)` qua MCP.
2. Ghi CSV `code, reportDate, ratioCode, value`.
3. Signal engine đọc CSV, gắn mỗi kỳ vào nến **sau** `reportDate + 45 ngày` (quý) /
   `+ 90 ngày` (năm) — `vndata.fundamental.DISCLOSURE_LAG_DAYS` — không forward-fill
   trước kỳ công bố đầu tiên.

## Logic tín hiệu

```python
roe = row.get("ratio_roe")          # % sau khi đã nhân 100, vd 19.5
pe  = row.get("ratio_pe")
pb  = row.get("ratio_pb")

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

## Quy ước tín hiệu

- `1/N` = được chọn long (N = số mã đạt lọc), `0` = không chọn.

> Ghi chú: `example_signal_engine.py` ưu tiên cột `ratio_*` (VN: dựng từ CSV chỉ số VNDIRECT), tự lùi về tính tay từ BCTC (`income_*`/`balancesheet_*`) hoặc cột pe/pb/roe (A-share tushare / US-HK yfinance) để tương thích đa thị trường.

## Lưu ý

- **P/E, P/B của VNDIRECT có hai loại `reportDate`**: chỉ số thị trường cập nhật
  **theo ngày giao dịch**; chỉ số BCTC theo **ngày cuối quý**. Lọc PIT thì dùng
  bản ghi có `reportDate` ≤ ngày quyết định.
- Ngân hàng: dùng `ROAE_TR_AVG4Q`, `PRICE_TO_BOOK`, `NET_INTEREST_MARGIN_TR_AVG5Q`,
  `BAD_LOANS_RATIO_AQ` — không dùng biên doanh thu kiểu phi tài chính.
- Danh mục N mã đạt lọc → mỗi mã trọng số 1/N.

## Phụ thuộc

```bash
pip install pandas numpy
```


## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)

1. **Không bịa/cook số liệu.** Mọi số tài chính phải có nguồn thật. Luôn **audit nhanh, cross-check tối thiểu 2 nguồn uy tín** (vd `cafef.vn`, `vietstock.vn`) — dùng **crawl4ai** cào số rồi đối chiếu; nếu nguồn lệch nhau thì nêu rõ, không chọn bừa.
2. **Nếu DataPro VÀ VNDIRECT MCP đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
