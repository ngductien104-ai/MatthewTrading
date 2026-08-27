---
name: bank-financial-statement
description: "Phân tích BCTC chuyên sâu NGÂN HÀNG TMCP Việt Nam (buy-side) — earnings quality (PPOP vs PBT, NIM tách yield−CoF, forensics lãi dự thu), rủi ro tài sản forward-looking (nợ nhóm 2/3/4/5, tỷ lệ hình thành nợ xấu, coverage, thời vụ, cho vay theo ngành, related-party hệ sinh thái), thanh khoản & vốn (CASA/LDR/CAR/internal capital generation). Routing: tự tính từ vnstock_data income+balance (8 năm + 34 quý, mã id ổn định); NIM/NPL/CASA/CAR/CIR lấy nhóm RT_BANK_* rồi cross-check công bố IR; nợ nhóm 2/3/4/5, cho vay theo ngành, related-party vẫn phải crawl4ai từ thuyết minh; cross-check ≥2 nguồn + môi giới ≤3 tháng. KHÔNG định giá (task riêng)."
category: analysis
---

# Phân tích BCTC Ngân hàng TMCP Việt Nam (buy-side · Financial Analyst)

## Vai trò & mục đích
Senior buy-side Financial Analyst (CFA, 10y+), chuyên ngành ngân hàng VN. Bóc **chất lượng lợi nhuận thật, rủi ro bảng cân đối, sức khỏe vốn/thanh khoản** qua 3 BCTC. **Chỉ phân tích tài chính — KHÔNG định giá** (định giá là skill/task riêng). Số bề mặt (NPL 1,1%) KHÔNG phải kết luận → phải tới **driver & xu hướng**.

**Khi nào dùng:** `Company.overview().is_bank == True` (hoặc com_type_code='NH'). Mẫu BCTC ngân hàng khác DN thường: có **Thu nhập lãi thuần / Tổng thu nhập hoạt động / trích lập dự phòng**, KHÔNG có doanh thu/giá vốn/tồn kho. Securities/insurance dùng template riêng.

---

## 1. ROUTING DỮ LIỆU (đã audit lại trên `vnstock_data` — BẮT BUỘC theo)

> Nguồn chính là **`vnstock_data` (Unified UI, gói tài trợ)**. Mẫu BCTC ngân hàng
> được tự nhận diện, trả frame dạng dài `period, id, name, level, unit, value`
> với **mã `id` ổn định, duy nhất trong mỗi kỳ** — không còn phải khớp chuỗi
> `item.str.contains(...)` mong manh như bản free.

### Tầng 1 — TỰ TÍNH từ `income_statement` + `balance_sheet` ✅ tin cậy

```python
from vnstock_data import Fundamental
f = Fundamental().equity("TCB")
inc = f.income_statement(period="year")      # 8 kỳ năm 2018–2025
bal = f.balance_sheet(period="year")
```

| Dòng cần | `id` |
|---|---|
| NII | `IS_NET_INTEREST_INCOME` |
| Lãi thuần dịch vụ (fee) | `IS_NET_FEE_AND_COMMISSION_INCOME` |
| Lãi KD ngoại hối / CK kinh doanh / CK đầu tư | `IS_NET_GAIN_LOSS_FROM_FOREIGN_CURRENCIES_AND_GOLD` / `..._TRADING_SECURITIES` / `..._INVESTMENT_SECURITIES` |
| Lãi thuần hoạt động khác | `IS_NET_OTHER_INCOME` |
| **TOI** | `IS_TOTAL_OPERATING_INCOME` |
| Opex | `IS_OPERATING_EXPENSES` ⚠️ **thường NaN** → suy ra `TOI − PPOP` |
| **PPOP** | `IS_OPERATING_PROFIT_BEFORE_PROVISION_FOR_CREDIT_LOSSES` |
| Trích lập dự phòng | `IS_PROVISION_FOR_CREDIT_LOSSES` (âm) |
| PBT / NPAT / NPAT mẹ | `IS_PROFIT_BEFORE_TAX` / `IS_NET_PROFIT_AFTER_TAX` / `IS_PROFIT_AFTER_TAX_FOR_SHAREHOLDERS_OF_PARENT_COMPANY` |
| EPS | `IS_BASIC_EARNINGS_PER_SHARE` |
| Tổng TS / VCSH / Vốn điều lệ | `BS_TOTAL_ASSETS` / `BS_EQUITY` / `BS_CHARTER_CAPITAL` |
| Cho vay KH (gross / thuần) / LLR | `BS_LOANS_TO_CUSTOMERS_GROSS` / `BS_LOANS_TO_CUSTOMERS` / `BS_PROVISION_LOANS_TO_CUSTOMERS` (âm) |
| Tiền gửi KH | `BS_CUSTOMER_DEPOSITS` |
| **Lãi & phí phải thu** (forensic) | `BS_INTEREST_AND_FEE_RECEIVABLES` |
| Chứng khoán đầu tư / TPDN-proxy | `BS_INVESTMENT_SECURITIES` |
| Tiền gửi & cho vay TCTD khác | `BS_PLACEMENTS_AND_LOANS_TO_CREDIT_INSTITUTIONS` |

