---
name: valuation-model
description: "Định giá cổ phiếu Việt Nam THEO NGÀNH — phân loại ngành trước, rồi chọn bộ phương pháp phù hợp (ngân hàng→RIM, BĐS→RNAV, chu kỳ→EV/EBITDA chuẩn hóa, sản xuất/tiêu dùng→DCF, holdings→SOTP). Kèm thư viện phương pháp, độ nhạy, bẫy định giá. Nguồn: vnstock + DataPro."
category: analysis
---

# Định giá cổ phiếu Việt Nam (theo ngành)

## Tổng quan

**Không có phương pháp định giá vạn năng.** Nguyên tắc cốt lõi: **phân loại ngành trước → chọn bộ phương pháp phù hợp với mô hình kinh doanh và bản chất tài sản của ngành đó**, rồi kiểm chứng chéo ≥2 phương pháp. Ngân hàng định giá khác sản xuất; bất động sản khác hàng tiêu dùng; DN chu kỳ khác DN tăng trưởng ổn định.

> ⚠️ **Trước khi tính (checklist Karpathy):** số CP lưu hành = `Company.overview().issue_share` (KHÔNG suy từ EPS); β **tự tính từ DataPro full-history**, nêu cửa sổ + R²; bóc khoản một lần trước khi annualize; tính ≥2 cách khi nhạy cảm (ROIC, WACC, Ke).

## Bước 0 — Phân loại ngành (quyết định phương pháp)

**Cách TỰ ĐỘNG (khuyến nghị):** chạy script đi kèm — nó đọc `is_bank/sector/icb_code_lv2` từ vnstock và TRẢ THẲNG bộ phương pháp:

```bash
python classify_valuation.py VCB            # 1 mã
python classify_valuation.py FPT HPG VHM    # nhiều mã
```
→ in ra: ngành, khung áp dụng, phương pháp CHÍNH / kiểm chứng chéo / TRÁNH / động lực giá trị + cảnh báo (BĐS KCN, holding→SOTP).
Hoặc import: `from classify_valuation import classify_valuation; rec = classify_valuation("VCB")`.

**Logic phân loại:** `is_bank=True` → **Ngân hàng (RIM/PB-ROE/DDM)**; còn lại map theo `sector` (vd "Real Estate"→RNAV, "Basic Resources"→EV/EBITDA chu kỳ), lùi về `icb_code_lv2` nếu thiếu. ICB **không** tách BĐS nhà ở vs KCN và không gắn cờ holding → script nêu cảnh báo để xét tay; tập đoàn đa ngành → **SOTP**.

## Bản đồ Ngành → Phương pháp định giá

