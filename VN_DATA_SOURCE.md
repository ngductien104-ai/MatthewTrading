# Nguồn dữ liệu Việt Nam — DataPro + VNDIRECT MCP

**Từ 13/11/2026 dự án không dùng vnstock** (sponsored `vnstock_data` /
`vnstock_ta` / `vnstock_news` và bản free). Gói đã huỷ; xác thực ngừng từ
10/11/2026 — chính việc này làm chết bản tin sáng 13/11. Mọi dữ liệu thị trường
Việt Nam đi qua **hai nguồn sự thật**, không chồng lấn:

| Nguồn | Phủ | Ai gọi được |
|---|---|---|
| **DataPro** (desktop `localhost:6789`) | giá/KL/GTGD, giá tham chiếu, khối ngoại & tự doanh theo mã, thoả thuận, chủ động mua/bán, chỉ số, phái sinh, ETF, danh sách mã + SLCP | Python (`agent/vndata`) + MCP `datapro` |
| **VNDIRECT MCP** (connector claude.ai "VNDIRECT MCP", OAuth, endpoint `https://mcp.vndirect.com.vn/mcp`) | chỉ số tài chính & định giá (≤5 năm), chỉ số ngân hàng, ICB 4 cấp, rổ chỉ số, sự kiện DN, lãnh đạo, khối ngoại tổng sàn chính thức, độ rộng sàn, quỹ mở, phái sinh, hàng hoá, lịch giao dịch | **Chỉ Claude / subagent** (tool `FINFO_API__*`) |

Không nguồn API nào có **BCTC từng dòng + thuyết minh** → lấy từ **PDF gốc**
(`agent/scripts/evidence_pack.py`, quy trình Phase 0 ở `CLAUDE.md`).
Vĩ mô VN → cơ quan công bố gốc (GSO, NHNN, BTC). Tỷ giá, DXY → Yahoo.

Bảng tool đầy đủ, cú pháp `get_ratios` và mã `ratioCode`: skill
[`data-routing`](agent/src/skills/data-routing/SKILL.md).

## 1. Lớp Python `agent/vndata`

| Module | Nguồn | Ghi chú |
|---|---|---|
| `vndata.price` | DataPro | DataPro chết → `SourceUnavailable`. **Không còn nguồn dự phòng.** |
| `vndata.reference.symbols/equities/etfs` | DataPro `/api/symbols` | cache trong tiến trình (DataPro trả 503 khi gọi dồn) |
| `vndata.reference.classification` | snapshot ICB cấp 2 từ VNDIRECT | `agent/data/vn_reference/icb_classification.csv` |
| `vndata.reference.symbols_by_group` | snapshot rổ từ VNDIRECT | `agent/data/vn_reference/index_members.json` |
| `vndata.ta` | tự tính trên giá DataPro | RSI/ATR làm mượt Wilder chuẩn (khớp ví dụ gốc 70,53) |
| `vndata.news.rss` | feed RSS nhà xuất bản | thân bài → `read_url` / crawl4ai |
| `vndata.fundamental/macro/corporate`, `reference.company/events/...`, `news.company_news/crawl` | — | **cố ý raise** `SourceUnavailable` chỉ sang VNDIRECT MCP |

Snapshot ghi `as_of` + `source`; làm mới khi VN30 đổi rổ (tháng 1, 7) hoặc khi
`agent/scripts/vn_preflight.py` báo thiếu/cũ — cách làm ở skill `data-routing`.
Snapshot đầu tiên (13/11/2026): ICB phủ **1.510/1.528** mã niêm yết DataPro; VN30
đủ 30 mã.

## 2. Điều kiện chạy

```bash
.venv/Scripts/python.exe agent/scripts/vn_preflight.py   # DataPro sống? snapshot bao nhiêu tuổi?
```

VNDIRECT MCP kiểm từ Claude: tool `health` của connector, hoặc `/mcp`. Hết phiên
OAuth → đăng nhập lại ở Connectors / `/mcp`.

## 3. Đơn vị

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

