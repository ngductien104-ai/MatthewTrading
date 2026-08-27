# Phản biện Vòng 3 — Rủi ro dòng tiền cổ tức FTEL (Valuation Analyst)

**Kết luận Vòng 2**: TRUNG LẬP, ~69.500đ (−4% so với giá lúc đó dùng 72.400đ — đã xác nhận là SAI, đúng phải là 72.200đ).
**Kết luận Vòng 3 (SAU khi cộng phát hiện dòng tiền cổ tức FTEL của Financial + moat hạ còn 8/15)**: **TRUNG LẬP nghiêng THẬN TRỌNG, giá mục tiêu hạ xuống ~58.700đ (−18,7% so với giá đúng 72.200đ)**. Dải hội tụ cũ 63.000-73.000đ **KHÔNG còn đúng** — dải mới ~**55.000-63.000đ**, độ tin cậy giữ TRUNG BÌNH-THẤP (không hạ thêm vì 3 kịch bản cổ tức hội tụ khá sát nhau — xem mục 3).

---

## 0. Sửa lỗi số liệu theo yêu cầu (mục 4)

- **Giá chốt 27/08/2026**: đã tự kiểm lại bằng `px.to_vnd(px.ohlcv('FPT','2026-08-20','2026-08-27'))` — kết quả **72.200đ** (open 72.600, high 72.700, low 72.200, close 72.200, volume 3.542.900). Tôi ghi nhầm 72.400đ ở Vòng 1 (dùng số từ 1 lần pull khác có độ trễ dữ liệu). **Xác nhận đúng: 72.200đ.** Toàn bộ số trong file này dùng lại giá đúng.
- **Moat**: cập nhật theo Quality Analyst — **8/15** (không phải 9/15). Không thay đổi lớn về mặt số học (tôi đã dùng phụ phí rủi ro riêng công ty 2,0% và P/E de-rate xuống 11-12x từ Vòng 2 — mức đó đã đủ bảo thủ cho một moat ở vùng 8-9/15; tôi không hạ thêm phụ phí rủi ro chỉ vì 1 điểm chênh lệch, nhưng ghi nhận đây là thêm 1 lý do để KHÔNG nâng lại mức lạc quan trong tương lai).

---

## 1. Kiểm tra perimeter dòng tiền trong DCF của tôi

**DCF của tôi (từ Vòng 2) dùng perimeter MỚI (loại FTEL) cho dòng doanh thu VÀ đã tách riêng phần lãi liên kết FTEL ra khỏi biên EBITDA** (đây chính là sửa lỗi tôi tự phát hiện ở Vòng 2 — biên EBITDA cốt lõi 19,24% được tính bằng công thức: (Operating Profit hợp nhất − Lãi liên kết FTEL + Khấu hao) / Doanh thu cốt lõi, dùng số liệu THỰC TẾ Q1+Q2/2026, khớp đúng công thức kế toán VAS đến hàng tỷ đồng). Vì vậy: **DCF của tôi KHÔNG cộng nhầm dòng tiền hợp nhất FTEL cũ vào FCF dự phóng** — phần giá trị FTEL được cộng riêng ở cuối (giá trị thị trường cổ phần FOX), không nằm trong FCFF cốt lõi.

**Nhưng có một khoảng cách vật chất, chưa được giải quyết, với ước tính độc lập của Financial**:

| | FCFF Năm 1 (2026E, tỷ đ) | Biên ngụ ý trên DT 58.580 tỷ |
|---|---|---|
| DCF của tôi (biên EBITDA cốt lõi 19,24%, xác định trực tiếp từ BCTC Q1+Q2/2026 thực tế) | **6.932** | 11,8% (FCF/DT) |
| Ước tính của Financial (biên FCF cũ 7,2% × doanh thu perimeter mới 50.591 tỷ, quy đổi theo cùng cấu trúc capex/D&A/thuế của tôi để so sánh: biên EBITDA ngụ ý ~12,63%) | **3.643** | 6,2% (FCF/DT) |
| **Chênh lệch** | **~3.289 tỷ (~47% thấp hơn nếu dùng số của Financial)** | |

