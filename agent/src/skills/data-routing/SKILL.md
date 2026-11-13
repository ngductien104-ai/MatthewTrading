---
name: data-routing
category: data-source
description: Data source selection decision tree. Load this skill BEFORE any backtest or data-fetching task to choose the correct source. For Vietnam there is exactly one correct source per data class — DataPro or VNDIRECT MCP — and this skill names it, with the exact tool.
---

## Vietnam — nguồn sự thật (BẮT BUỘC)

**Từ 13/11/2026 dự án KHÔNG dùng vnstock** (cả `vnstock_data` / `vnstock_ta` /
`vnstock_news` lẫn bản free) — gói đã huỷ, xác thực ngừng từ 10/11/2026. Không
`import vnstock*` ở bất kỳ đâu; MCP `vnstock` và các tool `vn_*` đã gỡ.

Còn **hai nguồn sự thật, không chồng lấn**:

| Nguồn | Gọi bằng | Ai gọi được |
|---|---|---|
| **DataPro** (app desktop `localhost:6789`) | Python `vndata.price` / `vndata.reference` / `vndata.ta`, hoặc MCP `datapro` (`get_daily`, `get_minute`, `get_tick`, `get_symbols`) | Python + Claude |
| **VNDIRECT MCP** (connector claude.ai, OAuth) | tool `FINFO_API__*` của connector "VNDIRECT MCP" | **Chỉ Claude / subagent** — Python KHÔNG gọi được |

Trong Claude Code tên đầy đủ có tiền tố ID connector, ví dụ
`mcp__43ec7302-c0f0-4d07-9fc8-71bd8ef0a93f__FINFO_API__get_ratios`. Tìm bằng
`ToolSearch("FINFO_API")` nếu tool chưa nạp. Kiểm cổng còn sống: tool `health`.

### Bảng định tuyến

| Loại dữ liệu | Nguồn | Gọi |
|---|---|---|
| OHLCV, KL, GTGD, giá tham chiếu/trần/sàn, chuỗi lịch sử | **DataPro** | `vndata.price.ohlcv()` · MCP `datapro.get_daily` |
| Khối ngoại / tự doanh theo mã, chuỗi ngày | **DataPro** | `vndata.price.foreign_flow()` / `proprietary_flow()` |
| Thoả thuận, chủ động mua/bán, chỉ số, phái sinh, ETF | **DataPro** | `vndata.price.ohlcv()` |
| Danh sách mã, sàn, loại CK, SLCP lưu hành | **DataPro** | `vndata.reference.symbols()` / `equities()` / `etfs()` |
| Chỉ báo kỹ thuật | **tự tính trên giá DataPro** | `vndata.ta.indicator()` (RSI/MACD/ATR/BB/OBV… Wilder chuẩn) |
| Tin tức (tiêu đề + link) | **RSS nhà xuất bản** | `vndata.news.rss()` → thân bài: `read_url` / crawl4ai |
| Khối ngoại **tổng sàn chính thức** (VNINDEX/HNX/UPCOM), rổ, room NN | **VNDIRECT** | `FINFO_API__get_foreign_trading` |
| Top mua ròng NN trong phiên | **VNDIRECT** | `FINFO_API__get_positive_foreign_net_value` |
| Độ rộng sàn (tăng/giảm/trần/sàn), GTGD khớp + thoả thuận theo sàn | **VNDIRECT** | `FINFO_API__get_vnmarket_prices` |
| Mã dẫn dắt VN-Index | **VNDIRECT** | `FINFO_API__get_vnindex_leaderlarger` |
| Thành phần rổ (VN30…), xếp hạng trong rổ | **VNDIRECT** | `FINFO_API__get_top_stocks(index=…)` · Python: snapshot `vndata.reference.symbols_by_group()` |
| Phân ngành ICB (cấp 1–4) | **VNDIRECT** | `FINFO_API__get_industry_classification` · Python: snapshot `vndata.reference.classification()` |
| P/E, P/B, P/S, vốn hoá, beta, cổ tức/thị giá, BVPS, sở hữu NN/nhà nước/nội bộ, free-float | **VNDIRECT** | `FINFO_API__get_latest_ratios` (mới nhất) · `FINFO_API__get_ratios` (lịch sử ≤5 năm) |
| Chỉ số cơ bản theo kỳ: tăng trưởng DT/LN/EPS/CFO (QoQ, YoY, 4Q, 2–3 năm), biên gộp/EBITDA, ROAE/ROAA/ROIC, vòng quay, DSO/DIO/DPO, nợ vay/EBITDA, ICR, payout | **VNDIRECT** | `FINFO_API__get_ratios(q="code:X~reportDate:YYYY-MM-DD")` |
| Đặc thù ngân hàng: NIM, nợ xấu, nợ quá hạn, bao phủ nợ xấu, LDR, chi phí tín dụng, cho vay/tiền gửi trên TS | **VNDIRECT** | `FINFO_API__get_ratios` (xem mã ở dưới) |
| Sự kiện DN (cổ tức tiền/CP, niêm yết bổ sung, ĐHĐCĐ, GDKHQ) | **VNDIRECT** | `FINFO_API__get_company_events` |
| Ban lãnh đạo | **VNDIRECT** | `FINFO_API__get_company_personnel` |
| Quỹ mở: hiệu suất NAV, phân bổ ngành / cổ phiếu / tài sản | **VNDIRECT** | `FINFO_API__get_fund_ratios` · `FINFO_API__get_fund_allocation` (không áp dụng ETF) |
| Hợp đồng phái sinh còn hiệu lực + giá | **VNDIRECT** | `FINFO_API__get_derivatives` · `get_derivative_prices` |
| Hàng hoá (vàng, Brent, cao su, đường, đồng, quặng sắt, HRC) | **VNDIRECT** | `FINFO_API__get_change_prices` (kiểm chéo Yahoo, xem bẫy) |
| Lịch giao dịch / phiên gần nhất | **VNDIRECT** | `FINFO_API__get_trading_calendar` · `get_latest_trading_calendar` |
| Bản đồ ngành thị trường | **VNDIRECT** | `FINFO_API__get_industry_map` |
| Tỷ giá, DXY | **Yahoo** (`yfinance`, venv dự án) | `USDVND=X`, `DX-Y.NYB` — DataPro trả 0 dòng |
| **BCTC từng dòng (KQKD/CĐKT/LCTT) + thuyết minh** | **BCTC GỐC (PDF)** | `agent/scripts/evidence_pack.py <MÃ>` — **không nguồn API nào có** |
| Vĩ mô VN (CPI, GDP, tín dụng, lãi suất điều hành) | **Cơ quan công bố gốc** | GSO / NHNN / BTC, cào bằng crawl4ai, ghi nguồn |

