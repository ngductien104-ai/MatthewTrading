# KHUNG SƯỜN MẪU — FINANCIAL ANALYSIS NGÂN HÀNG (VN) · buy-side

> **Role:** Senior buy-side Financial Analyst (CFA, 10y+), chuyên ngành ngân hàng VN. Mục tiêu: bóc **earnings quality thật, rủi ro bảng cân đối, sức khỏe vốn/thanh khoản** qua 3 BCTC — KHÔNG định giá (định giá là task riêng).
> **Học từ:** SSI Research & MBS Research (TPB, 03/2026) ở `Báo cáo phân tích/Ngành Ngân Hàng/`. Cấu trúc gốc: SSI Bảng 2 (BCĐKT) + Bảng 3 (P&L) + phân tích **thời vụ nợ xấu** + tách **NIM = yield − CoF**; MBS bảng đánh giá KQKD (Hình 5) + **X-quang sổ vay** theo khách hàng/ngành/kỳ hạn + **NPL formation theo quý**.
> **Nguyên tắc:** mỗi chỉ tiêu phải gắn (i) câu hỏi phân tích, (ii) red flag, (iii) "so what" cho quyết định. Số bề mặt (NPL 1,1%) KHÔNG phải kết luận — phải đi tới driver & xu hướng. Bổ trợ [[workflow-deep-dive-equity-analysis]] · [[feedback-vnstock-quarterly-labels-unreliable]].

---

## 0. NHẬN DIỆN & MÔ HÌNH KINH DOANH (định khung trước khi mổ số)
- Quy mô (tổng TS, vốn CSH, vốn hóa), sở hữu & **hệ sinh thái** (vd TCB–Vingroup/Masterise/Sun/One Mount; MBB–Viettel; VPB–consumer/GPBank; HDB–HD Saison; STB–tái cơ cấu).
- **Mô hình**: bán lẻ vs bán buôn vs "ngân hàng BĐS"; động lực thu nhập (NII-heavy hay fee-heavy); công ty con trọng yếu (TCBS, FE Credit, MCredit/MIC, HD Saison) — ảnh hưởng cấu trúc thu nhập & rủi ro.
- **Trạng thái room tín dụng**: có thuộc nhóm **nhận chuyển giao bắt buộc** (MBB/VCB/HDB/VPB) → được room cao hơn không. Quyết định trần tăng trưởng.
- → Chọn **đối chứng phù hợp** (so TCB với MBB/ACB/VPB, không so với VCB SOCB).

---

## I. PHÂN TÍCH LỢI NHUẬN & CHẤT LƯỢNG LỢI NHUẬN (Income — earnings quality)

### I.1 Cấu trúc & độ bền thu nhập
| Mục | Phân tích | Red flag |
|---|---|---|
| NII vs Non-II / TOI | tỷ trọng & xu hướng; mục tiêu đa dạng hóa | quá lệ thuộc NII khi NIM nén |
| **Bóc Non-II** | phí thanh toán/thẻ · **bancassurance** · FX · **lãi chứng khoán đầu tư/KD** · **thu hồi nợ đã xử lý** · thu khác | Non-II nhờ **trading/chứng khoán** (biến động) hoặc **thu nhập khác đột biến** = kém bền (TCB Q4/25 thu chứng khoán −99%) |
| Phí dịch vụ | driver bền (thanh toán/thẻ/NH số) vs rủi ro (banca sau siết luật) | phí giảm do banca → cần bù bằng mảng khác |

### I.2 NIM — phải TÁCH driver, không đọc 1 số
```
NIM = Lợi suất tài sản sinh lãi (IEA yield) − Chi phí vốn (CoF)
Driver: (a) asset mix (bán lẻ↑ → yield↑); (b) CASA↑ → CoF↓; (c) repricing cho vay/huy động;
        (d) tỷ trọng cho vay/tổng TS; (e) cạnh tranh lãi suất huy động.
```
- So **NIM trailing-12M** vs **NIM spot quý** (bắt điểm đảo chiều). VD TPB: NIM cả năm −50bps, NII +3,6% dù tín dụng +22% → **nén cấu trúc**. TCB Q1/26 NIM 3,1% (spot) vs 3,7% (trailing) → CoF tăng do cạnh tranh huy động.
- **So what:** NIM nén = động lực sinh lời lõi yếu → cần soi liệu bù được bằng volume (tăng tín dụng) & fee không.

