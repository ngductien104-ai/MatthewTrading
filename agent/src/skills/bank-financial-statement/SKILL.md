---
name: bank-financial-statement
description: "Phân tích BCTC chuyên sâu NGÂN HÀNG TMCP Việt Nam (buy-side) — earnings quality (PPOP vs PBT, NIM tách yield−CoF, forensics lãi dự thu), rủi ro tài sản forward-looking (nợ nhóm 2/3/4/5, tỷ lệ hình thành nợ xấu, coverage, thời vụ, cho vay theo ngành, related-party hệ sinh thái), thanh khoản & vốn (CASA/LDR/CAR/internal capital generation). Routing: tự tính từ BCTC gốc PDF (evidence_pack.py); NIM/NPL/coverage/LDR/chi phí tín dụng lấy VNDIRECT MCP get_ratios rồi cross-check công bố IR, CASA/CAR lấy IR/BCTC; nợ nhóm 2/3/4/5, cho vay theo ngành, related-party vẫn phải crawl4ai từ thuyết minh; cross-check ≥2 nguồn + môi giới ≤3 tháng. KHÔNG định giá (task riêng)."
category: analysis
---

# Phân tích BCTC Ngân hàng TMCP Việt Nam (buy-side · Financial Analyst)

## Vai trò & mục đích
Senior buy-side Financial Analyst (CFA, 10y+), chuyên ngành ngân hàng VN. Bóc **chất lượng lợi nhuận thật, rủi ro bảng cân đối, sức khỏe vốn/thanh khoản** qua 3 BCTC. **Chỉ phân tích tài chính — KHÔNG định giá** (định giá là skill/task riêng). Số bề mặt (NPL 1,1%) KHÔNG phải kết luận → phải tới **driver & xu hướng**.

**Khi nào dùng:** ICB cấp 2 = `8300` (`vndata.reference.classification()`). Mẫu BCTC ngân hàng khác DN thường: có **Thu nhập lãi thuần / Tổng thu nhập hoạt động / trích lập dự phòng**, KHÔNG có doanh thu/giá vốn/tồn kho. Securities/insurance dùng template riêng.

---

## 1. ROUTING DỮ LIỆU (BẮT BUỘC theo — nguồn đổi 13/11/2026)

> vnstock đã huỷ. Ngân hàng có **hai tầng nguồn**, không API nào thay được tầng 1:
> **Tầng 1 = BCTC gốc PDF** (dòng chi tiết + thuyết minh), **Tầng 2 = chỉ số
> VNDIRECT MCP** (`FINFO_API__get_ratios`). Bảng tool đầy đủ: skill `data-routing`.

### Tầng 1 — TỰ TÍNH từ BCTC gốc ✅ tin cậy nhất

```bash
./.venv/Scripts/python.exe agent/scripts/evidence_pack.py TCB --outdir _tcb_research --auto
```

Đọc KQKD + CĐKT (ưu tiên bản **soát xét bán niên / kiểm toán năm**), ghi từng số
kèm **trang** vào `FACTS.md`. Dòng cần lấy (mẫu B02/B03 TCTD):

| Dòng cần | Trên BCTC TCTD |
|---|---|
| NII | Thu nhập lãi thuần |
| Lãi thuần dịch vụ (fee) | Lãi thuần từ hoạt động dịch vụ |
| KD ngoại hối / CK kinh doanh / CK đầu tư | Lãi/lỗ thuần từ các hoạt động tương ứng |
| **TOI** | Tổng thu nhập hoạt động |
| Opex | Chi phí hoạt động |
| **PPOP** | LN thuần từ HĐKD trước chi phí dự phòng rủi ro tín dụng |
| Trích lập dự phòng | Chi phí dự phòng rủi ro tín dụng |
| PBT / NPAT / NPAT mẹ / CĐTS | Tổng LNTT / LNST / LN của cổ đông NH mẹ / lợi ích CĐTS |
| Tổng TS / VCSH / Vốn điều lệ | Tổng tài sản / Vốn chủ sở hữu / Vốn của TCTD |
| Cho vay KH (gross / dự phòng) | Cho vay khách hàng / Dự phòng rủi ro cho vay KH |
| Tiền gửi KH | Tiền gửi của khách hàng |
| **Lãi & phí phải thu** (forensic) | Các khoản lãi, phí phải thu |
| Chứng khoán đầu tư | Chứng khoán đầu tư (tách TPDN ở thuyết minh) |

**Khớp số bắt buộc trước khi dùng** (mẫu đã verify trên TCB 2025):
`PPOP 36.959 − dự phòng 4.421 = PBT 32.538` ✓ · `NPAT 25.954 = mẹ 25.290 + CĐTS 664` ✓ ·
`Vốn điều lệ 70.862 tỷ = 7,086 tỷ CP × 10.000đ` ✓ · `CIR = (53.391−36.959)/53.391 = 30,8%` ✓.