> **VNDIRECT chỉ có CHỈ SỐ và số tổng hợp**, không có BCTC từng dòng. Doanh thu
> thuần, LN ròng, EBIT, tổng TS, VCSH, tồn kho… có dạng `*_QR` (quý), `*_YD` (luỹ
> kế năm), `*_TR` (4 quý), `*_AQ` (cuối kỳ). Cần dòng chi tiết (giá vốn từng
> mảng, thu nhập khác, lãi dự thu, nợ nhóm 2–5) → **PDF gốc** theo Phase 0.

### Cú pháp `get_ratios` / `get_latest_ratios`

```text
get_ratios(q="code:HPG~reportDate:2026-09-30", size=300, fields="ratioCode,itemName,value")
get_ratios(q="code:VCB,TCB~ratioCode:BAD_LOANS_RATIO_AQ,NET_INTEREST_MARGIN_TR_AVG5Q", sort="reportDate:desc", size=50)
get_latest_ratios(filter="ratioCode:PRICE_TO_BOOK,PRICE_TO_EARNINGS", where="code:VCB,TCB", order="reportDate")
```

- Toán tử: `gt gte lt lte` (`reportDate:gte:2025-01-01`), nối điều kiện bằng `~`, liệt kê bằng `,`.
- `reportDate` của chỉ số thị trường là **ngày giao dịch**; của chỉ số cơ bản là **ngày cuối quý** (`2026-09-30`).
- Một mã một kỳ ~180–240 dòng → dùng `size=300` hoặc lọc `ratioCode`.

Mã hay dùng (đã kiểm trên HPG, VCB ngày 13/11/2026):