**Khớp số bắt buộc trước khi dùng** (verify TCB 2025 — làm đúng thế này cho mã khác):
`PPOP 36.959 − dự phòng 4.421 = PBT 32.538` ✓ · `NPAT 25.954 = mẹ 25.290 + CĐTS 664` ✓ ·
`Vốn điều lệ 70.862 tỷ = 7,086 tỷ CP × 10.000đ` ✓ · `CIR suy ra = (53.391−36.959)/53.391 = 30,8%`
khớp `RT_BANK_CIR` ✓.

**Công thức (tự tính, kiểm soát định nghĩa):**
```
ROAA = NPAT / bình quân Tổng TS          ROAE = NPAT mẹ / bình quân VCSH
NIM proxy = NII / bình quân Tổng TS       (NIM THỰC dùng TS sinh lãi → RT_BANK_NIM ở tầng 2)
CIR = (TOI − PPOP) / TOI                  Credit cost = -Provision / bình quân Cho vay
LDR thuần = Cho vay / Tiền gửi            LLR/loans = -LLR / Cho vay gross
Non-II/TOI, Fee/TOI ; PPOP growth vs PBT growth (chênh = "vay" LN từ trích lập)
Lãi dự thu/Tổng TS  → nếu tăng nhanh hơn NII = nghi lãi ảo
BVPS = VCSH / số CP ; P/B, P/E lấy thẳng RT_VALUE_PB / RT_VALUE_PE
```
Số CP: `RT_VALUE_OUTSTANDING_SHARES`. Room ngoại / target / rating: `company.overview()`.

### Tầng 1b — QUÝ (BẮT BUỘC — luôn tính thêm quý vừa công bố) ✅
> Phân tích FY là CHƯA ĐỦ. Quý gần nhất thường đảo chiều xu hướng FY (vd TPB: FY2025 nợ xấu "đẹp" 1,29% nhưng **Q1/2026 bật lại 1,85%**). Luôn kéo & tính quý mới nhất.

`period="quarter"` trả **34 kỳ, từ 2018-Q1 → 2026-Q2**, nhãn tường minh dạng
`2026-Q2`. Đây là thay đổi lớn so với bản free (chỉ 4 quý):

- **YoY tự tính được cho MỌI dòng** — không còn phải cào cafef/vietstock chỉ để
  lấy quý cùng kỳ năm trước. Cào chỉ còn là bước **cross-check**, không phải bước
  lấy dữ liệu.
- Tính QoQ, YoY, run-rate/annualize và trailing-4Q so với FY; BCĐKT cuối quý
  (cho vay, tiền gửi → growth YTD, LDR thuần, LLR/loans, lãi & phí phải thu).

> ⚠️ Nhãn quý của bản free KBS bị lệch (Q4→Q1) — `vnstock_data` KHÔNG dính lỗi
> này, nhưng **vẫn cross-check headline quý với công bố KQKD công ty + cafef**
> trước khi báo số ra ngoài.

### Tầng 2 — CHỈ SỐ NGÀNH `RT_BANK_*` (đã SỐNG, nhưng đọc đúng cách)

Bản tài trợ có hẳn nhóm **ĐẶC THÙ NGÀNH NGÂN HÀNG** trong `f.ratio(period=...)`:
`RT_BANK_NIM`, `RT_BANK_YIEA`, `RT_BANK_COF`, `RT_BANK_CIR`, `RT_BANK_LDR`,
`RT_BANK_NPL`, `RT_BANK_NPL_COVERAGE`, `RT_BANK_CAR`, `RT_BANK_CASA`,
`RT_BANK_LLR_TO_LOANS`, `RT_BANK_PROVISION_TO_LOANS`, `RT_BANK_LOAN_GROWTH`,
`RT_BANK_DEPOSIT_GROWTH`, `RT_BANK_EQUITY_TO_LOANS`, `RT_BANK_NOII` — **8 kỳ năm**.