### VNDIRECT MCP (đo 13/11/2026)

| Tool / trường | Đơn vị / bẫy |
|---|---|
| tỷ lệ trong `get_ratios` | **phân số** (ROAE 0,195 = 19,5%; NPL 0,00706 = 0,71%) |
| `EBITDA_TR` | **hỏng** (HPG −174.797 tỷ) → dùng `OPERATING_EBITDA_TR` |
| `QUICK_RATIO_AQ`, `CPS_AQ` | sai dấu → tự tính từ BCTC gốc |
| `get_stock_price_by_date` | giá **nghìn VND**, `ad*` = điều chỉnh; `nmValue` = **VND** |
| `get_foreign_trading` | **VND trần**; tổng sàn = dòng `VNINDEX`/`HNX`/`UPCOM`, không cộng từng mã |
| `get_change_prices` | `price: 0` → `changePct −100%` = **thiếu số**; `period=1M` trả rỗng |
| `get_fund_ratios` | `0` = **thiếu**, không phải "không đổi" |
| `get_ratios` phân trang | trang sau lặp mã trang trước → khử trùng theo `ratioCode` |

## 4. Quy ước mã

Hậu tố **`.VN`**: `VCB.VN`, `FPT.VN`, `VNINDEX.VN`, `VN30F1M.VN`.

Hậu tố này làm ba việc, không phải một:
1. định tuyến sang DataPro;
2. bật luật thị trường VN trong engine (T+2, biên độ, cấm bán khống, lô 100);
3. **bật swarm grounding** — worker được nạp giá thật vào prompt. Mã viết trần
   (`VCB`) sẽ **không** được grounding và worker sẽ trích giá từ dữ liệu huấn luyện.

## 5. Luật thị trường VN (engine `vn_equity`)

- **T+2**: mua hôm T chỉ bán được từ T+2.
- **Không bán khống.**
- **Biên độ ngày** so với `ref_price`: HOSE ±7% · HNX ±10% · UPCOM ±15%.
  Mặc định coi là HOSE; khai sàn khác qua `"vn_exchange_map": {"SHS": "HNX"}`
  hoặc `"vn_default_exchange": "HNX"`.
- **Lô** 100 cp (làm tròn xuống). **Phí** 0,15%/lượt + thuế bán 0,1%.

## 6. Backtest mẫu (`config.json`)

```json
{
  "codes": ["FPT.VN"],
  "start_date": "2024-01-01",
  "end_date": "2025-12-31",
  "source": "datapro",
  "interval": "1D",
  "engine": "daily",
  "initial_cash": 100000000
}
```

Chạy: `python -m backtest.runner <thư_mục_run>`. Chuỗi `vn_equity` = `["datapro"]`.
`fundamental_fields` cho mã `.VN` **báo lỗi** (Python không gọi được VNDIRECT):
lấy chỉ số qua MCP → CSV có `reportDate` → signal engine gắn point-in-time (năm
+90 ngày, quý +45 ngày — `vndata.fundamental.DISCLOSURE_LAG_DAYS`).

## 7. Các file của lớp dữ liệu

| File | Vai trò |
|---|---|
| `agent/vndata/__init__.py` | Hợp đồng công khai + `SOURCE_MAP` + `health()` |
| `agent/vndata/price.py` | DataPro: OHLCV, dòng tiền, thoả thuận, chủ động, bẫy đơn vị |
| `agent/vndata/reference.py` | DataPro symbol list + snapshot ICB / rổ (VNDIRECT) |
| `agent/vndata/ta.py` | Chỉ báo kỹ thuật tự tính |
| `agent/vndata/news.py` | RSS nhà xuất bản |
| `agent/vndata/fundamental.py`, `macro.py`, `corporate.py` | Chỉ còn hợp đồng + lỗi chỉ đường VNDIRECT |
| `agent/vndata/errors.py` | `SourceUnavailable`, `moved_to_vndirect()` |
| `agent/backtest/loaders/datapro_loader.py`, `registry.py` | Loader giá VN duy nhất |
