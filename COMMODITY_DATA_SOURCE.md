# Nguồn dữ liệu hàng hoá — bảng định tuyến đã kiểm chứng

File anh em với `VN_DATA_SOURCE.md`. Chỗ kia định tuyến dữ liệu **cổ phiếu Việt Nam**;
chỗ này định tuyến **giá hàng hoá** cho swarm `commodity_research_team_VN`.

Lý do file này tồn tại: `agent/src/swarm/grounding.py` chỉ nhận diện mã dạng `.VN` /
`.US` / `.HK` / `-USDT`. Biến `{commodity}` của preset hàng hoá ("dầu thô", "đồng")
**không khớp mẫu nào**, nên swarm chạy nguyên trạng sẽ không có một dòng giá thật nào
trong prompt — và worker sẽ trích giá từ trí nhớ mô hình. `agent/scripts/commodity_datapack.py`
bịt lỗ đó: kéo giá thật, kiểm chéo, rồi tiêm vào **mọi** worker qua `private_context`.

Mỗi dòng trong bảng dưới đây **đã được gọi thật**, không suy đoán. Lần dò gần nhất:
**07/09/2026** (toàn bộ 20 route).

---

## 1. Bảng định tuyến

`LIVE` = bar cuối cách hôm nay ≤ 10 ngày (`STALE_DAYS`). Ngày trong ngoặc là bar cuối
đo ngày 07/09/2026.

| Mặt hàng | Yahoo | vndata | akshare | Proxy cổ phiếu VN |
|---|---|---|---|---|
| `oil_crude` — Dầu thô WTI, USD/thùng | `CL=F` ✅ (06/09) | `oil_crude` ✅ (06/09) | `SC0` ✅ (04/09) | BSR, PLX, GAS, PVD, PVS, PVT |
| `oil_brent` — Dầu Brent, USD/thùng | `BZ=F` ✅ (06/09) | — | — | BSR, PLX, GAS, PVD, PVS, PVT |
| `gas` — Khí Henry Hub, USD/MMBtu | `NG=F` ✅ (06/09) | `gas` + `market='GLOBAL'` ✅ (06/09) | — | GAS, CNG, PGD, PGS |
| `gas_vn` — Xăng dầu bán lẻ VN, nghìn VND/lít | — | `gas` + `market='VN'` ✅ (07/09) | — | PLX, OIL, COM |
| `copper` — Đồng, USD/lb | `HG=F` ✅ (06/09) | — (chỉ snapshot trong `listing`) | `CU0` ✅ (04/09) | — |
| `aluminium` — Nhôm, USD/tấn | `ALI=F` ✅ (06/09) | — | `AL0` ✅ (04/09) | — |
| `gold` — Vàng thế giới, USD/oz | `GC=F` ✅ (06/09) | `gold` + `market='GLOBAL'` ✅ (06/09) | `AU0` ✅ (04/09) | PNJ |
| `gold_vn` — Vàng SJC, nghìn VND/lượng | — | `gold` + `market='VN'` ✅ (07/09) | — | PNJ |
| `steel` — Thép HRC, USD/tấn ngắn | `HRC=F` ✅ (06/09) | `steel` + `market='GLOBAL'` ✅ (04/09) | `RB0` ✅ (04/09) | HPG, HSG, NKG, GDA |
| `steel_vn` — Thép xây dựng VN, nghìn VND/kg | — | `steel` + `market='VN'` ✅ (04/09) | — | HPG, HSG, NKG, GDA, VGS |
| `iron_ore` — Quặng sắt 62% Fe, USD/tấn | `TIO=F` ✅ (04/09) | ⛔ **cố ý không dùng** (xem §3) | `I0` ✅ (04/09) | HPG |
| `coke` — Than cốc, CNY/tấn | — | ⛔ **cố ý không dùng** (xem §3) | `J0` ✅ (04/09) | HPG |
| `rubber` — Cao su, CNY/tấn | — (không có mã) | — (không có series) | `RU0` ✅ (04/09) | PHR, DPR, GVR, DRC, CSM |
| `sugar` — Đường thô #11, cent/lb | `SB=F` ✅ (04/09) | `sugar` ✅ (04/09) — **chuẩn khác** | `SR0` ✅ (04/09) | SBT, LSS, QNS |
| `corn` — Ngô, cent/bushel | `ZC=F` ✅ (04/09) | `corn` ✅ (04/09) | — | DBC, BAF, MML |
| `soybean` — Đậu tương, cent/bushel | `ZS=F` ✅ (04/09) | `soybean` ✅ (04/09) | — | DBC, BAF, MML |
| `coffee` — Cà phê Arabica, cent/lb | `KC=F` ✅ (04/09) | — (Robusta chỉ có trong `listing`) | — | PAN, LTG |
| `pork` — Heo hơi VN, VND/kg | — | `pork` ✅ (28/08, tần suất **tuần**) | — | DBC, BAF, HAG, MML |
| `urea` — Phân urê, USD/tấn | — | `fertilizer_ure` ⚠️ **STALE** (29/07, trễ 40 ngày) | — | DPM, DCM, LAS, BFC |

