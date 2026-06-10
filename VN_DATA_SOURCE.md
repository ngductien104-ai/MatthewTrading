# Nguồn dữ liệu Việt Nam (DataPro + vnstock)

Bản fork này bổ sung 2 nguồn dữ liệu cho thị trường chứng khoán Việt Nam, theo đúng
cơ chế "custom data source" của Vibe-Trading:

| Loại dữ liệu | Nguồn | Dùng cho |
|---|---|---|
| Giá OHLCV, khối lượng, dòng tiền nước ngoài | **DataPro** (`source="datapro"`) | Backtest giá |
| BCTC (KQKD, CĐKT, lưu chuyển tiền tệ) | **vnstock** (tự động khi source=datapro) | `fundamental_fields` |

## 1. Điều kiện chạy

- **DataPro desktop phải đang chạy** và đã bật API (cổng `6789`).
- Biến môi trường (đặt trong `agent/.env`):
  ```
  DATAPRO_URL=http://localhost:6789
  DATAPRO_API_KEY=WmKgntRMUMvd8rItMiTAoyrmczEGMRSGeqAR8oKUxwM
  ```
  > Localhost thường không cần key; key dùng khi truy cập remote.
- `vnstock` đã được cài trong `.venv` (cho phần BCTC).

## 2. Quy ước mã

Thêm hậu tố **`.VN`** vào mã để hệ thống áp đúng luật thị trường VN
(biên độ, T+2): ví dụ `VCB.VN`, `FPT.VN`, `VNINDEX.VN`.

## 3. Cấu hình backtest mẫu (`config.json`)

```json
{
  "codes": ["FPT.VN"],
  "start_date": "2024-01-01",
  "end_date": "2025-12-31",
  "source": "datapro",
  "interval": "1D",
  "engine": "daily",
  "initial_cash": 100000000,
  "fundamental_fields": { "income": ["net_sales", "gross_profit"] }
}
```

Chạy: `python -m backtest.runner <thư_mục_run>` (xem ví dụ ở `agent/runs/test_datapro`).
Hoặc nói với agent bằng ngôn ngữ tự nhiên — nó tự sinh config.

## 4. Luật thị trường VN (engine `vn_equity`)

- **T+2**: cổ phiếu mua hôm T chỉ bán được từ T+2 (không lướt T+0).
- **Không bán khống.**
- **Biên độ ngày** (so với giá tham chiếu): HOSE ±7% · HNX ±10% · UPCOM ±15%.
  - Mặc định coi mã là **HOSE (±7%)**. Khai báo sàn khác trong config nếu cần:
    `"vn_exchange_map": {"SHS": "HNX"}` hoặc `"vn_default_exchange": "HNX"`.
- **Lô**: làm tròn xuống 100 cp. **Phí**: 0,15%/lượt + thuế bán 0,1%.

## 5. Dữ liệu cơ bản vnstock (`fundamental_fields`)

- Bảng hỗ trợ: `income`, `balancesheet`, `cashflow`.
- Tên field = **`item_id`** của vnstock (vd: `net_sales`, `gross_profit`,
  `cost_of_sales`, `total_assets`, `net_cash_flow_from_operating_activities`...).
  Để xem danh sách item_id, gọi `Finance(symbol, source="VCI").income_statement(period="year", lang="en")["item_id"]`.
- **An toàn point-in-time**: mỗi kỳ chỉ "xuất hiện" sau ngày công bố ước tính
  (cuối kỳ + 90 ngày), nên không bị nhìn trước (lookahead).

### Giới hạn cần biết
- Bản **community của vnstock chỉ trả ~4 kỳ năm gần nhất** → backtest dài nhiều năm
  sẽ thiếu BCTC ở các năm cũ (cột nhận giá trị `NaN`).
- **Chỉ số (P/E, ROE, EPS)** KHÔNG đưa vào đường PIT này vì endpoint `ratio()` của
  bản community trả layout kỳ không ổn định. Cần phân tích chỉ số → dùng skill
  `valuation-model` / swarm (chạy trên hermes venv).

## 6. Các file đã thêm/sửa

- `agent/backtest/loaders/datapro_loader.py` — loader giá DataPro (mới)
- `agent/backtest/loaders/vnstock_fundamentals.py` — provider BCTC vnstock PIT (mới)
- `agent/backtest/engines/vn_equity.py` — engine luật HOSE/HNX/UPCOM (mới)
- `agent/backtest/loaders/registry.py` — đăng ký `datapro` + chain `vn_equity`
- `agent/backtest/engines/_market_hooks.py` — nhận diện mã `.VN`
- `agent/backtest/runner.py` — định tuyến engine VN
- `agent/backtest/metrics.py` — 250 phiên/năm cho `datapro`
- `agent/backtest/engines/base.py` — chọn provider BCTC theo nguồn