| Ngành (ICB) | Phương pháp CHÍNH | Kiểm chứng chéo | TRÁNH | Động lực giá trị / lưu ý |
|------|---------|------|------|------|
| **Ngân hàng** | **RIM**, P/B–ROE | DDM | DCF/FCFF, EV/EBITDA | ROE, NIM, NPL/LLR, CASA, CAR (TT41), tăng trưởng tín dụng |
| **Chứng khoán** | P/B, **SOTP** (môi giới + cho vay margin + tự doanh) | RIM | DCF, EV/EBITDA | ROE chuẩn hóa, dư nợ margin, phụ thuộc tự doanh (FVTPL) — LN rất biến động |
| **Bảo hiểm** | P/B–ROE (nhân thọ: Embedded Value) | P/E | DCF | LN đầu tư + kỹ thuật (combined ratio) |
| **BĐS nhà ở** | **RNAV** | P/B (cẩn trọng), presales | **P/E** (LN giật cục theo bàn giao), EV/EBITDA | Quỹ đất, pháp lý dự án, presales (người mua trả tiền trước), đòn bẩy |
| **BĐS Khu công nghiệp** | **RNAV** + DCF dòng cho thuê | P/B | P/E | Quỹ đất cho thuê còn lại, giá thuê, tỷ lệ lấp đầy, đáo hạn thuê đất |
| **BĐS cho thuê / TTTM** | NAV theo cap rate (NOI/cap rate), EV/EBITDA | DCF | P/E | NOI, tỷ lệ lấp đầy, cap rate |
| **Thép / Vật liệu (chu kỳ)** | EV/EBITDA, P/B, **P/E chuẩn hóa giữa chu kỳ** | ROIC vs WACC | P/E hiện tại (bẫy đỉnh chu kỳ) | Công suất, biên (giá bán − giá nguyên liệu), chu kỳ hàng hóa |
| **Xây dựng** | P/E điều chỉnh backlog, EV/EBIT | P/B | EV/EBITDA thuần | Backlog hợp đồng, vòng quay vốn lưu động, rủi ro phải thu |
| **Sản xuất / Công nghiệp** | **DCF (FCFF)**, EV/EBITDA | P/E, ROIC vs WACC | — | ROIC vs WACC, công suất, biên |
| **Hàng tiêu dùng (TP&ĐU)** | **DCF**, P/E | EV/EBITDA, DDM | — | Thương hiệu, biên gộp, tăng trưởng sản lượng |
| **Bán lẻ** | EV/EBITDA, P/E | EV/Sales (giai đoạn tăng trưởng) | — | LFL sales, store economics, vòng quay tồn kho |
| **Công nghệ / CNTT** | DCF, P/E, **PEG** | EV/EBITDA, EV/Sales (SaaS) | — | Tăng trưởng, biên, backlog dịch vụ |
| **Tiện ích (Điện/Nước/Khí)** | DCF, **DDM** | EV/EBITDA | — | Dòng tiền ổn định/điều tiết, cổ tức, hợp đồng PPA |
| **Dầu khí** | EV/EBITDA, EV/trữ lượng | DCF, NAV | P/E | Giá dầu, trữ lượng (1P/2P), sản lượng |
| **Logistics / Cảng** | EV/EBITDA, DCF | P/E | — | Sản lượng thông qua, công suất, phí dịch vụ |
| **Dược / Y tế** | DCF, P/E | EV/EBITDA | — | Danh mục sản phẩm, kênh ETC/OTC |
| **Nông nghiệp / Thủy sản** | P/E chuẩn hóa, EV/EBITDA | P/B | P/E hiện tại | Giá hàng hóa, chu kỳ, tỷ giá xuất khẩu |
| **Holdings / Đa ngành** | **SOTP** | RNAV/PB từng mảng | bội số gộp toàn tập đoàn | Định giá từng mảng − chiết khấu holding |
| **DN đang lỗ / early-stage** | P/S, EV/Sales, EV/GMV | — | P/E | Tăng trưởng doanh thu, đường tới hòa vốn |

---

# Thư viện phương pháp

## A. DCF — Chiết khấu dòng tiền (sản xuất / tiêu dùng / công nghệ / tiện ích)

```
EV = Σ FCFF_t / (1+WACC)^t + TV/(1+WACC)^n ;  Giá trị vốn chủ = EV − Nợ ròng
Giá/cổ phần = Giá trị vốn chủ / issue_share
FCFF = EBIT×(1−T) + Khấu hao − Capex − Tăng vốn lưu động   (≈ CFO − Capex)

WACC = E/(D+E)×Ke + D/(D+E)×Kd×(1−T)
Ke = Rf + β×ERP   (Rf = TPCP 10 năm ~3-5%; β tự tính DataPro; ERP VN ~7-9%)
Kd = chi phí lãi vay/nợ vay bình quân ; T = 20%
TV = FCF_n×(1+g)/(WACC−g)   (g 2-4%, ≤ tăng trưởng GDP danh nghĩa)
```
Độ nhạy bắt buộc: ma trận WACC × g (mỗi 1% WACC dịch định giá ~20%).

## B. DDM — Chiết khấu cổ tức (tiện ích, ngân hàng cổ tức cao, tiêu dùng trưởng thành)

```
Hai giai đoạn: P = Σ D_t/(1+Ke)^t + D_n(1+g)/[(Ke−g)(1+Ke)^n]
Gordon: P = D_1/(Ke−g)
```
Điều kiện: cổ tức tiền mặt đều >3 năm, payout ổn định >30%.

## C. RIM — Thu nhập thặng dư (NGÂN HÀNG / tài chính)

**Vì sao ngân hàng không dùng DCF:** lãi vay (huy động) là đầu vào kinh doanh cốt lõi → FCFF không định nghĩa được; vốn bị ràng buộc bởi **CAR (TT41, Basel II, ≥8%)**; giá trị sổ sách vốn chủ là thước đo kinh tế đáng tin.

```
V0 = B0 + Σ RI_t/(1+Ke)^t + TV/(1+Ke)^n
RI_t = NI_t − Ke×B_{t-1} = (ROE_t − Ke)×B_{t-1}
B_t = B_{t-1} + NI_t − Div_t          (clean surplus)
TV = RI_{n+1}/(Ke−g)  hoặc (Ohlson) RI_n×ω/(1+Ke−ω), ω = hệ số duy trì

→ P/B hợp lý (một giai đoạn) = (ROE − g)/(Ke − g)   ← cầu nối với PB-ROE
```