| Nhóm | `ratioCode` |
|---|---|
| Định giá | `PRICE_TO_EARNINGS`, `PRICE_TO_BOOK`, `PRICE_TO_SALES`, `MARKETCAP`, `BVPS_CR`, `EPS_TR`, `DIVIDEND_YIELD`, `BETA`, bình quân lịch sử `PRICE_TO_EARNINGS_AVG_CR_{1M,3M,6M,1Y,3Y,5Y}` / `PRICE_TO_BOOK_AVG_CR_*` |
| Sở hữu | `FOREIGN_OWNERSHIP`, `STATE_OWNERSHIP`, `TOTAL_INTERNAL_OWNERSHIP`, `FREEFLOAT`, `OUTSTANDING_SHARES`, `LISTED_SHARES` |
| Sinh lời | `ROAE_TR_AVG4Q`, `ROAA_TR_AVG4Q`, `ROIC_TR_AVG4Q`, `GROSS_MARGIN_{QR,TR,YD}`, `OPERATING_EBITDA_MARGIN_{QR,TR}`, `NET_MARGIN_{QR,TR,YD}` |
| Tăng trưởng | `NET_SALES_{QR_GRYOY,QR_GRQOQ,TR_GRYOY,TR_GR3YR}`, `NET_PROFIT_*`, `EPS_*`, `CFO_*`, `GROSS_PROFIT_*`, `OPERATING_EBIT_*` |
| Quy mô | `NET_SALES_{QR,YD,TR}`, `NET_PROFIT_{QR,YD,TR}`, `CFO_YD`, `TOTAL_ASSETS_AQ`, `OWNERS_EQUITY_AQ`, `INVENTORY_AQ`, `CURRENT_ASSETS_AQ` |
| Vốn lưu động | `DSO_TR_AVG5Q`, `DIO_QR_AVG2Q`, `DPO_QR_AVG2Q`, `CASH_CONVERSION_CYCLE_TR_AVG5Q`, `INVENTORY_TURNOVER_TR_AVG5Q` |
| Đòn bẩy | `DEBT_EBITDA`, `INTEREST_COVERAGE_TR`, `EQUITY_TO_ASSET_AQ`, `NET_CASH_TO_EQUITY_AQ`, `TOTAL_DEBT_AQ_GRYOY` |
| Ngân hàng | `NET_INTEREST_MARGIN_TR_AVG5Q`, `BAD_LOANS_RATIO_AQ`, `OVERDUE_LOANS_RATIO_AQ`, `PROVISION_BAD_LOANS_AQ` (bao phủ), `LOANS_TO_DEPOSIT_AQ`, `DOUBTFUL_EXPENSES_TO_LOANS_TR_AVG5Q` (chi phí TD), `CUSTOMER_LOANS_AQ_GRYOY`, `INTEREST_INCOME_RATIO_TR`, `NON_INTEREST_INCOME_RATIO_TR` |
| Kỹ thuật/dòng tiền | `DAILY_JDK_RS_CR`, `DAILY_JDK_RS_MOMENTUM_CR`, `NMVALUE_AVG_CR_20D`, `FOREIGN_BUY_VALUE_CR_WTD` |

**Ngân hàng KHÔNG có trong VNDIRECT:** CASA, CAR, cơ cấu nợ nhóm 2–5, YOEA/COF
tách riêng → đọc **BCTC gốc / báo cáo Basel III / IR** của ngân hàng.

### ⚠️ Bẫy VNDIRECT MCP (đo 13/11/2026)

| Bẫy | Thực tế | Xử lý |
|---|---|---|
| Tỷ lệ | **fraction** (ROAE 0.195 = 19,5%; NPL 0.00706 = 0,71%) | Nhân 100 khi trình bày |
| `EBITDA_TR` | HPG **−174.797 tỷ** (vô lý) trong khi `OPERATING_EBITDA_TR` = 42.231 tỷ | Dùng `OPERATING_EBITDA_*`, bỏ `EBITDA_TR` |
| `QUICK_RATIO_AQ`, `CPS_AQ` | HPG âm (−0,43; −7.060đ) — sai dấu/định nghĩa | Không dùng; tự tính từ BCTC gốc |
| Phân trang `get_ratios` | trang sau **lặp lại** mã của trang trước | Khử trùng theo `ratioCode`, hoặc `size=300` một trang |
| `get_change_prices` | `price: 0` → `changePct: -100%` (HRC 13/11); `period=1M` trả rỗng | `0` = THIẾU số, không phải sập giá; dùng `period=1D` + Yahoo |
| `get_fund_ratios` | `0` cho NAV 1M/3M/6M/YD của DCDS | `0` ≠ "không đổi" — coi là thiếu, kiểm website QLQ |
| `get_stock_price_by_date` | giá **nghìn VND** (`adClose` 21.05 = 21.050đ), `ad*` = đã điều chỉnh; `nmValue` = **VND** | Không trộn với `value` DataPro (nghìn VND) |
| `get_foreign_trading` | giá trị **VND trần**; tổng sàn lấy dòng `VNINDEX`/`HNX`/`UPCOM` | **Không cộng từng mã** (lệch số chính thức) |
| `get_top_stocks` | `field_sort="marketCap"` → lỗi upstream | Dùng `priceChgPctCr1D` (đã chạy) |

### Gọi từ Python (DataPro + snapshot)

```python
import vndata

bars = vndata.price.ohlcv("HPG.VN", "2026-01-01", "2026-11-13")       # DataPro
flow = vndata.price.foreign_flow("HPG.VN", "2026-11-01", "2026-11-13")
rsi  = vndata.ta.indicator("HPG.VN", "2026-01-01", "2026-11-13").momentum.rsi(14)
icb  = vndata.reference.classification()          # snapshot ICB cấp 2 (VNDIRECT)
vn30 = vndata.reference.symbols_by_group("VN30")  # snapshot rổ (VNDIRECT)
news = vndata.news.rss(hours=24)
vndata.health()                                   # DataPro sống? snapshot bao nhiêu tuổi?
```