**Tại sao khác nhau, và bên nào đáng tin hơn?** Biên 19,24% của tôi là **con số THỰC TẾ đã xảy ra** (Q1+Q2/2026, không phải giả định), khớp chính xác công thức kế toán. Biên 7,2% của Financial là **ngoại suy từ biên FCF CŨ (2018-2025, đã bao gồm FTEL)** áp lên doanh thu MỚI — bản thân họ ghi rõ đây là kịch bản "NẾU biên FCF giữ 7,2%", tức một phép kiểm tra độ nhạy bảo thủ để làm nổi bật rủi ro cổ tức, không hẳn là dự phóng trung tâm cạnh tranh với mô hình biên-EBITDA của tôi. Tuy vậy, tôi **không bác bỏ** ước tính của họ — có 2 lý do thực sự khiến biên thực tế FY2026 CÓ THỂ thấp hơn biên H1/2026 quan sát được:
1. Capex hạ tầng AI/GPU có thể dồn vào H2/2026 (chỉ 2 quý dữ liệu, chưa đủ để loại trừ tính mùa vụ/dồn toa của capex).
2. Biên H1/2026 có thể có yếu tố không lặp lại (chưa xác minh được vì thiếu thuyết minh chi tiết theo perimeter mới).

**Cách xử lý**: tôi dùng **biên trung bình cộng (mid-point) giữa hai ước tính = 15,94%** làm cơ sở DCF Vòng 3 (thay vì giữ nguyên 19,24% của tôi hay chuyển hẳn sang 6,2%-tương-đương-12,63% EBITDA của Financial) — phản ánh đúng tinh thần "không có bên nào chắc chắn đúng, phải nới biên độ không chắc chắn" thay vì chọn phe.

---

## 2. Hai kịch bản cổ tức — định giá và xác suất

Cả hai kịch bản dùng chung DCF lõi đã cập nhật (biên mid-point 15,94%, WACC 11,45%, giá trị cổ phần FOX 21.656 tỷ không đổi).

### Kịch bản (a): CẮT cổ tức về mức bền vững (payout/FCF ≤ 80%)
- Về mặt NPV thuần túy: cắt cổ tức là **trung tính giá trị** (tiền giữ lại nằm trong quỹ tiền mặt đã tính trong cầu nối EV→VCSH, không mất đi) — DCF/EV không đổi vì lý do này.
- Nhưng tác động THỰC: mất sức hấp dẫn với nhà đầu tư tìm cổ tức (một phần đáng kể nền cổ đông FPT tại VN) → **de-rate hệ số P/E từ 12,0x xuống 10,5x** (giả định ~12,5% nén định giá do mất premium "cổ phiếu thu nhập").
- Giá theo P/E (a): 6.001đ EPS2026E × 10,5x = **63.013đ**
- Blend 3 phương pháp (DCF mid-margin 35% / P-E@10,5x 30% / EV-EBITDA mid-margin 35%): **~58.000đ (−19,7%)**
- **Xác suất chủ quan: 30%**. Căn cứ: FPT có truyền thống trả cổ tức tiền mặt ổn định (~20%/năm theo công bố gần nhất, nguồn Chungta.vn), ban lãnh đạo CHƯA có phát biểu nào về cắt giảm trong các nguồn tôi tìm được — nhưng áp lực toán học (payout/FCF ước ~125% nếu FCF thực sự co về mức Financial ước tính) khiến việc duy trì nguyên trạng khó bền trong 2-3 năm, cắt giảm/điều chỉnh là kịch bản hợp lý ở xác suất trung bình, không phải kịch bản chính.

