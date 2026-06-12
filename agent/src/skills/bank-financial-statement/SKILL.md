---
name: bank-financial-statement
description: "Phân tích BCTC chuyên sâu NGÂN HÀNG TMCP Việt Nam (buy-side) — earnings quality (PPOP vs PBT, NIM tách yield−CoF, forensics lãi dự thu), rủi ro tài sản forward-looking (nợ nhóm 2/3/4/5, tỷ lệ hình thành nợ xấu, coverage, thời vụ, cho vay theo ngành, related-party hệ sinh thái), thanh khoản & vốn (CASA/LDR/CAR/internal capital generation). Routing: tự tính từ vnstock income+balance; NPL/CASA/CAR/coverage lấy từ công bố IR + crawl4ai (vnstock ratio LỖI THỜI), cross-check ≥2 nguồn + môi giới ≤3 tháng. KHÔNG định giá (task riêng)."
category: analysis
---

# Phân tích BCTC Ngân hàng TMCP Việt Nam (buy-side · Financial Analyst)

## Vai trò & mục đích
Senior buy-side Financial Analyst (CFA, 10y+), chuyên ngành ngân hàng VN. Bóc **chất lượng lợi nhuận thật, rủi ro bảng cân đối, sức khỏe vốn/thanh khoản** qua 3 BCTC. **Chỉ phân tích tài chính — KHÔNG định giá** (định giá là skill/task riêng). Số bề mặt (NPL 1,1%) KHÔNG phải kết luận → phải tới **driver & xu hướng**.

**Khi nào dùng:** `Company.overview().is_bank == True` (hoặc com_type_code='NH'). Mẫu BCTC ngân hàng khác DN thường: có **Thu nhập lãi thuần / Tổng thu nhập hoạt động / trích lập dự phòng**, KHÔNG có doanh thu/giá vốn/tồn kho. Securities/insurance dùng template riêng.

---

## 1. ROUTING DỮ LIỆU (đã audit — BẮT BUỘC theo)

### Tầng 1 — TỰ TÍNH từ vnstock `income_statement` + `balance_sheet` (VCI, ~4 năm) ✅ tin cậy
Pull: `Vnstock().stock(symbol=SYM, source='VCI').finance.income_statement(period='year', lang='vi')` (và `balance_sheet`). Khớp dòng bằng `item.str.contains(...)`:

| Dòng cần | Chuỗi khớp `item` |
|---|---|
| NII | `Thu nhập lãi thuần` |
| Thu nhập lãi gộp / chi phí lãi | `Thu nhập lãi và các khoản thu nhập tương tự` / `Chi phí lãi` |
| Lãi thuần dịch vụ (fee) | `Lãi/Lỗ thuần từ hoạt động dịch vụ` |
| Lãi KD ngoại hối / chứng khoán | `...kinh doanh ngoại` / `...mua bán chứng khoán` |
| TOI | `Tổng thu nhập hoạt động` |
| Opex | `Chi phí quản lý doanh nghiệp` (âm) |
| **PPOP** | `Lợi nhuận thuần hoạt động trước khi trích` |
| Trích lập dự phòng | `Trích lập dự phòng tổn thất tín dụng` (âm) |
| PBT / NPAT / NPAT mẹ | `Tổng lợi nhuận/lỗ trước thuế` / `Lợi nhuận sau thuế` / `Cổ đông của Công ty mẹ` |
| Tổng TS / VCSH / Vốn điều lệ | `TỔNG TÀI SẢN` / `VỐN CHỦ SỞ HỮU` / `Vốn điều lệ` |
| Cho vay KH (gross) / LLR | `Cho vay khách hàng` / `Dự phòng rủi ro cho vay khách hàng` (âm) |
| Tiền gửi KH | `Tiền gửi của khách hàng` |
| **Lãi & phí phải thu** (forensic) | `Các khoản lãi và phí phải thu` |
| Chứng khoán đầu tư / TPDN-proxy | `Chứng khoán đầu tư` |

**Công thức (tự tính, kiểm soát định nghĩa):**
```
ROAA = NPAT / bình quân Tổng TS          ROAE = NPAT mẹ / bình quân VCSH
NIM proxy = NII / bình quân Tổng TS       (NIM THỰC dùng TS sinh lãi → lấy ngoài; proxy thấp hơn ~0,3-0,4đ%)
CIR = -Opex / TOI                         Credit cost = -Provision / bình quân Cho vay
LDR thuần = Cho vay / Tiền gửi            LLR/loans = -LLR / Cho vay
Non-II/TOI, Fee/TOI ; PPOP growth vs PBT growth (chênh = "vay" LN từ trích lập)
Lãi dự thu/Tổng TS  → nếu tăng nhanh hơn NII = nghi lãi ảo
BVPS = VCSH / số CP ; EPS = NPAT mẹ / số CP ; P/B,P/E = market_cap (overview) / VCSH,NPAT mẹ
```
Số CP / market_cap / target / room ngoại / rating: `company.overview()` (`issue_share`,`market_cap`,`target_price`,`rating_as_of`,`foreigner_percentage`,`maximum_foreign_percentage`).

### Tầng 1b — QUÝ GẦN NHẤT (BẮT BUỘC — luôn tính thêm quý vừa công bố) ✅
> Phân tích FY là CHƯA ĐỦ. Quý gần nhất thường đảo chiều xu hướng FY (vd TPB: FY2025 nợ xấu "đẹp" 1,29% nhưng **Q1/2026 bật lại 1,85%**). Luôn kéo & tính quý mới nhất.

