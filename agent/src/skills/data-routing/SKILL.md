---
name: data-routing
category: data-source
description: Data source selection decision tree. Load this skill BEFORE any backtest or data-fetching task to choose the correct source. For Vietnam there is exactly one correct source per data class — this skill names it.
---

## Vietnam — nguồn sự thật (BẮT BUỘC)

Thị trường Việt Nam có **4 nguồn sự thật, không chồng lấn**. Mỗi loại dữ liệu chỉ có
**một** nguồn đúng. Không tự chọn nguồn khác, không "thử nguồn nào có trước".

| Loại dữ liệu | Nguồn sự thật | Gọi qua |
|---|---|---|
| OHLCV, khối lượng, giá trị GD | **DataPro** | `vndata.price.ohlcv()` |
| Giá tham chiếu / biên độ ngày | **DataPro** | `vndata.price.ohlcv()` → cột `ref_price` |
| Khối ngoại mua/bán ròng | **DataPro** | `vndata.price.foreign_flow()` |
| Tự doanh mua/bán ròng | **DataPro** | `vndata.price.proprietary_flow()` |
| Thoả thuận, chủ động mua/bán | **DataPro** | `vndata.price.ohlcv()` |
| Chỉ số, phái sinh, ETF, forex | **DataPro** | `vndata.price.ohlcv()` |
| BCTC (KQKD, CĐKT, LCTT), thuyết minh | **vnstock_data** | `vndata.fundamental.statement()` |
| Chỉ số tài chính, định giá | **vnstock_data** | `vndata.fundamental.ratios()` |
| Vĩ mô, lãi suất, tỷ giá, hàng hoá | **vnstock_data** | `vndata.macro.*` |
| Danh sách mã, ICB, rổ chỉ số, cổ đông | **vnstock_data** | `vndata.reference.*` |
| Chỉ báo kỹ thuật | **vnstock_ta** (tính trên giá DataPro) | `vndata.ta.indicator()` |
| Tin tức, nội dung bài báo | **vnstock_news** | `vndata.news.*` |

### `vnstock` bản free KHÔNG còn là nguồn

Gói tài trợ **silver** đã kích hoạt. Bản free bị loại khỏi mọi chuỗi fallback vì:
bảng `ratio()` trả layout kỳ không ổn định (đã từng trả số 2018 cho kỳ mới nhất),
giá không có `ref_price` nên không dựng được biên độ, và không có dòng tiền
khối ngoại/tự doanh. **Không viết `from vnstock import ...` trong bất kỳ phân tích nào.**

### Cách gọi

Luôn đi qua `vndata` — không import thẳng `vnstock_data` / `vnstock_ta` / `vnstock_news`.
Lớp này sửa sẵn các bẫy đơn vị (xem phần dưới) và báo lỗi to khi nguồn chết,
thay vì trả về số trông có vẻ đúng.

```python
import vndata

# Giá + dòng tiền (DataPro)
bars = vndata.price.ohlcv("HPG.VN", "2026-01-01", "2026-08-27")
flow = vndata.price.foreign_flow("HPG.VN", "2026-08-01", "2026-08-27")

# Cơ bản (vnstock_data) — đã chuẩn hoá đơn vị
roe = vndata.fundamental.ratios_wide("HPG")["RT_PRT_ROE"]      # đơn vị: %, không phải fraction
inc = vndata.fundamental.wide("HPG", "income_statement")        # đơn vị: VND
fix = vndata.fundamental.derived("HPG")                         # minority/opex/equity đã dựng lại

# Kỹ thuật (vnstock_ta trên giá DataPro)
ind = vndata.ta.indicator("HPG.VN", "2026-01-01", "2026-08-27")
rsi = ind.momentum.rsi(length=14)

# Tin tức (vnstock_news)
news = vndata.news.company_news("HPG")

# Kiểm tra nguồn nào đang sống trước khi chạy phân tích dài
vndata.health()
```

Chạy bằng Python có gói tài trợ: `$HOME\.venv\Scripts\python.exe`, với
`PYTHONPATH` trỏ vào thư mục `agent/`.

### ⚠️ Bẫy đơn vị DataPro: `VAL` khác thang theo loại công cụ (1000×)

| Loại | Nhận diện | `close` nghĩa là | Thang `value` |
|---|---|---|---|
| Cổ phiếu / ETF | `listed_shares > 0` | giá, **nghìn VND** | **nghìn VND** |
| Chỉ số | `listed_shares = 0`, `open_interest = 0` | **điểm số** | **triệu VND** |
| Phái sinh | `listed_shares = 0`, `open_interest > 0` | điểm chỉ số | **chưa xác minh** |

