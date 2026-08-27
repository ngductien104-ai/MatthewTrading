# Nguồn dữ liệu Việt Nam — kiến trúc 4 nguồn sự thật

Bản fork này định tuyến **mọi** dữ liệu thị trường Việt Nam qua đúng một lớp:
`agent/vndata`. Mỗi loại dữ liệu có **một** nguồn sự thật, không chồng lấn,
không "thử nguồn nào có trước".

| Loại dữ liệu | Nguồn sự thật | Entry point |
|---|---|---|
| OHLCV, khối lượng, giá trị GD | **DataPro** | `vndata.price.ohlcv()` |
| Giá tham chiếu (biên độ ngày) | **DataPro** | cột `ref_price` |
| Khối ngoại mua/bán ròng | **DataPro** | `vndata.price.foreign_flow()` |
| Tự doanh (tự doanh CTCK) | **DataPro** | `vndata.price.proprietary_flow()` |
| Thoả thuận, chủ động mua/bán | **DataPro** | cột `put_through_*`, `active_*` |
| Chỉ số, phái sinh, ETF, forex | **DataPro** | `vndata.price.ohlcv()` |
| BCTC + thuyết minh | **vnstock_data** | `vndata.fundamental.statement()` |
| Chỉ số tài chính, định giá | **vnstock_data** | `vndata.fundamental.ratios()` |
| Vĩ mô, lãi suất, tỷ giá, hàng hoá | **vnstock_data** | `vndata.macro.*` |
| Danh sách mã, ICB, rổ, cổ đông | **vnstock_data** | `vndata.reference.*` |
| Chỉ báo kỹ thuật | **vnstock_ta** (trên giá DataPro) | `vndata.ta.indicator()` |
| Tin tức + nội dung bài báo | **vnstock_news** | `vndata.news.*` |
| Lịch sử tăng vốn, giao dịch nội bộ, cơ cấu sở hữu | **vnstock (free)** — ngoại lệ duy nhất | `vndata.corporate.*` |

## 1. `vnstock` bản free không còn là nguồn

Tài khoản đã lên **gói tài trợ silver** (300 req/phút, 15.000 req/giờ). Bản free
bị gỡ khỏi chuỗi fallback `vn_equity` vì ba lý do cụ thể:

- bảng `ratio()` trả layout kỳ không ổn định (từng trả số 2018 cho kỳ mới nhất);
- giá không có `REF_PX` nên engine không dựng được biên độ trần/sàn;
- không có dòng tiền khối ngoại / tự doanh / thoả thuận.

Chuỗi mới: **`datapro` → `vnstock_data`**. Muốn dùng bản free phải khai
`source: "vnstock"` một cách có chủ đích, không có đường rơi ngầm.

**Ngoại lệ duy nhất, được ghi rõ** — `vndata.corporate`: gói tài trợ *không hề có*
`capital_history`, `insider_trading`, `ownership`. Ba hàm này nằm gọn trong một
file, đóng dấu nguồn lên từng frame trả về, và không có gì khác được phép
`import vnstock`.

## 2. Điều kiện chạy

- **DataPro desktop phải bật** và mở API (cổng `6789`).
  ```
  DATAPRO_URL=http://localhost:6789
  DATAPRO_API_KEY=...          # chỉ cần khi truy cập remote
  ```
- **Gói tài trợ vnstock đã kích hoạt.** API key ở `$HOME\.vnstock\api_key.json`.
  Kiểm nhanh: `python -c "import vnai; print(vnai.get_user_tier())"` → `silver`.
- Python có gói tài trợ: `$HOME\.venv\Scripts\python.exe` (và `.venv` của project),
  chạy với `PYTHONPATH` trỏ vào `agent/`.

Kiểm tra toàn bộ trong một lệnh:

```python
import vndata
vndata.health()
# {'datapro': True, 'tier': {'tier': 'silver', ...},
#  'installed': {'vnstock_data': '3.2.8', 'vnstock_ta': '1.0.6', 'vnstock_news': '2.2.2'},
#  'asean_macro_backend': False}
```

## 3. Đơn vị — đã chuẩn hoá một lần, đừng chuẩn hoá lại

