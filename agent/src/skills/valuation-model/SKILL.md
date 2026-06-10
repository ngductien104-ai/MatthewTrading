---
name: valuation-model
description: "Định giá cổ phiếu Việt Nam — định giá tuyệt đối (DCF, DDM, RIM cho ngân hàng, SOTP) và tương đối (PE-Band, PB-ROE, EV/EBITDA), phân tích độ nhạy và nhận diện bẫy định giá. Nguồn dữ liệu vnstock (BCTC) + DataPro (giá/beta)."
category: analysis
---

# Phương pháp định giá cổ phiếu Việt Nam

## Tổng quan

Khung định giá doanh nghiệp có hệ thống, gồm định giá tuyệt đối (`DCF / DDM / RIM / SOTP`) và tương đối (`PE / PB / EV-EBITDA`), kèm phân tích độ nhạy và checklist nhận diện bẫy định giá. Áp cho thị trường Việt Nam.

> ⚠️ **Trước khi tính (checklist Karpathy):** số CP lưu hành = `Company.overview().issue_share` (KHÔNG suy từ EPS); β **tự tính từ DataPro full-history**, nêu cửa sổ + R² (không lấy số cũ trong memory); bóc khoản một lần (lãi tỷ giá/thanh lý/đánh giá lại) trước khi annualize; tính ≥2 cách khi nhạy cảm (ROIC, WACC, Ke).

## Định giá tuyệt đối

### 1. DCF (Chiết khấu dòng tiền tự do)

**Công thức lõi:**

```
Giá trị doanh nghiệp (EV) = Σ FCFF_t / (1+WACC)^t + TV / (1+WACC)^n
Giá trị vốn chủ = EV − Nợ ròng
Giá trị mỗi cổ phần = Giá trị vốn chủ / Số CP lưu hành (issue_share)
```

**Bước 1 — Dự phóng dòng tiền tự do (thường 5 năm):**

```
FCFF = EBIT × (1 − thuế suất) + Khấu hao − Capex − Tăng vốn lưu động
Đơn giản: FCFF ≈ Dòng tiền HĐKD (CFO) − Capex
```

| Năm | Doanh thu (tỷ) | EBIT (tỷ) | FCFF (tỷ) | Tăng trưởng |
|------|---------|---------|---------|------|
| N+1 | 120 | 24 | 18 | +15% |
| N+2 | 138 | 28 | 21 | +15% |
| N+3 | 155 | 31 | 24 | +12% |
| N+4 | 170 | 34 | 26 | +10% |
| N+5 | 182 | 36 | 28 | +7% |

**Bước 2 — Tính WACC:**

```
WACC = E/(D+E) × Ke + D/(D+E) × Kd × (1−T)

Ke (chi phí vốn chủ) = Rf + β × ERP
  - Rf: lợi suất TPCP 10 năm hiện hành (tra cứu; VN ~3-5%)
  - β: TỰ TÍNH từ DataPro full-history (nêu cửa sổ + R²)
  - ERP: phần bù rủi ro VCSH thị trường VN (~7-9%, kiểm chứng)

Kd (chi phí nợ): lãi vay bình quân — đọc thuyết minh BCTC hoặc = chi phí lãi vay / nợ vay bình quân
  (vay ngân hàng có TSĐB ~7-9%, trái phiếu DN ~9-12%, vay khác cao hơn)
T: thuế suất TNDN (phổ thông 20%)
```

**Khoảng WACC tham chiếu theo ngành VN** (kiểm chứng bằng số thật):

| Ngành | Khoảng WACC | β tham chiếu |
|------|---------|------|
| Tiêu dùng | 9-11% | 0,7-1,0 |
| Công nghệ | 11-14% | 1,1-1,4 |
| Bất động sản | 12-15% | 1,1-1,5 |
| Tiện ích (điện/nước) | 8-10% | 0,5-0,8 |
| Thép/Vật liệu (chu kỳ) | 11-14% | 1,0-1,4 |