Dùng `vndata.price.to_vnd(df)` — tự nhận loại, không đổi `close` của chỉ số, và
**từ chối quy đổi GTGD phái sinh** thay vì đoán. Đừng tự nhân 1.000 vào mọi thứ.

### ⚠️ Bẫy đơn vị của `vnstock_data` — `vndata` đã sửa, đừng sửa lại

Nếu vì lý do nào đó phải đọc thẳng `vnstock_data`, những field sau **nói dối** ở
cột `unit` (đã kiểm chứng trên HPG và TCB, FY2025, ngày 27/08/2026):

| Field | `unit` khai báo | Giá trị thật |
|---|---|---|
| `RT_VALUE_MARKET_CAP`, `RT_VALUE_EBIT`, `RT_VALUE_EBITDA` | `tỷ VNĐ` | VND trần (chia 1e9 mới ra tỷ) |
| `RT_PRT_*`, `RT_BANK_*` | `%` | **fraction** (ROE 0.1269 = 12,69%) |
| `RT_VALUE_DIVIDEND_YIELD` | `%` | đã là % rồi — KHÔNG nhân 100 |
| `RT_BANK_COF`, `RT_BANK_CIR`, `RT_BANK_NPL_COVERAGE`, `RT_BANK_PROVISION_TO_LOANS` | `%` | fraction **và mất dấu** (coverage −1.28 = 128%) |
| `RT_VALUE_EQUITY`, `RT_BANK_NOII` | `tỷ VNĐ` | **hỏng** — lấy vốn chủ từ `BS_EQUITY` |
| `IS_OPERATING_EXPENSES` (ngân hàng) | VND | `NaN` — tự tính `TOI − PPOP` |
| `IS_MINORITY_INTEREST` | VND | mất dấu khi lỗ — tự tính `LNST − LN cổ đông mẹ` |

Hai quy ước nữa: **`0.0` trong bảng ratio nghĩa là "không áp dụng"**, không phải số
đo (ngân hàng trả 0.0 cho vòng quay hàng tồn kho, DN sản xuất trả 0.0 cho NIM) —
`vndata` đổi thành `NaN`. Và **`NaN` giữ nguyên `NaN`**, không bao giờ thay bằng 0.

### Tình trạng nguồn đã biết (27/08/2026)

- **`asean-apigw.aseansc.com.vn` (backend macro) hay sập tạm thời rồi tự sống lại.**
  Sáng 27/08/2026 nó chết ~1 tiếng rồi hồi. Ảnh hưởng khi sập: `macro.economy.*`
  (CPI, GDP, tín dụng, FDI...), `macro.commodity.*`, hầu hết `macro.currency.*`,
  kèm `Insights.flow` / `Insights.sentiment`.
  **Gặp lỗi thì THỬ LẠI trước** — kiểm bằng `vndata.health()["asean_macro_backend"]`.
  Dấu hiệu sập của nó là DNS vẫn phân giải nhưng TCP không kết nối; **đó không
  phải lỗi mạng máy anh**, đừng đi chỉnh firewall/proxy.
  Chỉ khi sập kéo dài mới cào từ **cơ quan công bố gốc** (GSO, NHNN, Bộ Tài chính)
  bằng crawl4ai và **ghi rõ nguồn**, không ước lượng.
  `vndata.macro.currency("interest_rate")` và `vndata.macro.index_valuation()`
  dùng backend khác, chạy xuyên qua các đợt sập.
- **Các method phẳng `Macro().gdp()`, `.cpi()`, `.interest_rate()`… bị
  DEPRECATED, gỡ sau 31/08/2026.** `vndata.macro` chỉ bọc API sub-domain mới
  (`economy` / `currency` / `commodity`), nên không viết code gọi method phẳng.

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

Dùng `source: "auto"` — runner tự nhận thị trường theo hậu tố mã và tự chuyển nguồn
khi nguồn chính chết. Với mã `.VN`, chuỗi là `datapro → vnstock_data`; bản free
**không** nằm trong chuỗi, muốn dùng phải khai `source: "vnstock"` một cách có chủ đích.

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
2. **Nếu DataPro VÀ vnstock_data đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
3. **Trước khi kết luận nguồn nào sai, kiểm tổng `LNST = LN cổ đông mẹ + lợi ích cổ đông thiểu số`.** Bảng cào từ web hay lệch cột; phép cộng này phân xử.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
