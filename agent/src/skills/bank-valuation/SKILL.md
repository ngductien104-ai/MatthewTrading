---
name: bank-valuation
description: "Định giá NGÂN HÀNG TMCP Việt Nam (buy-side/IB) — KHÔNG DCF/FCF. Lõi: Residual Income (COE per-bank = Rf TPCP10Y + β·ERP, ROE fade về bền vững, g 3-4%) + P/B mục tiêu (justified Gordon + hồi quy P/B–ROE chéo ngành + P/B lịch sử percentile); SOTP cho NH có công ty con trọng yếu (TCBS/FE Credit…); reverse-Gordon (variant perception); kịch bản + độ nhạy 2 chiều. Dùng ROE/earnings CHUẨN HÓA từ task Financial Analysis. β & P/B lịch sử dựng từ DataPro; Rf TPCP10Y crawl; neo môi giới ≤3 tháng. TASK RIÊNG với FA."
category: analysis
---

# Định giá Ngân hàng TMCP Việt Nam (buy-side · Valuation Analyst)

## Vai trò & nguyên tắc
Senior Valuation Analyst, đa mô hình cross-validation, ngành ngân hàng VN. **Task RIÊNG với Financial Analysis** — nhận **ROE/earnings power CHUẨN HÓA** + adjusted book từ task FA, KHÔNG phân tích lại BCTC. **NH KHÔNG dùng DCF/FCF** (dòng tiền không phải FCF) → định giá trên **vốn chủ sở hữu**. Khung dài: `_bankdata/_FRAMEWORK_VALUATION_NGANHANG.md`. Khi nào dùng: sau khi có báo cáo FA của mã (is_bank).

---

## 1. ROUTING DỮ LIỆU ĐẦU VÀO (đã audit)

### Từ task Financial Analysis (bắt buộc)
- **ROE chuẩn hóa** (through-cycle, không dùng ROE danh nghĩa bị tô) — vd TPB ~14% (≠18%).
- **Earnings power chuẩn hóa** (PPOP − credit cost qua chu kỳ − one-off); **adjusted book** = VCSH − thiếu hụt dự phòng [NPL×(coverage mục tiêu − hiện tại)] − lãi dự thu kém chất lượng.
- BVPS, VCSH, SLCP, chất lượng tài sản, NIM/credit-growth outlook.

### β (beta) — tính từ DataPro ✅ (chuẩn institution: 2Y khung TUẦN — [[feedback-beta-institution-standard]])
```python
# DataPro: agent/backtest/loaders/datapro_loader.DataLoader().fetch(symbol, from, to)  (hoặc MCP get_daily)
# Lấy ~2 năm giá NGÀY (adjusted) của mã + VNINDEX → resample TUẦN (W-FRI) → log return
# β = cov(r_stock, r_mkt) / var(r_mkt)
```
DataPro có giá điều chỉnh + `VNINDEX`. β bluechip ~1,0–1,1 (TCB/VCB), midcap cao hơn ~1,3 (TPB).

### Rf & ERP
- **Rf = lợi suất TPCP 10Y VN hiện tại** — crawl (investing.com / tradingeconomics / cafef / KBNN). **~4,4–4,5% (06/2026)** — dùng SỐ HIỆN TẠI, không bê số cũ của môi giới (MBS 03/2026 dùng 4,0%; nay đã ~4,47%).
- **ERP** (frontier VN) ~7–9% (MBS 8,5%). → **COE = Rf + β·ERP** (ngành 13–15%).

### P/B / P/E LỊCH SỬ — dựng từ DataPro (vnstock ratio LỖI THỜI)
```
P/B_t = (close_t × SLCP) / VCSH(kỳ gần t) ;  P/E_t = (close_t × SLCP) / NPAT(TTM)
```
DataPro `close` (adjusted) × SLCP / BVSH theo quý (vnstock) → chuỗi P/B lịch sử → **percentile** hiện tại + TB 3–5 năm. Nêu rõ window.

### Peer P/B–ROE (hồi quy chéo ngành)
Kéo ~15 NH (vnstock income+balance + `overview` market_cap) → ROE & P/B từng mã → **hồi quy `P/B = a + b×ROE`** → mã trên/dưới đường = đắt/rẻ tương đối. (Đặt nền từ bảng peer task FA.)