**Công thức (tự tính, kiểm soát định nghĩa):**
```
ROAA = NPAT / bình quân Tổng TS          ROAE = NPAT mẹ / bình quân VCSH
NIM proxy = NII / bình quân Tổng TS       (NIM THỰC dùng TS sinh lãi → so NET_INTEREST_MARGIN_TR_AVG5Q)
CIR = (TOI − PPOP) / TOI                  Credit cost = Provision / bình quân Cho vay
LDR thuần = Cho vay / Tiền gửi            LLR/loans = Dự phòng / Cho vay gross
Non-II/TOI, Fee/TOI ; PPOP growth vs PBT growth (chênh = "vay" LN từ trích lập)
Lãi dự thu/Tổng TS  → nếu tăng nhanh hơn NII = nghi lãi ảo
BVPS = VCSH / số CP ; P/B, P/E từ VNDIRECT PRICE_TO_BOOK / PRICE_TO_EARNINGS
```
Số CP: `OUTSTANDING_SHARES`; room ngoại: `FINFO_API__get_foreign_trading` (`totalRoom`/`currentRoom`).

### Tầng 1b — QUÝ (BẮT BUỘC — luôn tính thêm quý vừa công bố) ✅
> Phân tích FY là CHƯA ĐỦ. Quý gần nhất thường đảo chiều xu hướng FY (vd TPB: FY2025 nợ xấu "đẹp" 1,29% nhưng **Q1/2026 bật lại 1,85%**). Luôn kéo & tính quý mới nhất.

- Lấy BCTC quý gần nhất từ PDF; YoY/QoQ nhanh có sẵn ở VNDIRECT:
  `NET_PROFIT_QR_GRYOY`, `NET_PROFIT_QR_GRQOQ`, `OPERATING_INCOME_QR_GRYOY`,
  `CUSTOMER_LOANS_AQ_GRYOY` / `_GRYTD` (`get_ratios(q="code:TCB~reportDate:2026-09-30")`).
- Tính QoQ, YoY, run-rate và trailing-4Q so với FY; CĐKT cuối quý (cho vay, tiền
  gửi → growth YTD, LDR, LLR/loans, lãi & phí phải thu).
- Headline quý phải đối chiếu **công bố KQKD công ty + cafef** trước khi báo ra ngoài.

### Tầng 2 — CHỈ SỐ NGÂN HÀNG TỪ VNDIRECT (`FINFO_API__get_ratios`)

| Chỉ tiêu | `ratioCode` |
|---|---|
| NIM | `NET_INTEREST_MARGIN_TR_AVG5Q` |
| Nợ xấu / nợ quá hạn | `BAD_LOANS_RATIO_AQ` / `OVERDUE_LOANS_RATIO_AQ` |
| Bao phủ nợ xấu | `PROVISION_BAD_LOANS_AQ` (VCB 2,43 = 243%) |
| LDR | `LOANS_TO_DEPOSIT_AQ` |
| Chi phí tín dụng | `DOUBTFUL_EXPENSES_TO_LOANS_TR_AVG5Q` |
| Cơ cấu thu nhập | `INTEREST_INCOME_RATIO_TR`, `NON_INTEREST_INCOME_RATIO_TR`, `NET_SERVICE_INCOME_RATIO_TR` |
| Tăng trưởng tín dụng | `CUSTOMER_LOANS_AQ_GRYOY`, `CUSTOMER_LOANS_AQ_GRYTD` |
| ROAE / ROAA | `ROAE_TR_AVG4Q`, `ROAA_TR_AVG4Q` |
| Định giá | `PRICE_TO_BOOK`, `PRICE_TO_EARNINGS`, `PRICE_TO_BOOK_AVG_CR_{1Y,3Y,5Y}` |

**Bẫy khi đọc (đo VCB 30/09/2026):** tỷ lệ là **phân số** (NPL 0,00706 = 0,71%)
→ nhân 100 khi trình bày; `EBITDA_TR` / `EBIT_TR` của ngân hàng **không có nghĩa**
(VCB `EBITDA_TR` âm) → cấm dùng; NIM là **bình quân 5 quý**, không phải NIM quý.
**VNDIRECT KHÔNG có CASA, CAR, YOEA/COF tách riêng** → tầng 1 / IR / Basel III.

**Vẫn PHẢI lấy ngoài** (API không có), thứ tự ưu tiên:
1. **Công bố KQKD của ngân hàng (IR press release PDF)** — **nợ nhóm 2**, **split
   nhóm 3/4/5**, **tỷ lệ hình thành nợ xấu**, CAR theo Basel II/III do NH tự công bố.