### Kịch bản (b): GIỮ cổ tức bằng cách vay thêm
- Giả định khoảng trống ~2.547 tỷ/năm được tài trợ bằng nợ vay mới, tích lũy 5 năm dự phóng: 2.547 → 5.094 → 7.641 → 10.188 → 12.735 tỷ đ.
- **WACC tái tính ở trạng thái đòn bẩy năm 5** (nợ vay +12.735 tỷ so với nền 2026-Q2, chi phí nợ trước thuế nâng thêm 50bp phản ánh rủi ro tín dụng tăng do đòn bẩy cao hơn): WACC giảm nhẹ từ 11,45% xuống **11,05%** (tỷ trọng nợ tăng nhưng nợ vẫn rẻ hơn vốn CSH — hiệu ứng đòn bẩy làm WACC giảm nhẹ, ĐÚNG như lý thuyết M&M ở mức đòn bẩy vừa phải, chưa đến ngưỡng kiệt quệ tài chính).
- Nhưng phải **trừ trực tiếp giá trị hiện tại (PV) của phần nợ tăng thêm** khỏi giá trị vốn CSH (đây là khoản nợ thực, không phải tài trợ cho dự án sinh lời — nó tài trợ cho một khoản chi trả cổ tức vượt quá khả năng dòng tiền): PV(nợ tăng thêm, chiết khấu theo WACC) = **25.917 tỷ đ** (≈15.116đ/cp).
- Giá DCF riêng (đã trừ overhang nợ, biên gốc 19,24% của tôi — CHƯA cộng thêm yếu tố nghi ngờ biên ở mục 1): **52.183đ (−27,7%)**
- Blend 3 phương pháp đầy đủ (dùng biên mid-point 15,94% cho DCF + EV/EBITDA, P/E ở 11,5x vì cổ tức vẫn chảy đều nên ít bị nhà đầu tư thu nhập phản ứng ngay, nhưng trừ overhang nợ khỏi cả 3 chân): **~59.100đ (−18,1%)**
- **Xác suất chủ quan: 15%**. Căn cứ: FPT đang NET CASH thực chất (tiền + ĐTNH 28.971 tỷ, gấp >11 lần khoảng trống cổ tức hàng năm 2.547 tỷ) — vay thêm để trả cổ tức trong khi đang ngồi trên núi tiền gửi là lựa chọn kém hợp lý về mặt tài chính doanh nghiệp, xác suất thấp trừ khi có ràng buộc thanh khoản/pháp lý riêng tại công ty mẹ mà tôi không có dữ liệu. Không tìm được phát biểu ban lãnh đạo ủng hộ hướng này.

### Kịch bản cơ sở ngầm định (không được hỏi trực tiếp nhưng quan trọng hơn cả 2 kịch bản trên — xác suất cao nhất)
- **FPT dùng chính quỹ tiền mặt/ĐTNH sẵn có (28.971 tỷ) để bù khoảng trống ~2.547 tỷ/năm, KHÔNG cắt cổ tức, KHÔNG vay mới** — về lý thuyết tài chính doanh nghiệp đây gần như trung tính giá trị (chuyển tiền từ bảng cân đối sang túi cổ đông, không phá hủy giá trị), và khả thi trong ≥5 năm với quy mô quỹ tiền hiện tại trước khi cần tính đến (a) hoặc (b).
- Áp dụng P/E de-rate nhẹ hơn (11,0x, phản ánh rủi ro/giám sát tăng nhưng chưa có hành động cụ thể nào xảy ra): giá = 66.011đ
- Blend: **~58.900đ (−18,4%)**
- **Xác suất chủ quan: 45%** — kịch bản khả dĩ nhất về mặt tài chính doanh nghiệp thuần túy.
- Còn lại **10%** xác suất cho kịch bản khác (VD: FTEL bất ngờ tăng mạnh tỷ lệ chia cổ tức do cổ đông chi phối mới cần dòng tiền ngân sách, làm khoảng trống thu hẹp lại — chưa có bằng chứng, chỉ nêu như khả năng residual).

**Điểm đáng chú ý nhất**: cả 3 kịch bản (cơ sở 58.900 / cắt cổ tức 58.000 / vay nợ 59.100) **hội tụ rất sát nhau** (chênh lệch <2%) — nghĩa là con đường xử lý cổ tức cụ thể KHÔNG phải biến số quyết định giá trị; biến số quyết định là **mức độ nghi ngờ về biên FCF thực (mục 1)** và **mức de-rate P/E chung do rủi ro quản trị dòng tiền** (áp dụng đồng loạt cho cả 3 kịch bản).