### I.3 PPOP — thước đo earnings power LÕI
- **PPOP = TOI − chi phí HĐ** = lợi nhuận trước khi "chọn" mức trích lập. **So tăng trưởng PPOP vs tăng trưởng PBT**: chênh lớn = lợi nhuận do **giảm trích lập**, không phải core (TPB: PBT +21% nhưng PPOP +5,5%).
- **Operating leverage**: TOI growth vs opex growth; **CIR** xu hướng & cấu phần (nhân sự/công nghệ/marketing). **Cảnh báo cắt giảm bất thường** đẩy CIR ảo (TPB Q4/25 cắt 45% chi phí nhân sự → CIR 22,8%).

### I.4 Forensics chất lượng lợi nhuận (đào thuyết minh)
- **Lãi & phí phải thu (accrued interest receivable)** trên BCĐKT: tăng **nhanh hơn NII thực** → dấu hiệu **lãi dự thu ảo** (lãi ghi nhận nhưng chưa thu được tiền) → chất lượng lợi nhuận đáng ngờ. **Chỉ tiêu forensic số 1 của NH.**
- **Thu nhập khác** đột biến (thu hồi nợ đã xử lý, hoàn nhập dự phòng, đánh giá lại) → bóc one-off.
- **Thuế suất hiệu dụng** bất thường (ưu đãi/hoàn) làm méo NPAT.
- **So what:** dựng **earnings power chuẩn hóa** = PPOP − **credit cost qua chu kỳ (through-cycle)** − one-off → LN bền thật làm nền cho định giá sau.

---

## II. CHẤT LƯỢNG TÀI SẢN & RỦI RO BẢNG CÂN ĐỐI — ⭐ TRỌNG TÂM

### II.1 X-quang sổ cho vay (không chỉ tổng dư nợ)
- **Tăng trưởng tín dụng vs room NHNN**; cho vay KH vs tổng tín dụng (gồm TPDN/liên NH).
- **Theo khách hàng**: KHDN lớn / SME / bán lẻ — ai dẫn dắt? (TPB: KHDN lớn +23,7%, tỷ trọng 12%→22% → tập trung hóa). Tăng nóng nhóm nào = rủi ro nhóm đó.
- **Theo ngành** (đọc thuyết minh): **chủ đầu tư BĐS · mua nhà · xây dựng · sản xuất · tiêu dùng/thẻ · BOT**. VD TPB cho vay KD BĐS 32.255 tỷ (+51%); nợ xấu dồn ở mua nhà/BĐS/xây dựng.
- **Kỳ hạn**: tỷ trọng trung-dài hạn (TPB 61,3%, +8,4% QoQ) → lệch kỳ hạn.
- **TPDN nắm giữ**: tỷ trọng/dư nợ, tổ chức phát hành (BĐS?), xu hướng (TPB giảm = de-risk; điểm cộng).

### II.2 Chất lượng nợ — FORWARD-LOOKING (đây là chỗ khác "associate")
| Lớp | Chỉ tiêu | Vì sao quan trọng |
|---|---|---|
| Tĩnh | NPL (nhóm 3-5), **nợ nhóm 2** | nhóm 2 = **leading indicator** NPL 1-2 quý |
| Cơ cấu | **% nhóm 5 (mất vốn) trong NPL** | nhóm 5 cao = chất lượng xấu thực (TPB Q1/26 nhóm 5 = 42% NPL, +79%) |
| **Động (lõi)** | **Tỷ lệ hình thành nợ xấu** = nợ xấu mới hình thành / dư nợ bình quân | **chỉ báo XU HƯỚNG quan trọng nhất** — loại nhiễu xử lý/thời vụ |
| Roll-rate | dịch chuyển nhóm 1→2→3→5 theo quý | tốc độ "trôi" nợ |
| **Thời vụ** | NPL có giảm Q4 (xử lý/tái cơ cấu) rồi **tăng lại Q1-Q3**? | mô-típ TPB 2022-24 → cải thiện Q4/25 chỉ THỜI VỤ (SSI), Q1/26 xác nhận |
| Làm đẹp | **xử lý nợ (write-off) & thu hồi (recovery)** trong kỳ | đo phần NPL giảm do "dọn" thay vì cải thiện thật |
| Tái cơ cấu | **TT02/TT06/TT31** — nợ phân loại lại nhóm 1, nợ tái cơ cấu còn treo | nợ ẩn sắp lộ khi hết hiệu lực (TPB tái phân loại 1.800 tỷ về nhóm 1) |