### DataPro (`vndata.price`) — ⚠️ đơn vị KHÁC NHAU theo loại công cụ

Đây là bẫy 1000×. `VAL` **không** cùng thang cho mọi mã:

| Loại | Nhận diện | `*_PX` nghĩa là | Thang `VAL` |
|---|---|---|---|
| Cổ phiếu / ETF | `LISTED_VOL > 0` | giá, **nghìn VND** | **nghìn VND** |
| Chỉ số | `LISTED_VOL = 0`, `OI = 0` | **điểm số** (không phải giá) | **triệu VND** |
| Phái sinh | `LISTED_VOL = 0`, `OI > 0` | điểm chỉ số | **chưa xác minh** |

Bằng chứng (đo 25–27/08/2026):
- HPG 68.320.100 cp × 23.163 đ = 1,58e12 đ, `VAL` = 1.793.446.015 → khớp ở **×1.000**.
- E1VFVN30 845.000 × 31.750 = 2,68e10 đ, `VAL` = 26.915.697 → cũng **×1.000**.
- HNXINDEX `VAL` = 2.621.503 chỉ hợp lý ở **×1.000.000** (= 2.621 tỷ; 117,9 triệu cp
  → giá bình quân ~22.240 đ). Ở thang cổ phiếu sẽ ra 22 đ/cp — vô lý.
- VN30F1M không khớp thang nào → lớp này **từ chối quy đổi GTGD phái sinh**
  thay vì bịa hệ số.

`VOL` và mọi `*_volume`: **số cổ phiếu / số hợp đồng**.

Quy đổi: `vndata.price.to_vnd(df)` — tự nhận loại công cụ, không đổi `close` của
chỉ số (vì đó là điểm số), và ghi loại đã dùng vào `df.attrs["instrument"]`.

### vnstock_data (`vndata.fundamental`)

Bảng `ratio()` khai `unit` **sai** ở nhiều field. Đã kiểm chứng trực tiếp trên
HPG (sản xuất) và TCB (ngân hàng), FY2025, ngày 27/08/2026:

| Field | `unit` khai báo | Giá trị thật |
|---|---|---|
| `RT_VALUE_MARKET_CAP`, `RT_VALUE_EBIT`, `RT_VALUE_EBITDA` | `tỷ VNĐ` | **VND trần** |
| `RT_PRT_*`, `RT_BANK_*` | `%` | **fraction** (ROE `0.1269` = 12,69%) |
| `RT_VALUE_DIVIDEND_YIELD` | `%` | **đã là %** — không nhân 100 |
| `RT_BANK_COF`, `CIR`, `NPL_COVERAGE`, `PROVISION_TO_LOANS` | `%` | fraction **và mất dấu** (`-1.28` = 128%) |
| `RT_VALUE_EQUITY`, `RT_BANK_NOII` | `tỷ VNĐ` | **hỏng** → lấy `BS_EQUITY` |
| `IS_OPERATING_EXPENSES` (NH) | VND | `NaN` → tính `TOI − PPOP` |
| `IS_MINORITY_INTEREST` | VND | mất dấu khi lỗ → tính `LNST − LN cổ đông mẹ` |

Hai quy ước chung: **`0.0` trong bảng ratio = "không áp dụng"**, không phải số đo
(ngân hàng trả `0.0` cho vòng quay hàng tồn kho, DN sản xuất trả `0.0` cho NIM)
→ đổi thành `NaN`; và **`NaN` giữ nguyên `NaN`**, không bao giờ điền 0.

Bản đặc tả nằm ở `agent/vndata/normalize.py` và được **cả** provider backtest
(`vnstock_data_fundamentals.py`) dùng chung, nên `ratio_roe` trong backtest và
`RT_PRT_ROE` trong phân tích luôn cùng một đơn vị (**%**).

## 4. Tình trạng nguồn đã biết (27/08/2026)