Pull `income_statement(period='quarter', lang='vi')` + `balance_sheet(period='quarter', lang='vi')` (source='VCI'): trả **4 quý gần nhất, nhãn ĐÚNG** dạng `2026-Q1, 2025-Q4, 2025-Q3, 2025-Q2`.
> ⚠️ Nhãn quý **chỉ chuẩn ở source VCI**; **KBS dán nhãn lệch** (Q4→Q1) → dùng VCI cho quý. Vẫn cross-check headline quý với **công bố KQKD công ty + cafef**.

Tính cho quý gần nhất: P&L (NII/fee/TOI/PPOP/provision/PBT/NPAT) **QoQ** (vs quý liền trước có trong 4 quý) + **run-rate/annualize** & **trailing-4Q** so với FY; BCĐKT cuối quý (cho vay, tiền gửi → **growth YTD**, LDR thuần, LLR/loans, **lãi & phí phải thu** xu hướng).

**QUÝ CÙNG KỲ NĂM TRƯỚC (cho YoY) — CÀO bằng crawl4ai (vnstock chỉ trả 4 quý, thiếu quý này):**
Để có cơ sở tự tính YoY cho **mọi dòng** (không chỉ headline PR nêu), **cào nguyên BCTC quý cùng kỳ năm trước** từ (ưu tiên theo thứ tự, cross-check ≥2):
1. **cafef.vn**: `s.cafef.vn/bao-cao-tai-chinh/<MÃ>/IncSta/<năm>/<quý>/0/0/<slug>.chn` (KQKD; slug = `ket-qua-hoat-dong-kinh-doanh-<ten-cty>`), và `/BSheet/...` (cân đối). Parse bảng bằng `pandas.read_html`; nhãn cột regex `Quý\s*\d-\s*\d{4}`.
2. **vietstock.vn**: `finance.vietstock.vn/<MÃ>/...` (BCTC theo quý).
3. **Website IR công ty** (press release/BCTC quý đó) — vd `techcombank.com/.../`, `tpb.vn/nha-dau-tu/bao-cao-tai-chinh`.
→ Lấy quý cùng kỳ (vd để đánh giá **2026-Q1** thì cào **2025-Q1**), tự tính **YoY** từng dòng, **cross-check** số YoY mình tính với %YoY công bố trong PR (lệch → nêu rõ).
> NPL/nợ nhóm/CASA/CAR/coverage **cuối quý** lấy từ tầng 2 (công bố/thuyết minh quý).

### Tầng 2 — LẤY NGOÀI (vnstock `ratio` LỖI THỜI cho bank → KHÔNG dùng)
> ⚠️ Đã verify: `finance.ratio()` community trả số **vintage ~2018–2019, mislabel year** (vd TCB ROE 21-25%/NPL 2% trong khi thực tế 2025 là 15,4%/1,13%). **Tuyệt đối không lấy NPL/CASA/CAR/NIM/coverage từ vnstock ratio.**

Các chỉ tiêu sau **PHẢI** lấy từ nguồn ngoài (thứ tự ưu tiên):
1. **Công bố KQKD chính thức của ngân hàng (IR press release PDF)** — nguồn TỐT NHẤT, có sẵn: **NPL, nợ nhóm 2, CASA, CAR (Basel II/III), NIM, coverage/LLCR, ROE/ROA, tăng trưởng tín dụng/huy động**. URL mẫu: `techcombank.com/.../fy25-press-release-vie.pdf`, `1q26-press-release-vie.pdf`; TPB `tpb.vn/nha-dau-tu/bao-cao-tai-chinh`.
2. **BCTC + thuyết minh** (crawl4ai/PDF) cho granular: **phân loại nợ nhóm 1/2/3/4/5** (note "Phân tích chất lượng nợ cho vay"), **cho vay theo ngành**, **giao dịch bên liên quan**, TPDN, LDR quy định, vốn NH cho vay TDH.
3. **Báo cáo môi giới ≤3 THÁNG** (SSI/HSC/VCI/MBS/VND) — cross-check + chỉ tiêu phái sinh (formation rate, NIM yield/CoF tách sẵn). **Bỏ báo cáo cũ hơn 3 tháng** (giả định lạc hậu).

Chỉ tiêu tầng 2: NPL (nhóm 3-5) · **nợ nhóm 2** · **nhóm 3/4/5 split** · **tỷ lệ hình thành nợ xấu** · CASA · CD/huy động · CAR · RWA · NIM thực (yield−CoF) · coverage/LLCR · cho vay theo ngành (BĐS/mua nhà/xây dựng) · TPDN · related-party · LDR quy định · vốn NH cho vay TDH · vốn liên NH/nợ.

### Tầng 3 — CROSS-CHECK (bắt buộc ≥2 nguồn)
cafef.vn / vietstock.vn đối chiếu mọi số tầng 1–2. **Quý gần nhất:** vnstock chỉ ~4 năm & **nhãn quý không tin** → lấy từ **công bố công ty + cafef**. Mâu thuẫn nguồn → **nêu rõ, không chọn bừa** (vd NPL: PR 0,96% vs BCTC 1,29% → dùng số BCTC).

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
2. **vnstock ratio LỖI THỜI cho ngân hàng** → NPL/CASA/CAR/NIM/coverage **PHẢI** lấy từ **công bố IR công ty + BCTC thuyết minh** (crawl4ai), cross-check môi giới **≤3 tháng**. Tự tính phần tầng 1 từ income+balance.
3. **Khoản bất thường → đọc THUYẾT MINH** (nợ nhóm 3/4/5, cho vay theo ngành, related-party, lãi dự thu, TPDN) và trích nguồn trước khi diễn giải.
4. **Báo cáo môi giới chỉ dùng nếu ≤3 tháng tuổi** (cũ hơn = giả định lạc hậu, không làm neo).