> Ngân hàng / Chứng khoán / Bảo hiểm: **KHÔNG dùng FCFF/DCF** (lãi vay là đầu vào kinh doanh cốt lõi, FCFF không định nghĩa được) → dùng **RIM / DDM / PB-ROE** (xem mục 3).

**Bước 3 — Giá trị cuối kỳ (Terminal Value):**

```
Tăng trưởng đều (Gordon): TV = FCF_n × (1+g) / (WACC − g)
  - g: tăng trưởng dài hạn (thường 2-4%, không vượt tăng trưởng GDP danh nghĩa)
Bội số thoát: TV = EBITDA_n × bội số EV/EBITDA ngành
```

**Bước 4 — Phân tích độ nhạy:**

```markdown
### Độ nhạy DCF (giá/cổ phần, nghìn đồng)

| WACC \ g | 3,0% | 3,5% | 4,0% |
|----------|------|------|------|
| 11,0% | 32,5 | 35,8 | 40,2 |
| 11,5% | 28,3 | 30,8 | 34,0 |
| 12,0% | 24,8 | 26,7 | 29,1 |
| 12,5% | 22,0 | 23,5 | 25,3 |
| 13,0% | 19,6 | 20,8 | 22,2 |
```

### 2. DDM (Chiết khấu cổ tức)

**Áp dụng:** cổ phiếu cổ tức cao, ổn định (ngân hàng, tiện ích, tiêu dùng trưởng thành).

```
DDM hai giai đoạn:
P = Σ D_t / (1+Ke)^t + D_n × (1+g) / [(Ke−g) × (1+Ke)^n]

Gordon (một giai đoạn): P = D_1 / (Ke − g)
```

**Checklist áp dụng:**
- [x] Trả cổ tức tiền mặt đều >3 năm
- [x] Tỷ lệ chi trả ổn định (>30%)
- [x] Lợi nhuận dễ dự báo
- [ ] Thường không hợp cổ phiếu tăng trưởng cao (không/ít cổ tức)

### 3. RIM (Mô hình Thu nhập Thặng dư) — chuẩn cho NGÂN HÀNG

**Vì sao ngân hàng VN dùng RIM thay vì DCF:** với ngân hàng/CTCK/bảo hiểm, lãi vay (huy động) là **đầu vào kinh doanh cốt lõi** nên FCFF không định nghĩa được; vốn bị ràng buộc bởi **CAR (Thông tư 41 — Basel II, tối thiểu 8%)**; và giá trị sổ sách vốn chủ là thước đo kinh tế đáng tin. RIM định giá phần lợi nhuận tạo ra **vượt trên chi phí vốn chủ**.

**Trực giác:** Giá trị vốn chủ = Vốn chủ sổ sách hiện tại + Hiện giá thu nhập thặng dư tương lai.

**Công thức:**

```
V0 = B0 + Σ_{t=1}^{n} RI_t / (1+Ke)^t + TV / (1+Ke)^n

RI_t (thu nhập thặng dư) = NI_t − Ke × B_{t-1} = (ROE_t − Ke) × B_{t-1}
B_t = B_{t-1} + NI_t − Div_t        (quan hệ "clean surplus": vốn chủ tăng = LN giữ lại)

Terminal:  TV = RI_{n+1} / (Ke − g)              (RI tăng trưởng đều g)
   hoặc (Ohlson, hệ số duy trì ω∈[0,1]):  TV = RI_n × ω / (1 + Ke − ω)
```

**Liên hệ P/B hợp lý (một giai đoạn) — cầu nối với ma trận PB-ROE:**

```
P/B hợp lý = (ROE − g) / (Ke − g)
```

→ RIM là phiên bản nghiêm ngặt, nhiều giai đoạn của PB-ROE.

**Ví dụ minh hoạ (ngân hàng, số giả định):** B0 = 100 (chỉ số), ROE bền vững 15%, Ke 13%, g 4%

