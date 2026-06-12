# KHUNG SƯỜN — VALUATION NGÂN HÀNG TMCP VIỆT NAM (buy-side · IB)

> **Role:** Senior Valuation Analyst, đa mô hình cross-validation, ngành ngân hàng VN. **Task RIÊNG với Financial Analysis** — nhận đầu vào (ROE/earnings power **chuẩn hóa**, BVPS, chất lượng tài sản) từ task FA, KHÔNG phân tích lại BCTC ở đây.
> **Học từ:** MBS (RI 50% + P/B mục tiêu 50%, COE 14,8%, g 3%), SSI (P/B mục tiêu 0,9x, thận trọng), Shinhan (TCB **SOTP**: NH mẹ P/B 1,5x + TCBS P/B 2,5x). Báo cáo `Báo cáo phân tích/Ngành Ngân Hàng/`.
> **Nguyên tắc:** NH **KHÔNG DCF/FCF** (dòng tiền không phải FCF). Định giá trên **vốn chủ sở hữu** (equity value). Mọi mô hình chạy trên **ROE CHUẨN HÓA** (qua chu kỳ), không dùng ROE danh nghĩa bị tô bởi giảm trích lập/one-off. Bổ trợ [[project-bank-sector-analysis]] · [[feedback-beta-institution-standard]].

---

## 0. ĐẦU VÀO (nhận từ task Financial Analysis — bắt buộc)
- **ROE chuẩn hóa** (through-cycle) & **earnings power chuẩn hóa** (PPOP − credit cost qua chu kỳ − one-off). VD TPB: ROE chuẩn ~14% (≠ 18% danh nghĩa).
- **BVPS / VCSH** hiện tại + **điều chỉnh book**: trừ (a) **thiếu hụt dự phòng** (NPL × (coverage mục tiêu − coverage hiện tại)), (b) lãi dự thu kém chất lượng → **adjusted/tangible book**.
- Chất lượng tài sản, NIM outlook, tăng trưởng tín dụng (room), CASA → driver cho ROE path.
- **SLCP hiện tại** (điều chỉnh cổ tức cổ phiếu/pha loãng), market_cap, giá (overview).

---

## I. PHƯƠNG PHÁP LÕI 1 — Residual Income / Excess Return ⭐
```
RI_t = (ROE_t − COE) × VCSH_(t-1)
Giá trị VCSH = VCSH_0 (adjusted) + Σ PV(RI_t, t=1..n) + PV(giá trị cuối cùng)
Giá trị cuối cùng = RI_(n+1) / (COE − g) ; chiết khấu về hiện tại.
Giá trị/cp = Giá trị VCSH / SLCP.
```
**Tinh chỉnh "deep" (khác associate):**
- **COE per-bank**: COE = Rf + β×ERP. **β tính riêng từng mã** (2Y tuần, Bloomberg-style — [[feedback-beta-institution-standard]]): bluechip ~1,0–1,1 (TCB/VCB) vs midcap ~1,3 (TPB). Rf = **lợi suất TPCP 10Y VN** (~3–4%). ERP VN (frontier) ~7–9%. → COE ngành 13–15%.
- **ROE FADE path**: ROE_t giảm dần từ ROE chuẩn hóa hiện tại về **ROE bền vững** (sustainable), KHÔNG phẳng. ROE bền vững gắn với tăng trưởng bền vững g = ROE×(1−payout) và RWA.
- **g terminal**: 3–4% (gắn GDP danh nghĩa VN dài hạn), kiểm tra g < COE.
- Equity roll-forward: VCSH_t = VCSH_(t-1) + NPAT_t×(1−payout). Cổ tức **CP = trung tính** (chia per-share); cổ tức **tiền mặt** giảm VCSH.

## II. PHƯƠNG PHÁP LÕI 2 — Justified P/B & P/B mục tiêu ⭐
```
P/B hợp lý (Gordon) = (ROE_bền_vững − g) / (COE − g)
Giá mục tiêu = P/B mục tiêu × BVPS forward (thường +1 năm)
```
- **Hồi quy P/B–ROE chéo ngành** (cross-sectional, ~15 NH niêm yết): dựng đường `P/B = a + b×ROE` → mã nằm **trên/dưới đường** = đắt/rẻ tương đối so chất lượng. **Công cụ tạo "edge" chính** — đặt nền từ bảng peer của task FA.
- **P/B mục tiêu** neo theo 3 mỏ: (a) justified P/B (Gordon), (b) **P/B lịch sử** (TB 3–5 năm + **percentile** hiện tại), (c) đường hồi quy ngành — rồi **điều chỉnh theo outlook chất lượng tài sản & ROE** (SSI hạ về 0,9x do lo nợ xấu; MBS 1,2x = TB 3 năm).

## III. SOTP — cho NH có công ty con trọng yếu ⭐
NH mẹ (P/B theo ROE mẹ) **+** công ty con định giá riêng, tránh **double-count**:
| NH | Công ty con | Cách định giá con |
|---|---|---|
| TCB | **TCBS** (chứng khoán, ~94%) | P/B ~2,5x (Shinhan) — sắp IPO, optionality |
| VPB | **FE Credit** | P/B/P/E tài chính tiêu dùng (đang lỗ/hồi phục → thận trọng) |
| MBB | MCredit + MIC (bảo hiểm) | P/B riêng |
| HDB | HD Saison | P/B tài chính tiêu dùng |
> ⚠️ **Không cộng cả RI hợp nhất VÀ SOTP** (LN con đã trong hợp nhất). Chọn: hoặc RI/ P-B trên hợp nhất, hoặc SOTP (mẹ tách + con riêng). SOTP hợp khi con có multiple khác hẳn mẹ (TCBS).