**Tỷ giá / vĩ mô nền** (kéo kèm mọi data pack, `MACRO_CONTEXT`): `DX-Y.NYB` (DXY),
`^TNX` (US10Y), `USDVND=X`, `^GSPC`, `000001.SS` — **toàn bộ qua Yahoo**. DataPro không
có tape FX; xem `VN_DATA_SOURCE.md` §4.

---

## 2. Bốn nguồn, mỗi nguồn một vai

| Nguồn | Vai trò | Đơn vị |
|---|---|---|
| **Yahoo** (`yfinance`) | Hợp đồng toàn cầu. Nguồn chính cho hầu hết. | USD |
| **vndata.macro.commodity** | Cùng feed với Yahoo cho dầu/vàng/khí, nhưng là nguồn **duy nhất** cho giá VN nội địa: thép VN, vàng SJC, xăng bán lẻ, heo hơi. | USD hoặc VND tuỳ series |
| **akshare** `futures_main_sina` | Hợp đồng liên tục Trung Quốc, ~20 năm. Nguồn **duy nhất** cho cao su (`RU0`), quặng sắt (`I0`), than cốc (`J0`). | CNY |
| **DataPro** (`vndata.price`) | Giá + khối ngoại các mã VN ăn theo hàng hoá. | nghìn VND |

akshare là CNY nên **không tham gia kiểm chéo** — chỉ Yahoo vs vndata (cùng USD) mới so
được. Dùng chuỗi Trung Quốc để đọc backwardation / tồn kho nội địa TQ, đừng so thẳng
với hợp đồng phương Tây.

---

## 3. Bẫy đã kiểm chứng

**Chuỗi chết trả 0 dòng mà không raise.** `vndata.macro.commodity('iron_ore')` và
`('coke')` dừng ở **07/03/2025**. Với `start=2015` chúng trả 1.304 dòng rồi im lặng hết
số — agent sẽ báo "không có dữ liệu" thay vì "nguồn chết". Cả hai route đã **cố ý không
khai** `vndata`, thay bằng Yahoo `TIO=F` + akshare `I0` / `J0`. Đừng "sửa lại cho đủ".

**Không truyền `start=` thì chỉ được ~6 tháng.** `commodity(name)` trần trả ~139 dòng.
`build()` luôn truyền `start=` (mặc định 6 năm).

**`gas` mặc định `market='VN'` là giá xăng bán lẻ**, không phải Henry Hub — cột
`ron95` / `ron92` / `oil_do`, đơn vị nghìn VND/lít. Route `gas` ép `market='GLOBAL'`;
giá xăng nằm ở route riêng `gas_vn`.

**Đường: ba hợp đồng khác nhau, không được trộn.** Yahoo `SB=F` = đường thô #11
(cent/lb, 18,02); vndata `sugar` = đường trắng London (USD/tấn, 523,1); `SR0` = CZCE
(CNY/tấn, 5.437). Chênh trắng–thô là **white premium**, không phải lỗi dữ liệu. Route
`sugar` đặt `crosscheck=False` — nếu không, kiểm chéo báo động giả 2.802% mỗi lần chạy.