**Ví dụ (số giả định):** ROE bền vững 15%, Ke 13%, g 4% → P/B hợp lý = (0,15−0,04)/(0,13−0,04) = **1,22x**.

**Đặc thù ngân hàng VN:** B0 = `owners_equity`; NI = `net_profit_loss_after_tax`; **chuẩn hóa chi phí tín dụng** (bóc trích lập/hoàn nhập dự phòng bất thường); g bền vững bị giới hạn bởi **CAR**; chú ý **pha loãng** (tăng vốn, cổ tức cổ phiếu → issue_share thật); soi **NPL/LLR** (B "ảo" nếu dự phòng thiếu).

## D. RNAV — Giá trị tài sản ròng đánh giá lại (BẤT ĐỘNG SẢN)

**Vì sao BĐS nhà ở không dùng P/E:** doanh thu ghi nhận khi **bàn giao** (VAS) → lợi nhuận giật cục theo dự án, P/E hiện tại vô nghĩa. **P/B cũng là bẫy:** hàng tồn kho/quỹ đất ghi theo **giá vốn**, thấp xa giá thị trường → book bị định giá thấp.

```
RNAV = Σ Giá trị thị trường (đánh giá lại) từng dự án/quỹ đất
       + Tài sản khác theo giá thị trường − Nợ ròng − thuế/chi phí tiềm ẩn khi hiện thực hóa

Giá trị mỗi dự án = NPV dòng tiền dự án (DCF từng dự án)
   hoặc = Diện tích thương phẩm × (giá bán kỳ vọng − chi phí phát triển còn lại) × xác suất triển khai
Giá mục tiêu = (RNAV / issue_share) × (1 ± premium/discount)
   discount theo: pháp lý chưa hoàn thiện, quản trị, đòn bẩy cao, thanh khoản quỹ đất
```

**Động lực & dữ liệu cần (ngoài BCTC):** quỹ đất & pháp lý từng dự án, tiến độ bán hàng (**presales** = "Người mua trả tiền trước"/"Doanh thu chưa thực hiện" trên CĐKT = backlog đã chốt), giá bán khu vực. → Cần bổ sung từ báo cáo thường niên / bản cáo bạch (dùng skill `web-reader`/firecrawl); BCTC vnstock chỉ cho số sổ sách (giá vốn).

**Biến thể KCN:** RNAV quỹ đất cho thuê còn lại + DCF dòng tiền cho thuê định kỳ. **Cho thuê/TTTM:** NAV = NOI / cap rate.

## E. SOTP — Định giá từng phần (HOLDINGS / đa ngành)

```
Giá trị tập đoàn = Σ định giá từng mảng (THEO PHƯƠNG PHÁP CỦA NGÀNH mảng đó)
                 + tiền ròng − chiết khấu holding (10-20%)
```
Ví dụ: mảng ngân hàng → RIM; mảng BĐS → RNAV; mảng bán lẻ → EV/EBITDA; rồi cộng lại, trừ chiết khấu.

## F. Định giá tương đối

- **PE Band:** phân vị PE_TTM 5 năm (10/25/50/75/90%) so với hiện tại. Tránh cho DN chu kỳ/BĐS.
- **PB-ROE:** `P/B hợp lý = (ROE−g)/(Ke−g)`; đồ thị PB (tung) vs ROE (hoành), vùng "PB thấp + ROE cao" = mua tốt. Chuẩn cho ngân hàng/tài chính.
- **EV/EBITDA:** `EV = vốn hóa + nợ ròng`. Loại khác biệt cấu trúc vốn & khấu hao; hợp tài sản nặng. **KHÔNG dùng cho ngân hàng.**
- **P/S, EV/Sales:** DN đang lỗ / tăng trưởng cao chưa có lợi nhuận.

## Nhận diện bẫy định giá