## IV. ĐỊNH GIÁ TƯƠNG ĐỐI
- **Peer multiples forward** (P/B, P/E, **P/B-ROE**) vs TB NHTMCP tư nhân (~1,5x/18% ROE) & SOCB (~2,1x) & dẫn đầu. (MBS bảng peer 03/2026.)
- **P/B/P/E lịch sử percentile** — nêu rõ window. **vnstock ratio LỖI THỜI** → dùng **DataPro `close` × SLCP / (VCSH, NPAT)** tự dựng chuỗi P/B, P/E lịch sử.
- PEG ít dùng cho NH.

## V. REVERSE / IMPLIED (variant perception)
- **Reverse Gordon**: giá hiện hàm ý **ROE/g** bao nhiêu → so với ROE chuẩn hóa của mình. (VD TPB P/B 0,82x fwd hàm ý ROE ≈ COE → thị trường không tin ROE > COE bền.)
- **Implied COE** từ giá + ROE/g đồng thuận.

## VI. TỔNG HỢP, KỊCH BẢN & ĐỘ NHẠY
- **Blend** (vd RI 50% + P/B mục tiêu 50% — MBS; hoặc 3 phương pháp có trọng số).
- **Kịch bản bull/base/bear gắn DRIVER** (credit cost, NIM, ROE, tăng trưởng tín dụng) — không chỉ ±%.
- **Bảng độ nhạy 2 chiều**: (COE × credit cost) và (**P/B mục tiêu × credit cost**) — vì với NH có ROE≈COE, giá cực nhạy 2 biến này.
- **Target 12M** (xác suất-gia quyền), **biên an toàn**, vùng mua, **khuyến nghị**.
- **Catalysts re-rating ĐỊNH LƯỢNG** (tích cực/tiêu cực): formation rate đảo chiều, NIM phục hồi, SOTP/IPO con, room tín dụng, credit cost normalize…

## VII. LIÊN KẾT VĨ MÔ (top-down)
Chu kỳ **lãi suất** → NIM & COE (Rf); chu kỳ **BĐS** → chất lượng tài sản & ROE & tăng trưởng tín dụng; **room tín dụng NHNN** (nhóm nhận chuyển giao bắt buộc được room cao → tăng trưởng & ROE cao hơn). Định giá phải nhất quán với kịch bản vĩ mô.

## VIII. PARAM THAM CHIẾU (neo môi giới ≤3 tháng — kiểm hạn)
| | SSI (23/03) | MBS (10/03) | Shinhan (TCB) |
|---|---|---|---|
| Phương pháp | P/B mục tiêu (+RI) | **RI 50% + P/B 50%** | **SOTP** |
| COE | — | **14,8%** (Rf4%+β1,3×ERP8,5%) | — |
| g | — | 3,0% | — |
| P/B mục tiêu | 0,9x (thận trọng) | 1,2x (=TB 3 năm) | mẹ 1,5x + TCBS 2,5x |
| Quan điểm | thận trọng (nợ xấu thời vụ) | lạc quan | SOTP |
> Param ngành (MBS 03/2026): TB NHTMCP tư nhân forward P/B ~1,5x · P/E ~7,8x · ROE ~18% · ROA ~1,7%; SOCB P/B ~2,1x.

---

## ĐẦU RA (OUTPUT) — format định giá
1. **Kết luận**: overvalued / fair / undervalued + **biên an toàn** (% chiết khấu/phụ trội so giá trị nội tại).
2. **RI model**: COE (Rf/β/ERP), ROE path & fade, g, BV adjusted → giá trị/cp (bull/base/bear).
3. **P/B mục tiêu**: justified P/B, P/B lịch sử percentile, đường hồi quy ngành → P/B mục tiêu × BVPS fwd.
4. **(SOTP nếu có công ty con trọng yếu).**
5. **Định giá tương đối** + **lịch sử percentile** (dựng từ DataPro).
6. **Bảng độ nhạy** (COE × credit cost; P/B mục tiêu × credit cost) + **kịch bản gắn driver**.
7. **Target 12M** (xác suất-gia quyền) + dải + **khuyến nghị** + vùng mua.
8. **Catalysts** tái định giá (định lượng).

## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)
1. Dùng **ROE/earnings chuẩn hóa từ task FA**, KHÔNG dùng ROE danh nghĩa bị tô. Điều chỉnh book cho thiếu hụt dự phòng.
2. **vnstock ratio lỗi thời** → P/B/P/E lịch sử dựng từ **DataPro giá × số liệu BCTC**; ROE/BVPS từ vnstock income+balance. β tính từ DataPro (2Y tuần).
3. **Báo cáo môi giới chỉ neo nếu ≤3 tháng**; cross-check ≥2 nguồn; mâu thuẫn nêu rõ. Không bịa số.
4. Không cộng trùng RI hợp nhất + SOTP.