- **Macro qua `asean-apigw.aseansc.com.vn` không truy cập được từ máy này.**
  DNS phân giải ra `119.17.209.229` nhưng TCP và ICMP đều không thông (máy đi qua
  Cisco Umbrella SSE). Ảnh hưởng: `macro.economy.*`, `macro.commodity.*`, hầu hết
  `macro.currency.*`, và `Insights.flow` / `Insights.sentiment`.
  **Còn chạy:** `vndata.macro.currency("interest_rate")`, `vndata.macro.index_valuation()`.
  Khi cần số vĩ mô → cào từ cơ quan công bố gốc (GSO, NHNN, Bộ Tài chính) và ghi rõ nguồn.
- **Các method phẳng `Macro().gdp()`, `.cpi()`, `.interest_rate()`… bị DEPRECATED,
  gỡ sau 31/08/2026.** `vndata.macro` chỉ bọc API sub-domain mới, nên không cần sửa lại.
- `vnstock_pipeline` cần tier golden/diamond — silver chưa có.

## 5. Quy ước mã

Hậu tố **`.VN`**: `VCB.VN`, `FPT.VN`, `VNINDEX.VN`, `VN30F1M.VN`.

Hậu tố này làm ba việc, không phải một:
1. định tuyến sang chuỗi nguồn VN;
2. bật luật thị trường VN trong engine (T+2, biên độ, cấm bán khống, lô 100);
3. **bật swarm grounding** — worker được nạp giá thật vào prompt. Mã viết trần
   (`VCB`) sẽ **không** được grounding và worker sẽ trích giá từ dữ liệu huấn luyện.

## 6. Luật thị trường VN (engine `vn_equity`)

- **T+2**: mua hôm T chỉ bán được từ T+2.
- **Không bán khống.**
- **Biên độ ngày** so với `ref_price`: HOSE ±7% · HNX ±10% · UPCOM ±15%.
  Mặc định coi là HOSE; khai sàn khác qua `"vn_exchange_map": {"SHS": "HNX"}`
  hoặc `"vn_default_exchange": "HNX"`.
- **Lô** 100 cp (làm tròn xuống). **Phí** 0,15%/lượt + thuế bán 0,1%.

## 7. Backtest mẫu (`config.json`)

```json
{
  "codes": ["FPT.VN"],
  "start_date": "2024-01-01",
  "end_date": "2025-12-31",
  "source": "auto",
  "interval": "1D",
  "engine": "daily",
  "initial_cash": 100000000,
  "fundamental_fields": { "ratio": ["roe", "pe", "pb"] }
}
```

Chạy: `python -m backtest.runner <thư_mục_run>`.

Độ sâu BCTC gói tài trợ: **8 kỳ năm + 34 kỳ quý** (không còn giới hạn ~4 kỳ của
bản free). Mỗi kỳ chỉ "xuất hiện" sau ngày công bố ước tính (năm +90 ngày, quý
+45 ngày) nên không bị nhìn trước.

## 8. Các file của lớp dữ liệu

| File | Vai trò |
|---|---|
| `agent/vndata/__init__.py` | Hợp đồng công khai + `SOURCE_MAP` + `health()` |
| `agent/vndata/price.py` | DataPro: OHLCV, dòng tiền, thoả thuận, chủ động |
| `agent/vndata/fundamental.py` | BCTC, chỉ số, `derived()` dựng lại 3 field hỏng |
| `agent/vndata/normalize.py` | **Bản đặc tả đơn vị/dấu duy nhất** |
| `agent/vndata/macro.py` | Vĩ mô/lãi suất/hàng hoá (chỉ API sub-domain mới) |
| `agent/vndata/reference.py` | Danh mục mã, ICB, cổ đông, quỹ, ETF |
| `agent/vndata/ta.py` | vnstock_ta chạy trên giá DataPro |
| `agent/vndata/news.py` | Tin tức + cào toàn văn 21 đầu báo |
| `agent/vndata/corporate.py` | Ngoại lệ free tier (3 hàm, có đóng dấu nguồn) |
| `agent/vndata/errors.py` | `SourceUnavailable` — nguồn chết thì báo to, không lùi ngầm |

Các file cũ vẫn giữ vai trò backtest: `datapro_loader.py`,
`vnstock_data_loader.py`, `vnstock_data_fundamentals.py`, `vn_equity.py`,
`registry.py`, `_market_hooks.py`, `runner.py`, `metrics.py`.