### II.3 Bộ đệm dự phòng (đủ hấp thụ không?)
- **LLCR (coverage = dự phòng/NPL)**: so peer (VCB >200% vs tư nhân 60–130%); **tính biến động** (TPB choppy 61→93%→~62%; TCB ổn định >100% 9 quý liền).
- **Credit cost** (trích lập/dư nợ bình quân) vs **tỷ lệ hình thành nợ xấu**: trích lập có theo kịp nợ xấu mới sinh không? Giảm credit cost + coverage mỏng = "vay" lợi nhuận tương lai.
- **So what:** coverage mỏng + nợ xấu tăng → 2026 buộc trích lập bù → bào mòn LN (chính là rủi ro earnings của TPB).

### II.4 Concentration, related-party & tài sản ẩn rủi ro (VN đặc thù)
- **Top-20 khách hàng / dư nợ + TPDN hệ sinh thái** (đọc thuyết minh giao dịch bên liên quan): TCB–Masterise/Vingroup/Sun; rủi ro 1 chủ đầu tư lớn vỡ.
- **LTV tài sản đảm bảo** (chủ yếu BĐS) — giá trị TSĐB co khi BĐS giảm.
- **Tài sản Có khác / các khoản phải thu** tăng bất thường (TPB phải thu ×3,7 QoQ Q4/25 — SSI flag) → có thể "giấu" tài sản kém chất lượng.
- **Off-balance-sheet**: bảo lãnh, L/C, cam kết cho vay không hủy ngang.

---

## III. NGUỒN VỐN, THANH KHOẢN & AN TOÀN VỐN (Funding / Liquidity / Capital)

### III.1 Huy động & chi phí vốn
- Tăng trưởng huy động vs tín dụng (huy động hụt hơi → lệ thuộc nguồn khác). **CASA** (TCB 39% số 1 → CoF thấp; TPB 22%) — **CASA bền hay nhờ KM lãi suất?**
- Tỷ trọng **chứng chỉ tiền gửi (CD)** — CD cao = vốn đắt nhưng giảm lệch kỳ hạn (TPB CD 13%→17%).

### III.2 Thanh khoản & lệch kỳ hạn
- **LDR quy định (trần 85%)** vs **LDR thuần** (cho vay/tiền gửi) — phân biệt (TPB reg 68,8% nhưng thuần 92,6%; TCB thuần 122%).
- **Tỷ lệ vốn ngắn hạn cho vay trung-dài hạn** (trần NHNN **30%**), xu hướng (TPB 18,9%).
- **Vốn liên ngân hàng / giấy tờ có giá trên tổng nợ** (TPB 24%) → nhạy lãi suất liên NH, rủi ro thanh khoản khi căng.
- **Maturity wall** trái phiếu/GTCG phát hành đáo hạn.

### III.3 An toàn vốn & khả năng tự tạo vốn
- **CAR (Basel II; một số NH Basel III)**, Tier-1, **RWA density** (RWA/tổng TS); lộ trình Basel III.
- **Internal capital generation** = ROE × (1 − payout) so với **tốc độ tăng RWA**: tăng trưởng có "ăn" vào vốn không, có cần phát hành thêm không. (TCB vốn quá dày → ROE bị pha loãng; TPB giữ lại để xây CAR sau khi CAR giảm 14,7%→12,8%.)
- **Đòn bẩy** Tài sản/Vốn CSH (~10-12x).

---

## IV. "CASH-FLOW HEALTH" CHO NGÂN HÀNG (điều chỉnh — KHÔNG dùng FCF)
> BCLCTT của NH ít ý nghĩa; FCF/CAPEX không áp dụng. Thay bằng các "đại lượng tiền thật" của NH:
- **Lãi dự thu vs NII thực thu** (mục I.4) — lãi ảo hay tiền thật.
- **Recovery thực** từ nợ đã xử lý (tiền về thật).
- **Internal capital generation** (mục III.3) thay cho FCF — khả năng tự nuôi tăng trưởng bằng vốn nội sinh.
- Dòng tiền huy động ròng vs giải ngân ròng (mất cân đối → căng thanh khoản).

---