### Param môi giới ≤3 tháng (neo, kiểm hạn) + SOTP comps
Target/COE/g/P-B mục tiêu từ SSI/MBS/HSC/VCI/Shinhan ≤3 tháng. SOTP comps: TCBS (P/B ~2,5x), FE Credit, MCredit/MIC, HD Saison.

---

## 2. PHƯƠNG PHÁP (theo `_FRAMEWORK_VALUATION_NGANHANG.md`)

### I. Residual Income / Excess Return ⭐
`RI_t=(ROE_t−COE)×VCSH_(t-1)` → `Equity = VCSH_0(adj) + ΣPV(RI) + PV(terminal)`; terminal=`RI×(1+g)/(COE−g)`.
- **COE per-bank** (Rf hiện tại + β·ERP). **ROE FADE** từ ROE chuẩn hóa về ROE bền vững (không phẳng). g 3–4% (<COE).
- Roll-forward VCSH theo payout; cổ tức CP trung tính, tiền mặt giảm VCSH.

### II. P/B mục tiêu ⭐
`P/B Gordon=(ROE_bền−g)/(COE−g)`; `Giá=P/B mục tiêu×BVPS forward`. P/B mục tiêu neo: (a) Gordon, (b) **P/B lịch sử percentile**, (c) **đường hồi quy ngành** — điều chỉnh theo outlook chất lượng TS/ROE.

### III. SOTP (NH có công ty con trọng yếu)
NH mẹ (P/B theo ROE mẹ) + con định giá riêng (TCBS 2,5x…). **KHÔNG cộng trùng** RI hợp nhất + SOTP.

### IV. Tương đối + V. Reverse-Gordon
Peer multiples forward (P/B, P/E, P/B-ROE) vs TB ngành/dẫn đầu. **Reverse**: giá hiện hàm ý ROE/g bao nhiêu → so ROE chuẩn hóa của mình (variant perception).

### VI. Kịch bản & độ nhạy
Bull/base/bear **gắn driver** (credit cost, NIM, ROE, tăng trưởng tín dụng). **Bảng độ nhạy 2 chiều**: (COE × credit cost) & (**P/B mục tiêu × credit cost**) — NH có ROE≈COE thì giá cực nhạy.

### VII. Liên kết vĩ mô
Lãi suất→NIM & Rf/COE; chu kỳ BĐS→chất lượng TS & ROE; room tín dụng (nhóm nhận chuyển giao bắt buộc → tăng trưởng/ROE cao hơn). Định giá nhất quán kịch bản vĩ mô.

---

## 3. ĐẦU RA (OUTPUT)
1. **Kết luận**: overvalued/fair/undervalued + **biên an toàn** (% so giá trị nội tại).
2. **RI model**: COE (Rf/β/ERP — số hiện tại), ROE path & fade, g, BV adjusted → giá trị/cp (bull/base/bear).
3. **P/B mục tiêu**: Gordon + P/B lịch sử percentile + đường hồi quy ngành → P/B mục tiêu × BVPS fwd.
4. **SOTP** (nếu có công ty con trọng yếu).
5. **Tương đối + lịch sử percentile** (dựng từ DataPro).
6. **Bảng độ nhạy** (COE×credit cost; P/B mục tiêu×credit cost) + **kịch bản gắn driver**.
7. **Target 12M** (xác suất-gia quyền) + dải + **khuyến nghị** + vùng mua.
8. **Catalysts** tái định giá (định lượng).

---

## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)
1. Dùng **ROE/earnings CHUẨN HÓA từ task FA**, không dùng ROE danh nghĩa bị tô; adjusted book cho thiếu hụt dự phòng.
2. **Rf, β, P/B lịch sử dùng SỐ HIỆN TẠI tự dựng** (TPCP 10Y crawl; β & P/B từ DataPro) — **vnstock ratio lỗi thời**, không lấy. Không bê param cũ của môi giới khi thị trường đã đổi (vd Rf 4,0%→4,47%).
3. **Báo cáo môi giới chỉ neo nếu ≤3 tháng**; cross-check ≥2 nguồn; mâu thuẫn nêu rõ; **không bịa số**.
4. **Không cộng trùng** RI hợp nhất + SOTP. g < COE. Kiểm tra tính hợp lý P/B mục tiêu vs ROE (Gordon).