`vndata.fundamental.*`, `vndata.macro.*`, `vndata.reference.company/events/...`,
`vndata.corporate.*` **cố ý báo `SourceUnavailable`** và chỉ sang VNDIRECT MCP —
Python không có đường tới nguồn này, và không được tự chế nguồn thay.

### Làm mới snapshot (khi VN30 đổi rổ tháng 1/7, hoặc preflight báo cũ)

1. Gọi `FINFO_API__get_industry_classification(q="industryCode:0500,1300,1700,2300,2700,3300,3500,3700,4500,5300,5500,5700,6500,7500,8300,8500,8600,8700,9500")`.
2. Gọi `FINFO_API__get_top_stocks(index="VN30", field_sort="priceChgPctCr1D", size=40)`.
3. Ghi bằng `vndata.reference.save_classification(df, source=...)` và
   `vndata.reference.save_index_members("VN30", [...], source=...)` — hàm từ
   chối mã trùng ngành. File ở `agent/data/vn_reference/`.

### ⚠️ Bẫy đơn vị DataPro: `VAL` khác thang theo loại công cụ (1000×)

| Loại | Nhận diện | `close` nghĩa là | Thang `value` |
|---|---|---|---|
| Cổ phiếu / ETF | `listed_shares > 0` | giá, **nghìn VND** | **nghìn VND** |
| Chỉ số | `listed_shares = 0`, `open_interest = 0` | **điểm số** | **triệu VND** |
| Phái sinh | `listed_shares = 0`, `open_interest > 0` | điểm chỉ số | **chưa xác minh** |

Dùng `vndata.price.to_vnd(df)` — tự nhận loại, không đổi `close` của chỉ số, và
**từ chối quy đổi GTGD phái sinh** thay vì đoán. Đừng tự nhân 1.000 vào mọi thứ.
DataPro chết thì `vndata.price` **báo lỗi** — không còn nguồn giá dự phòng.

---

## Các thị trường khác

| Source | Markets | Auth | Network |
|--------|---------|------|---------|
| tushare | A-shares, funds, futures, macro | `TUSHARE_TOKEN` | China network |
| akshare | A-shares, US, HK, futures, macro, forex | No | Unrestricted |
| yfinance | US stocks, HK stocks, ETFs | No | Yahoo Finance |
| okx | Crypto (OKX) | No | okx.com |
| ccxt | Crypto (100+ exchanges) | No | exchange access |

**A-shares**: tushare (nếu có `TUSHARE_TOKEN`) > akshare
**US / HK stocks**: yfinance > akshare
**Crypto**: okx (một sàn) > ccxt (đa sàn)
**Futures / Macro ngoài VN**: tushare > akshare

## Backtest (viết `config.json`)

Dùng `source: "auto"` hoặc `"datapro"` — mã `.VN` chỉ có **một** nguồn giá là DataPro;
DataPro chết thì backtest dừng chứ không đổi nguồn. Backtest VN **không** gắn được
`fundamental_fields` (Python không gọi được VNDIRECT): lấy chỉ số qua MCP, ghi CSV, rồi
đọc CSV trong signal engine.

## Quy ước mã

| Market | Format | Ví dụ |
|--------|--------|---------|
| **Vietnam** | `TICKER.VN` | VCB.VN, FPT.VN, VNINDEX.VN, VN30F1M.VN |
| A-shares | `NNNNNN.SZ/SH/BJ` | 000001.SZ, 600000.SH |
| US stocks | `TICKER.US` | AAPL.US, MSFT.US |
| HK stocks | `NNN(N).HK` | 700.HK, 9988.HK |
| Crypto | `SYMBOL-USDT` | BTC-USDT, ETH-USDT |

Hậu tố `.VN` không chỉ để định tuyến nguồn: nó bật luật thị trường VN trong engine
(T+2, biên độ HOSE ±7% / HNX ±10% / UPCOM ±15%, cấm bán khống, lô 100).
Nó cũng là thứ khiến swarm **grounding** nạp giá thật vào prompt của worker —
mã viết trần (`VCB`) sẽ không được grounding và worker sẽ trích giá từ dữ liệu huấn luyện.

## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)

1. **Không bịa/cook số liệu.** Mọi số tài chính phải có nguồn thật. Luôn **audit nhanh, cross-check tối thiểu 2 nguồn uy tín** (vd `cafef.vn`, `vietstock.vn`) — dùng **crawl4ai** cào số rồi đối chiếu; nếu nguồn lệch nhau thì nêu rõ, không chọn bừa.
2. **Nếu DataPro VÀ VNDIRECT MCP đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
3. **Trước khi kết luận nguồn nào sai, kiểm tổng `LNST = LN cổ đông mẹ + lợi ích cổ đông thiểu số`.** Bảng cào từ web hay lệch cột; phép cộng này phân xử.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