| Năm | B đầu kỳ | RI = (ROE−Ke)×B | Hệ số chiết khấu (1/1,13ᵗ) | PV(RI) |
|------|------|------|------|------|
| 1 | 100,0 | 2,00 | 0,885 | 1,77 |
| 2 | 104,0 | 2,08 | 0,783 | 1,63 |
| 3 | 108,2 | 2,16 | 0,693 | 1,50 |
| TV (cuối năm 3) | — | RI₄/(Ke−g) = 2,25/0,09 = 25,0 | 0,693 | 17,33 |
| **Tổng PV thặng dư** | | | | **22,2** |

→ V0 = B0 + 22,2 = **122,2** → **P/B hợp lý ≈ 1,22x** (khớp công thức (ROE−g)/(Ke−g) = (0,15−0,04)/(0,13−0,04)).
*Đọc: ngân hàng ROE bền vững 15%, Ke 13%, g 4% xứng đáng giao dịch quanh 1,22x P/B; cao hơn nhiều = đắt, thấp hơn = rẻ (nếu ROE thật bền).*

**Đặc thù ngân hàng VN khi áp RIM:**
1. **B0 = `owners_equity`** (vnstock CĐKT); NI = `net_profit_loss_after_tax` (hoặc `attributable_to_parent_company` cho phần cổ đông mẹ).
2. **Chuẩn hoá chi phí tín dụng:** ROE hiện tại dễ bị bóp méo bởi trích lập/hoàn nhập dự phòng bất thường → dùng **ROE chuẩn hoá** (bóc one-off trước khi đưa vào RI).
3. **Ràng buộc CAR (TT41):** tăng trưởng vốn chủ g·B bị giới hạn bởi CAR tối thiểu; tốc độ tăng tài sản có rủi ro (RWA) → nhu cầu vốn → giới hạn khả năng chia cổ tức và g bền vững.
4. **Pha loãng:** ngân hàng VN hay tăng vốn (phát hành, cổ tức cổ phiếu) → B và số CP đổi liên tục; dùng `issue_share` THẬT, không suy từ EPS.
5. **Chất lượng tài sản:** NPL (nợ xấu) và LLR (bao phủ nợ xấu) quyết định độ tin của B và NI — B "ảo" nếu dự phòng thiếu. Soi cùng skill `financial-statement`.

### 4. SOTP (Định giá từng phần)

**Áp dụng:** tập đoàn đa ngành (vd Masan, Vingroup, FPT-đa mảng).

```
Giá trị tập đoàn = Σ định giá từng mảng + tiền ròng − chiết khấu holding

Ví dụ (tập đoàn đa ngành):
| Mảng | Doanh thu (tỷ) | Phương pháp | Định giá (tỷ) |
|------|---------|---------|---------|
| Bán lẻ tiêu dùng | 80 | 18x P/E | 600 |
| Bất động sản | 50 | 0,8x P/B | 120 |
| Tài chính/ngân hàng | 30 | RIM / 1,2x P/B | 200 |
| Tổng | | | 920 |
| Chiết khấu holding | | −15% | −138 |
| Định giá tập đoàn | | | 782 |
```

## Định giá tương đối

### 1. PE Band

```
Phân vị PE lịch sử 5 năm (PE_TTM): tính phân vị 10/25/50/75/90%
Đối chiếu PE hiện tại với phân vị để đánh giá đắt/rẻ

| Phân vị | PE | Giá hàm ý | Diễn giải |
|------|-----|---------|------|
| 90% | 35x | 52,5 | Rất đắt |
| 75% | 28x | 42,0 | Đắt |
| 50% | 22x | 33,0 | Hợp lý |
| 25% | 16x | 24,0 | Rẻ |
| 10% | 12x | 18,0 | Rất rẻ |
| Hiện tại | 18x | 27,0 | Rẻ (phân vị ~30%) |
```

### 2. Ma trận PB-ROE