> Cảnh báo cũ "vnstock_data ratio trả số vintage 2018" **chỉ còn đúng với bản free**.
> Bản tài trợ trả số kỳ hiện hành: TCB 2025 NIM 3,76% · CASA 35,87% · CAR 14,61%
> · NPL 1,07% · CIR 30,8% · ROE 15,85% — đúng bậc so với công bố của ngân hàng.

**Ba cái bẫy khi đọc `RT_*` (đã verify trên TCB 2025):**

| Bẫy | Thực tế | Xử lý |
|---|---|---|
| `unit` ghi `%` | Là **phân số** (NPL 0,01068 = 1,068%) | Nhân 100 khi trình bày |
| Một số chỉ tiêu **mang dấu âm** theo dòng chi phí gốc: `COF −3,34%`, `CIR −30,8%`, `NPL_COVERAGE −128%`, `PROVISION_TO_LOANS −0,63%` | Độ lớn mới là số thật | Lấy `abs()`, nêu rõ trong ghi chú |
| Chỉ tiêu công nghiệp trả **0,0** cho ngân hàng: `EBIT`, `EBITDA`, `ATR`, `CR`, `QR`, `LEV_DE`, `RT_VALUE_EQUITY` | `0` ở đây nghĩa là **KHÔNG ÁP DỤNG**, không phải bằng không | **Cấm** báo "D/E = 0". Vốn chủ lấy `BS_EQUITY` |

**Vẫn PHẢI lấy ngoài** (API không có), thứ tự ưu tiên:
1. **Công bố KQKD của ngân hàng (IR press release PDF)** — **nợ nhóm 2**, **split
   nhóm 3/4/5**, **tỷ lệ hình thành nợ xấu**, CAR theo Basel II/III do NH tự công bố.
2. **BCTC + thuyết minh** (crawl4ai/PDF): phân loại nợ nhóm 1–5 (note "Phân tích
   chất lượng nợ cho vay"), **cho vay theo ngành**, **giao dịch bên liên quan**,
   TPDN, LDR quy định, vốn ngắn hạn cho vay trung–dài hạn.
3. **Báo cáo môi giới ≤3 THÁNG** (SSI/HSC/VCI/MBS/VND) — cross-check + chỉ tiêu
   phái sinh. **Bỏ báo cáo cũ hơn 3 tháng.**

> Chênh giữa `RT_BANK_*` và công bố IR là chuyện bình thường (định nghĩa khác:
> cuối kỳ vs bình quân, hợp nhất vs riêng lẻ). **Lệch → nêu cả hai và nói rõ dùng
> số nào, không chọn bừa.**

### Tầng 3 — CROSS-CHECK (bắt buộc ≥2 nguồn)
cafef.vn / vietstock.vn đối chiếu mọi số tầng 1–2. **Quý gần nhất:** `vnstock_data` đã có 34 quý nhãn tường minh, nhưng headline quý vẫn phải đối chiếu **công bố công ty + cafef** trước khi báo ra ngoài. Mâu thuẫn nguồn → **nêu rõ, không chọn bừa** (vd NPL: PR 0,96% vs BCTC 1,29% → dùng số BCTC).

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
2. **`RT_BANK_*` của vnstock_data đã sống** → NIM/NPL/CASA/CAR/CIR/coverage lấy được trực tiếp (nhớ: phân số, vài chỉ tiêu mang dấu âm, `0` = không áp dụng) nhưng **vẫn cross-check công bố IR**. Riêng **nợ nhóm 2, split nhóm 3/4/5, hình thành nợ xấu, cho vay theo ngành, related-party** thì API KHÔNG có → **BẮT BUỘC** lấy từ công bố IR + BCTC thuyết minh (crawl4ai), cross-check môi giới **≤3 tháng**. (Cảnh báo "ratio lỗi thời" chỉ còn đúng với bản free.)
3. **Khoản bất thường → đọc THUYẾT MINH** (nợ nhóm 3/4/5, cho vay theo ngành, related-party, lãi dự thu, TPDN) và trích nguồn trước khi diễn giải.
4. **Báo cáo môi giới chỉ dùng nếu ≤3 tháng tuổi** (cũ hơn = giả định lạc hậu, không làm neo).