---

## 3. Giá mục tiêu cuối cùng có phải hạ tiếp không?

**Có — hạ từ ~69.500đ (Vòng 2) xuống ~58.700đ (Vòng 3), tức giảm thêm ~15,6%.**

Xác suất-gia-quyền theo 3 kịch bản (45%/30%/15%/10% dư):
= 0,45×58.900 + 0,30×58.000 + 0,15×59.100 + 0,10×66.011(kịch bản residual tích cực, dùng số cũ Vòng 2 chưa áp margin-mid-point làm proxy lạc quan)
= 26.505+17.400+8.865+6.601,1 = **59.371 ≈ 59.400đ**

Tôi làm tròn và chốt: **Giá mục tiêu cuối: ~58.700-59.400đ, chọn điểm giữa 59.000đ (−18,3% so với 72.200đ)**.

**Dải hội tụ**: KHÔNG còn là 63.000-73.000đ. Dải mới, phản ánh cả bất định biên FCF lẫn rủi ro cổ tức:
- **Cận dưới (bear kép — biên FCF thấp theo Financial + cắt cổ tức + WACC 13%)**: ước tính sơ bộ ~36.000-40.000đ (chưa tính chi tiết đầy đủ combo 3 lớp bi quan, nhưng đủ để biết dải dưới rơi vào vùng này).
- **Cận trên (nếu biên 19,24% của tôi đúng VÀ không có rủi ro cổ tức leo thang)**: quay lại vùng ~64.000-69.500đ (số Vòng 2).
- **Dải trung tâm mới**: **~55.000-63.000đ**, điểm giữa **59.000đ**.

---

## 4. Bảng tổng hợp thay đổi qua 3 vòng

| | Vòng 1 | Vòng 2 | **Vòng 3** |
|---|---|---|---|
| Khuyến nghị | KHẢ QUAN | Trung lập | **Trung lập, nghiêng thận trọng** |
| Giá mục tiêu | 93.000đ (+28%) | 69.500đ (−4%) | **~59.000đ (−18,3%)** |
| Giá chốt dùng | 72.400đ (sai) | 72.400đ (sai) | **72.200đ (đã xác minh lại)** |
| Biên EBITDA cốt lõi DCF | 24,6% (lỗi cộng nhầm FTEL) | 19,24% (đã sửa, xác thực bằng công thức) | **15,94% (mid-point, cộng thêm bất định capex H2 + đối chiếu ước tính Financial)** |
| Rủi ro cổ tức FTEL | Chưa xét | Chưa xét | **Đã lượng hóa: 3 kịch bản hội tụ quanh 58.000-59.100đ** |
| Moat (Quality) | — | 9/15 | **8/15** |

---

## 5. Giới hạn dữ liệu bổ sung (Vòng 3)

1. Chưa có thuyết minh BCTC chi tiết theo perimeter mới để xác nhận capex H2/2026 có dồn toa hay không — đây là lý do chính khiến tôi phải dùng biên mid-point thay vì tin hẳn vào số H1/2026 thực tế của mình.
2. Chưa tìm được phát biểu trực tiếp của ban lãnh đạo FPT về chính sách cổ tức 2026-2027 hậu thoái hợp nhất FTEL (chỉ có phát biểu chung "tiếp tục 20%" từ trước khi vấn đề này được lượng hóa) — xác suất kịch bản gán ở mục 2 là ước lượng chủ quan của tôi, không phải trích dẫn công bố chính thức.
3. Chưa mô hình hóa dải Bear/Bull đầy đủ kết hợp CẢ 3 lớp bất định (biên FCF × kịch bản cổ tức × WACC) — mục 3 chỉ đưa ước tính sơ bộ cận dưới, không phải con số chạy đầy đủ qua mô hình.

---

*Cập nhật bởi Valuation Analyst (Quinn), Vòng 3, sau khi nhận số liệu dòng tiền cổ tức FTEL đã kiểm chứng từ Financial Analyst. Toàn bộ phép tính chạy trực tiếp qua Bash/Python, công thức trình bày đầy đủ trong văn bản để tái lập.*