**Bar cuối tuần của Yahoo là bản sao thứ Sáu.** Yahoo dán một bar cho ngày cuối tuần
bằng cách lặp lại giá đóng cửa thứ Sáu, trong khi vndata có phiên điện tử thật. So thẳng
bar-cuối-với-bar-cuối vì thế biến chuyện đó thành "lệch nguồn" giả. Đo ngày 07/09/2026
(Chủ nhật 06/09 là bar cuối): `oil_crude` báo lệch 0,52%, `gas` 1,51%, `steel` 1,37% —
tức **3 trong 6** route có kiểm chéo đều báo động giả. Kiểm chéo nay so ở **ngày chung
cuối cùng rơi vào thứ Hai–thứ Sáu**; cùng dữ liệu đó cho 0,00% / 0,17% / 0,00%.

Sau khi sửa, `oil_crude` khớp `CL=F` **đến từng cent ở mọi phiên giao dịch** (0,000%
suốt 28/08–04/09) — đúng như ghi chú route: cùng một feed.

**`macro.currency('exchange_rate')` chết từ 09/07/2026** và bỏ qua `start=`. Tỷ giá
sống lấy từ Yahoo `USDVND=X`. Chi tiết ở `VN_DATA_SOURCE.md` §4.

**`TUSHARE_TOKEN` là placeholder.** Chain `"futures": ["tushare", "akshare"]` của tool
`backtest` chết ở mắt xích đầu. Kéo theo:

**Tool `backtest` không backtest được hợp đồng hàng hoá toàn cầu.**
`akshare_loader._fetch_one()` không có nhánh futures nên `CLF25` rơi xuống
`stock_zh_a_hist()` và fail; còn `CL=F` thì `_detect_market()` rơi về mặc định
`a_share` → dựng `ChinaAEngine` (T+1, biên ±10%, lô 100) cho một hợp đồng dầu. Preset
VN vì thế **chỉ cho backtest trên mã `.VN` với `source: "datapro"`**; không có proxy
thì ghi thẳng "không backtest được".

**Backend `asean-apigw.aseansc.com.vn`** đỡ toàn bộ `vndata.macro` và đã từng chết cả
tiếng (27/08/2026). Yahoo là nguồn thứ hai độc lập — đó là lý do phần lớn route khai
cả hai.

---

## 4. Môi trường Python — đừng nhầm

| | `C:\Users\VVVZV\MatthewTrading\.venv` (**dự án**) | `$HOME\.venv` (home) |
|---|---|---|
| `yfinance` / `akshare` / `tushare` / `ccxt` | ✅ | ❌ |
| vnstock sponsor + `crawl4ai` | ✅ | ✅ |

Data pack và swarm hàng hoá **chỉ chạy được ở venv dự án**. Dùng nhầm `$HOME\.venv` thì
Yahoo và akshare hỏng im lặng, pack còn mỗi vndata.

---

## 5. Quy trình chạy

```bash
.venv/Scripts/python.exe agent/scripts/commodity_datapack.py --list
.venv/Scripts/python.exe agent/scripts/commodity_datapack.py oil_crude
.venv/Scripts/python.exe agent/_run_commodity.py oil_crude --horizon "6 thang"
```

Exit 0 khi còn ít nhất một chuỗi giá sống; exit 1 khi không còn nguồn nào.

Hậu kiểm bắt buộc sau mỗi run:

1. `grep` prompt đã lưu trong `agent/.swarm/runs/<RUN_ID>/` → xác nhận data pack tới
   được worker qua `private_context`.
2. Lấy 5 con số bất kỳ trong `final_report` truy ngược về `datapack.json`. Số nào không
   truy được là agent bịa → siết prompt.
3. Mục 7 (kiểm định lịch sử) phải có kết quả trên mã `.VN` **hoặc** câu "không backtest
   được" — không được để rỗng.
4. Mục 8 (Ánh xạ Việt Nam) phải có độ nhạy định lượng, không được chỉ liệt kê mã.

---

## 6. Các file

| File | Vai trò |
|---|---|
| `agent/scripts/commodity_datapack.py` | `ROUTES` + `build()` + render markdown/JSON |
| `agent/src/swarm/presets/commodity_research_team_VN.yaml` | Preset 3 agent (cung / cầu / chiến lược) |
| `agent/_run_commodity.py` | Runner: đọc `datapack.md` → `private_context` |
| `_commodity_<key>_<YYYYMMDD>/` | Data pack đã dựng (`datapack.md` + `datapack.json`) |

Preset gốc upstream `commodity_research_team.yaml` **giữ nguyên, không sửa** — đúng tiền
lệ `value_investing_committee_VN.yaml`.