```
Quan hệ lý thuyết: P/B = (ROE − g) / (Ke − g)   (chính là RIM một giai đoạn)
Thực hành: vẽ các DN cùng ngành lên đồ thị PB (trục tung) vs ROE (trục hoành)

| Góc phần tư | PB | ROE | Diễn giải |
|------|-----|-----|------|
| Dưới-phải | PB thấp | ROE cao | Định giá thấp (vùng mua tốt nhất) |
| Trên-phải | PB cao | ROE cao | Hợp lý (phần bù chất lượng) |
| Dưới-trái | PB thấp | ROE thấp | Bẫy giá trị hoặc đang tái cấu trúc |
| Trên-trái | PB cao | ROE thấp | Định giá cao (tránh) |
```

### 3. EV/EBITDA

```
EV = Vốn hoá + Nợ ròng (nợ vay có lãi − tiền & tương đương tiền)
EBITDA = LN hoạt động + Khấu hao

Ưu điểm: loại khác biệt cấu trúc vốn (vs PE), loại khác biệt chính sách khấu hao
Hợp DN tài sản nặng (điện/dầu khí/hạ tầng). KHÔNG dùng cho ngân hàng.

Khoảng EV/EBITDA tham chiếu theo ngành VN:
| Ngành | Trung vị | Rẻ | Đắt |
|------|--------|------|------|
| Tiêu dùng | 10-15x | <8x | >20x |
| Công nghệ | 10-16x | <8x | >20x |
| Năng lượng/Điện | 6-10x | <5x | >12x |
| Tiện ích | 7-11x | <6x | >14x |
```

## Nhận diện bẫy định giá

### 10 bẫy định giá phổ biến

| # | Bẫy | Cách phát hiện | Ví dụ điển hình |
|---|------|---------|---------|
| 1 | PE thấp đỉnh chu kỳ | PE thấp nhất khi LN cao nhất sắp đảo chiều | Thép/hoá chất P/E 5x ở đỉnh chu kỳ |
| 2 | PE cao có thể hợp lý | `PEG < 1` nghĩa là tăng trưởng đỡ được định giá | P/E 30x + tăng 40% = PEG 0,75 |
| 3 | PB thấp huỷ hoại giá trị | `ROE < Ke` kéo dài = huỷ hoại giá trị cổ đông | DN tài sản nặng lỗ triền miên |
| 4 | Bom lợi thế thương mại | Lợi thế TM/vốn CSH >30% → rủi ro tổn thất | Thâu tóm giá cao rồi dưới kỳ vọng |
| 5 | Bẫy phải thu | Phải thu/doanh thu tăng = chất lượng doanh thu kém | Phải thu Nhà nước + tập trung khách hàng |
| 6 | Bẫy vốn hoá chi phí | Vốn hoá lãi vay/chi phí PT thổi lợi nhuận | PE tăng gấp đôi sau khi ghi nhận đúng |
| 7 | Lãi một lần | Chênh lớn giữa LN cốt lõi và LN báo cáo | Thanh lý tài sản/đánh giá lại/tỷ giá |
| 8 | Pha loãng cổ phiếu | ESOP/trái phiếu chuyển đổi/tăng vốn bào EPS | PE nên tính trên EPS pha loãng & issue_share thật |
| 9 | Giao dịch bên liên quan | Mua rẻ/bán đắt với bên liên quan | Chuyển lợi nhuận ra ngoài DN niêm yết |
| 10 | Biến động tỷ giá | Tỷ trọng doanh thu/nợ ngoại tệ cao | VND mất giá bào lợi nhuận DN nhập khẩu/vay USD |

## Khung phân tích

### Cây quyết định chọn phương pháp

```
DN thuộc loại nào?
├── Ngân hàng / Chứng khoán / Bảo hiểm
│   └── RIM + PB-ROE + DDM   (KHÔNG dùng DCF/EV-EBITDA)
├── Trưởng thành, ổn định (tiêu dùng / tiện ích)
│   ├── Cổ tức cao → DDM
│   └── Cổ tức thấp → DCF + PE Band
├── Tăng trưởng cao (công nghệ / bán lẻ mới)
│   └── DCF (giai đoạn tăng trưởng) + PEG + P/S
├── Chu kỳ (thép / hoá chất / BĐS)
│   └── PB + EV/EBITDA (tránh PE) + LN chuẩn hoá giữa chu kỳ
├── Tập đoàn đa ngành
│   └── SOTP
└── DN đang lỗ
    └── P/S + EV/Sales
```