## IV-bis. PHÂN TÍCH QUÝ GẦN NHẤT (bắt buộc — FY là chưa đủ)
> Quý vừa công bố thường **đảo chiều** xu hướng FY → luôn tính thêm. (TPB: FY2025 NPL 1,29% "đẹp" nhưng **Q1/2026 bật lại 1,85%, nhóm 5 +79%**.)
- **KQKD quý**: NII/fee/TOI/PPOP/provision/PBT/NPAT — **QoQ** (vnstock VCI quý, nhãn chuẩn `2026-Q1...`) + **YoY** — vnstock chỉ trả 4 quý (thiếu quý cùng kỳ năm trước) → **crawl4ai cào quý cùng kỳ** (cafef `IncSta/BSheet` + vietstock + IR công ty) để tự tính YoY mọi dòng, cross-check %YoY công bố.
- **Bóc core vs one-off** trong quý (thu chứng khoán/thu hồi nợ/đánh giá lại) — chất lượng lợi nhuận quý.
- **Run-rate / trailing-4Q** vs FY & vs kế hoạch năm → đang chạy nhanh/chậm hơn pace.
- **BCĐKT cuối quý**: cho vay/tiền gửi (growth YTD), LDR, **lãi & phí phải thu** xu hướng; **NPL/nhóm 2/coverage/CASA cuối quý** (công bố/thuyết minh).
- **Kết luận: quý gần nhất XÁC NHẬN hay ĐẢO CHIỀU** các xu hướng FY (nợ xấu, NIM, fee, CIR)?

---

## V. TỔNG HỢP — CHẤM ĐIỂM SỨC KHỎE TÀI CHÍNH
**3 trụ (chấm 1-10 mỗi trụ, nêu rõ lý do):**
1. **Earnings power & quality** — PPOP growth, NIM bền, non-II bền, operating leverage, lãi dự thu, mức độ "vay" LN từ giảm trích lập.
2. **Asset quality & BS risk** — formation rate & xu hướng, nhóm 2/nhóm 5, coverage vs formation, concentration/related-party, thời vụ.
3. **Funding / liquidity / capital** — CASA/CoF, LDR & lệch kỳ hạn, liên NH, CAR & internal capital generation.

**Đầu ra bắt buộc:**
- **Điểm tổng hợp 1-10** + **nhãn earnings quality** (cao / trung bình / nghi ngờ) kèm lý do lõi.
- **3-5 rủi ro tài chính cốt lõi — ĐỊNH LƯỢNG** (vd "mỗi +0,1% credit cost ≈ −X tỷ NPAT"; "coverage 62% < formation rate → cần trích thêm Y tỷ").
- **Tín hiệu cải thiện / xấu đi** (1-2 năm) + **earnings power chuẩn hóa** (PPOP − through-cycle credit cost − one-off) → bàn giao cho task Định giá.
- **So peer** (đặt nền cho hồi quy P/B–ROE ở bước định giá, KHÔNG định giá ở đây).

---

## VI. BẢNG CHỈ TIÊU CHUẨN (4 năm + quý gần nhất) — template điền cho mỗi mã
Sinh lời: NII · Non-II (bóc) · TOI · **PPOP** · CIR · **NIM (yield/CoF)** · ROAA · ROAE · Non-II/TOI
Tăng trưởng: tín dụng (vs room) · huy động · CASA · TOI · PPOP · PBT · EPS · BVPS
Chất lượng TS: NPL · **nợ nhóm 2** · **nhóm 5 %** · **formation rate** · LLCR · credit cost · write-off/recovery · TPDN · cho vay BĐS+xây dựng %
Thanh khoản/vốn: LDR (reg & thuần) · vốn NH/cho vay TDH · liên NH/nợ · CAR · RWA density · internal capital gen · TS/VCSH
Forensic: lãi & phí phải thu / tổng TS · phải thu khác (bất thường)

---

## VII. CROSS-CHECK & DATA INTEGRITY (BẮT BUỘC)
1. **Mẫu BCTC NH** khác DN thường (Thu nhập lãi thuần; không DT/giá vốn/tồn kho) → dùng template NH. Nhận diện qua `Company.overview().is_bank`.
2. Nguồn 3 BCTC: vnstock VCI (4 năm) + công bố NH (press release KQKD) + **cross-check ≥2 nguồn** (cafef/vietstock). **Không tin nhãn cột quý vnstock** → lấy quý từ cafef/công bố.
3. **Mọi khoản bất thường → đọc THUYẾT MINH** (nợ nhóm 3/4/5, cho vay theo ngành, giao dịch bên liên quan, lãi dự thu, TPDN) và trích nguồn trước khi diễn giải.
4. **Mâu thuẫn nguồn → nêu rõ, không chọn bừa** (vd TPB NPL: PR 0,96% vs BCTC 1,29% → dùng số BCTC).
5. Số đủ + chính xác (đã cross-check) → kết luận mới chuẩn. Thiếu → đi crawl4ai/đọc PDF kiểm toán, không đoán.