2. **BCTC + thuyết minh** (crawl4ai/PDF): phân loại nợ nhóm 1–5 (note "Phân tích
   chất lượng nợ cho vay"), **cho vay theo ngành**, **giao dịch bên liên quan**,
   TPDN, LDR quy định, vốn ngắn hạn cho vay trung–dài hạn.
3. **Báo cáo môi giới ≤3 THÁNG** (SSI/HSC/VCI/MBS/VND) — cross-check + chỉ tiêu
   phái sinh. **Bỏ báo cáo cũ hơn 3 tháng.**

> Chênh giữa chỉ số VNDIRECT và công bố IR là chuyện bình thường (định nghĩa khác:
> cuối kỳ vs bình quân, hợp nhất vs riêng lẻ). **Lệch → nêu cả hai và nói rõ dùng
> số nào, không chọn bừa.**

### Tầng 3 — CROSS-CHECK (bắt buộc ≥2 nguồn)
cafef.vn / vietstock.vn đối chiếu mọi số tầng 1–2. **Quý gần nhất:** headline quý vẫn phải đối chiếu **công bố công ty + cafef** trước khi báo ra ngoài. Mâu thuẫn nguồn → **nêu rõ, không chọn bừa** (vd NPL: PR 0,96% vs BCTC 1,29% → dùng số BCTC).

**Công cụ:** `WebFetch`/`WebSearch` cho PR/bài báo; **crawl4ai** cho bảng cafef render + trang JS; `pdfplumber` đọc PDF text (PR/môi giới/BCTN); PDF scan kiểm toán → `pypdf` trích ảnh + `Read` (vision) [[workflow-deep-dive-equity-analysis]].

---

## 2. KHUNG PHÂN TÍCH (theo `_FRAMEWORK_FINANCIAL_ANALYSIS_NGANHANG.md`)

### 0. Nhận diện & mô hình KD
Quy mô, **hệ sinh thái** (TCB–Vingroup/Masterise; MBB–Viettel; VPB–consumer; HDB–HD Saison; STB–tái cơ cấu), mô hình (bán lẻ/bán buôn/"NH BĐS"), công ty con trọng yếu (TCBS/FE Credit/MCredit), **trạng thái room tín dụng** (nhóm nhận chuyển giao bắt buộc MBB/VCB/HDB/VPB được room cao). → chọn đối chứng đúng.

### I. Lợi nhuận & chất lượng lợi nhuận
- **Bóc Non-II**: phí thanh toán/thẻ · bancassurance · FX · **lãi chứng khoán (volatile)** · **thu hồi nợ đã xử lý** · thu khác → bền vs one-off.
- **NIM tách yield − CoF** (asset mix, CASA→CoF, repricing); so trailing-12M vs spot quý (bắt đảo chiều).
- **PPOP growth vs PBT growth**: chênh lớn = LN nhờ giảm trích lập, không phải core.
- **Operating leverage**: TOI vs opex growth, CIR & cấu phần; cảnh báo cắt chi phí bất thường (đẩy CIR ảo).
- **Forensic**: **lãi & phí phải thu** tăng nhanh hơn NII = lãi dự thu ảo (chỉ tiêu số 1); thu khác đột biến; thuế suất bất thường.
- → **Earnings power chuẩn hóa** = PPOP − credit cost through-cycle − one-off.

### II. Chất lượng tài sản & rủi ro BCĐKT ⭐ TRỌNG TÂM
- **X-quang sổ vay**: tín dụng vs room; theo KH (KHDN lớn/SME/bán lẻ); **theo ngành** (chủ đầu tư BĐS/mua nhà/xây dựng/SX/tiêu dùng); kỳ hạn (TDH%); TPDN nắm giữ.
- **Forward-looking** (khác associate): **nợ nhóm 2 (leading)** · **% nhóm 5 trong NPL** · **tỷ lệ hình thành nợ xấu** (chỉ báo xu hướng số 1) · roll-rate · **phân tích thời vụ** (NPL giảm Q4 do xử lý/tái cơ cấu rồi tăng lại Q1-Q3?) · write-off & recovery · **TT02/06/31** (nợ tái phân loại nhóm 1, nợ tái cơ cấu treo).
- **Bộ đệm**: coverage (LLCR) vs peer & tính biến động; credit cost vs formation rate (đệm đủ hấp thụ?).
- **Concentration & related-party hệ sinh thái** (top-20, TPDN/dư nợ bên liên quan) · LTV TSĐB · **phải thu/tài sản Có khác bất thường** · off-B/S (bảo lãnh/LC).

### III. Nguồn vốn / thanh khoản / vốn
- CASA (bền hay nhờ KM?) & CD share → CoF; **LDR reg (trần 85%) vs thuần**; **vốn NH cho vay TDH (trần 30%)**; **vốn liên NH/nợ** (nhạy lãi suất); maturity wall GTCG.
- **CAR** (Basel II/III), RWA density; **internal capital generation = ROE×(1−payout) vs tăng RWA** (tăng trưởng có cần tăng vốn?); đòn bẩy TS/VCSH.

### IV. "Cash-flow health" cho NH (bỏ FCF)
Lãi dự thu vs thu thật · recovery thật · internal capital generation · cân đối huy động ròng vs giải ngân ròng.

---

## 3. ĐẦU RA (OUTPUT) — FORMAT CHUẨN (theo đúng 6 mục)

### 1. Financial Health Score — điểm tổng hợp **1–10**
- Trọng số ĐỀU 3 trụ: **Earnings / Assets / Cash-flow health** (NH: trụ 3 = funding–liquidity–capital, bản điều chỉnh cho ngân hàng) — nêu lý do từng trụ.
- **+ Điểm nhấn KQKD quý gần nhất:** **bảng tóm tắt chỉ tiêu chính của quý** (NII · fee · TOI · Opex · PPOP · provision · PBT · NPAT — **QoQ & YoY**) + **nhận xét khi có thay đổi quan trọng** (bóc core vs one-off; quý gần nhất XÁC NHẬN hay ĐẢO CHIỀU xu hướng FY).

### 2. Earnings Quality Judgment — nhãn **"high quality / moderate / questionable"** + lý do lõi
(PPOP growth vs PBT growth; NIM bền; **forensic lãi dự thu**; one-off/cắt chi phí một-lần; chất lượng non-II).

### 3. Financial Risk Warnings — **3–5 rủi ro**, mỗi cái có **NGUỒN rủi ro + MỨC ĐỘ ĐỊNH LƯỢNG**. BẮT BUỘC nêu rõ:
- **Nợ nhóm 2 & tỷ lệ nợ xấu (NPL) cuối FY — so với cùng kỳ năm trước.**
- **Tỷ lệ bao phủ nợ xấu (coverage) tại QUÝ GẦN NHẤT — so với cùng kỳ & so với đầu năm.**
- **Chi phí tín dụng (credit cost) cả năm — so với cùng kỳ.**
- (+ rủi ro khác: NIM nén, thanh khoản/LDR/huy động, tập trung ngành/BĐS, related-party…) — định lượng tác động (vd "đưa coverage về 90% → cần trích thêm X tỷ ≈ Y% PPOP").

### 4. Key Financial Metrics Table — xu hướng **3 năm (+ quý gần nhất)**
Cột bắt buộc: **NIM · NPL ratio · CAR · CASA · LDR · CIR · LLR/credit cost · provision coverage · ROE · ROA · P/B**.
(Bổ sung tùy mã: NII/Non-II/TOI/PPOP/PBT/NPAT, nợ nhóm 2, nhóm 5%, formation rate, tăng trưởng tín dụng/huy động, lãi&phí phải thu/TS.)

### 5. Improvement / Deterioration Signals — thay đổi đáng kể **1–2 năm** (+ quý gần nhất), đánh giá **hướng xu thế** + **earnings power chuẩn hóa** (bàn giao task Định giá).

### 6. Peer Comparison — chỉ tiêu chính **vs trung bình ngành / NH dẫn đầu** (ROE · NIM · CASA · coverage · CAR · P/B). Đặt nền cho hồi quy P/B–ROE ở bước định giá — **KHÔNG định giá ở đây**.

---

## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)
1. **Không bịa/cook số liệu.** Mọi số phải có nguồn thật. **Cross-check ≥2 nguồn uy tín** (cafef.vn, vietstock.vn) — crawl4ai cào rồi đối chiếu; nguồn lệch thì nêu rõ, không chọn bừa.
2. **Chỉ số ngân hàng VNDIRECT** (`FINFO_API__get_ratios`) cho NIM/NPL/coverage/LDR/chi phí tín dụng (phân số — nhân 100), nhưng **vẫn cross-check công bố IR**; CASA/CAR KHÔNG có trong VNDIRECT. Riêng **nợ nhóm 2, split nhóm 3/4/5, hình thành nợ xấu, cho vay theo ngành, related-party** thì API KHÔNG có → **BẮT BUỘC** lấy từ công bố IR + BCTC thuyết minh (crawl4ai), cross-check môi giới **≤3 tháng**.
3. **Khoản bất thường → đọc THUYẾT MINH** (nợ nhóm 3/4/5, cho vay theo ngành, related-party, lãi dự thu, TPDN) và trích nguồn trước khi diễn giải.
4. **Báo cáo môi giới chỉ dùng nếu ≤3 tháng tuổi** (cũ hơn = giả định lạc hậu, không làm neo).