### Kiểm chứng chéo

```
Dùng ít nhất 2 phương pháp và lấy vùng giá trị giữa:
1. DCF/RIM → giá trị nội tại
2. So sánh PE/PB ngành → định giá thị trường
3. Lệch >30% → soát lại tính hợp lý của giả định
```

## Mẫu output

```markdown
## Phân tích định giá: [Tên DN / Mã .VN]

### Tóm tắt định giá
| Phương pháp | Giá/cổ phần | Trọng số | Ghi chú |
|------|---------|------|------|
| DCF / RIM | 32,5 | 50% | WACC=12%, g=3% (hoặc Ke=13%, ROE=15%) |
| So sánh PE | 28,0 | 30% | PE ngành 18x, EPS=1,55 |
| PB-ROE | 30,0 | 20% | PB hợp lý 1,5x |
| **Giá mục tiêu tổng hợp** | **30,8** | | Giá hiện tại 25,0, tiềm năng +23% |

### Phân tích độ nhạy
[ma trận WACC×g hoặc Ke×g]

### Soát bẫy định giá
- [x] PE thấp giả tạo đỉnh chu kỳ → Không
- [x] Lợi thế TM/vốn CSH → 12%, an toàn
- [x] Phải thu/doanh thu → Ổn định
- [!] Chênh LN cốt lõi vs báo cáo → 15%, lệ thuộc khoản một lần, cần lưu ý

### Khuyến nghị: MUA
Giá mục tiêu 30,8 nghìn đồng, giá hiện tại 25,0 nghìn đồng, tiềm năng +23%
```

## Lưu ý

1. **DCF/RIM rất nhạy với giả định:** WACC/Ke đổi 1% có thể dịch định giá 20%+ → phân tích độ nhạy là bắt buộc; tính ≥2 cách (checklist Karpathy).
2. **DN so sánh phải thật sự so được:** cùng ngành + cùng quy mô + cùng giai đoạn; đừng áp bội số của DN đầu ngành cho DN nhỏ.
3. **Định giá ≠ giá mục tiêu giao dịch:** thị trường có thể phi lý dài; định giá là điểm neo, không phải tín hiệu mua/bán tức thời.
4. **DN chu kỳ:** dùng LN chuẩn hoá (giữa chu kỳ), không dùng LN hiện tại.
5. **Ngân hàng:** ưu tiên RIM/PB-ROE; chú ý NPL/LLR/CAR và pha loãng; không dùng DCF/EV-EBITDA.
6. **Không hợp tiền mã hoá:** dùng on-chain (xem `onchain-analysis`).

## Nguồn dữ liệu

- **BCTC → vnstock** (`source="VCI"`, `lang="vi"`): `income_statement` / `balance_sheet` / `cash_flow`. Item_id thường dùng cho định giá: `net_sales`, `gross_profit`, `net_profit_loss_after_tax`, `attributable_to_parent_company`, `owners_equity` (B0 cho RIM), `total_assets`, `short_term_borrowings`, `long_term_borrowings`, `cash_and_cash_equivalents` (cho nợ ròng), `net_cash_inflows_outflows_from_operating_activities` (CFO cho FCFF).
- **Giá / vốn hoá → DataPro** (`source="datapro"`, mã `.VN`): giá đóng cửa × `issue_share` = vốn hoá.
- **β → tự tính từ DataPro full-history** (regress lợi suất cổ phiếu vs VNINDEX), nêu cửa sổ + R².
- **Số CP lưu hành → `Company.overview().issue_share`** (không suy từ EPS).
- ⚠️ Endpoint `ratio()` của vnstock community trả layout kỳ KHÔNG ổn định → tự tính P/E, P/B, ROE từ giá + BCTC thay vì lấy trực tiếp. Bản community chỉ ~4 kỳ năm gần nhất.