| # | Bẫy | Phát hiện |
|---|------|---------|
| 1 | P/E thấp đỉnh chu kỳ | P/E thấp nhất khi LN đỉnh sắp đảo (thép, hóa chất) → dùng LN chuẩn hóa |
| 2 | P/B thấp BĐS là BẪY | Tồn kho/quỹ đất ghi giá vốn → dùng RNAV, không phải P/B |
| 3 | P/B thấp huỷ hoại giá trị | `ROE < Ke` kéo dài → huỷ hoại giá trị cổ đông |
| 4 | PE cao có thể hợp lý | `PEG < 1` = tăng trưởng đỡ được định giá |
| 5 | Bom lợi thế thương mại | LTTM/vốn CSH >30% → rủi ro tổn thất |
| 6 | Lãi một lần | Chênh LN cốt lõi vs báo cáo (thanh lý/đánh giá lại/tỷ giá) |
| 7 | Pha loãng | ESOP/CB/tăng vốn → dùng EPS pha loãng & issue_share thật |
| 8 | Bẫy phải thu | Phải thu/doanh thu tăng = chất lượng doanh thu kém |
| 9 | Giao dịch bên liên quan | Chuyển lợi nhuận ra ngoài DN niêm yết |
| 10 | Tỷ giá | Tỷ trọng doanh thu/nợ ngoại tệ cao |

## Kiểm chứng chéo & mẫu output

```markdown
## Phân tích định giá: [Tên DN / Mã .VN]  — Ngành: [ICB], is_bank=[T/F]

### Phương pháp áp dụng (theo ngành): [vd BĐS → RNAV + presales]

### Tổng hợp định giá
| Phương pháp | Giá/cổ phần | Trọng số | Ghi chú |
|------|---------|------|------|
| [Chính theo ngành] | ... | 50-60% | giả định lõi |
| [Kiểm chứng chéo] | ... | 30-40% | |
| **Giá mục tiêu** | **...** | | Giá hiện tại ..., tiềm năng ±..% |

### Độ nhạy
[ma trận WACC×g / Ke×g / cap rate]

### Soát bẫy định giá
- [ ] (theo ngành) ...

### Khuyến nghị: [MUA/NẮM GIỮ/BÁN], giá mục tiêu ..., tiềm năng ...%
```

**Quy tắc:** luôn ≥2 phương pháp; lệch >30% → soát lại giả định. Định giá là điểm neo, không phải tín hiệu giao dịch tức thời.

## Nguồn dữ liệu

- **Phân loại ngành → vnstock** `Company.overview()`: `is_bank`, `sector`, `icb_code_lv2/lv4`; hoặc `Listing.symbols_by_industries()` → `icb_name`.
- **BCTC → vnstock nguồn KBS** (`Finance(source="kbs", ...)`, chi tiết theo VAS): dùng KEY SẠCH (loader tự ánh xạ + xử lý quirk KBS): `net_sales`, `gross_profit`, `net_profit_loss_after_tax`, `attributable_to_parent_company`, `owners_equity` (B0/RIM — thực ở KBS là `owners_equity_2`, đã map sẵn), `total_assets`, `short_term_borrowings`, `long_term_borrowings`, `cash_and_cash_equivalents` (nợ ròng), CFO (`net_cash_inflows_outflows_from_operating_activities`), `eps`.
- **Chỉ số định giá/sinh lời → vnstock bảng `ratio` (nguồn KBS)**: `from vnstock import Finance; Finance(source="kbs", symbol="X").ratio(period="year")` → SẴN `pe_ratio`, `pb_ratio`, `ps_ratio`, `ev_ebit`, `ev_ebitda`, `roe`, `roa`, `net_margin`, `beta`, `dividend_yield`, tăng trưởng...; ngân hàng có `net_interest_margin_nim`. *(Dùng KBS, KHÔNG dùng VCI cho ratio — VCI trả layout kỳ lỗi.)*
- **Giá / vốn hóa / β → DataPro** (`source="datapro"`, mã `.VN`); **β tự tính regress vs VNINDEX full-history** (nêu cửa sổ + R²) cho WACC; `ratio.beta` của KBS chỉ dùng kiểm chứng nhanh.
- **issue_share / market_cap / target_price → `Company.overview()`.**
- **RNAV / quỹ đất / presales / backlog → báo cáo thường niên + `web-reader`/firecrawl** (BCTC chỉ cho số sổ sách giá vốn).
- ⚠️ vnstock KBS bản community trả ~4 kỳ năm gần nhất.


## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)

1. **Không bịa/cook số liệu.** Mọi số tài chính phải có nguồn thật. Luôn **audit nhanh, cross-check tối thiểu 2 nguồn uy tín** (vd `cafef.vn`, `vietstock.vn`) — dùng **crawl4ai** cào số rồi đối chiếu; nếu nguồn lệch nhau thì nêu rõ, không chọn bừa.
2. **Nếu DataPro VÀ vnstock đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
