# Phân tích Báo cáo Tài chính: FPT Corporation (HOSE: FPT)
**Vai trò**: Financial Analyst — Hội đồng nghiên cứu FPT
**Ngày phân tích**: 2026-08-27
**Nguồn dữ liệu**: `vnstock_data` qua lớp `vndata.fundamental` (BCTC hợp nhất, đơn vị VND), cross-check bằng web search (vietnambiz.vn, vietstock.vn, cafef.vn) cho sự kiện bất thường
**Số kỳ dữ liệu thực có**: 8 năm (2018–2025) + 6 quý gần nhất (2025-Q1 → 2026-Q2)
**Ghi chú áp dụng template**: FPT không phải ngân hàng/chứng khoán/bảo hiểm → dùng template chuẩn (biên lợi nhuận gộp, tồn kho, phải thu), không dùng NIM/NPL/CAR.

---

## ⚠️ Sự kiện cấu trúc quan trọng nhất — PHẢI đọc trước khi diễn giải số liệu 2026

Khi đối chiếu số liệu quý, tôi phát hiện **Tổng tài sản giảm đột ngột 19.552 tỷ đồng** giữa Q4/2025 (88.142 tỷ) và Q1/2026 (68.586 tỷ, khớp gần như tuyệt đối với số liệu tự tính từ `vndata`: 88.142 → 68.587 tỷ). Đây KHÔNG phải suy giảm hoạt động mà là **thay đổi phạm vi hợp nhất**:

- Tháng 7/2025, SCIC chuyển giao **50,17% cổ phần FPT Telecom (FTEL)** cho **Bộ Công an**. FPT chỉ còn giữ **45,66%** tại FTEL (trước đó FPT hợp nhất FTEL nhờ quyền kiểm soát thực tế dù sở hữu <50%).
- **Từ 01/01/2026**, FPT chuyển phương pháp hạch toán FTEL từ **hợp nhất** sang **vốn chủ sở hữu (equity method)** — coi FTEL là công ty liên kết, không còn là công ty con.
- Hệ quả: doanh thu hợp nhất giảm ước tính **~20.000 tỷ đồng/năm**; FPT dự báo DTT và LNTT cả năm 2026 giảm lần lượt **~16,6%** và **~10,8%** so với 2025 (theo hướng dẫn công ty, dẫn qua vietnambiz.vn). Tiền + tiền gửi giảm 13.800 tỷ về 26.800 tỷ tại thời điểm 31/3/2026.
- Công ty khẳng định **LNST thuộc cổ đông công ty mẹ (NPATMI) không bị ảnh hưởng** — vì theo equity method, FPT vẫn ghi nhận phần lãi tương ứng tỷ lệ sở hữu (45,66%) từ FTEL, chỉ mất phần doanh thu/chi phí gộp của FTEL trên báo cáo hợp nhất, không mất phần lợi nhuận thuộc về mình.
- Nguồn: [vietnambiz.vn](https://vietnambiz.vn/fpt-du-bao-lai-truoc-thue-nam-2026-giam-11-khi-khong-con-hop-nhat-voi-fpt-telecom-2026320212039109.htm), [vietstock.vn](https://vietstock.vn/2026/03/fpt-dieu-chinh-cach-hach-toan-ket-qua-kinh-doanh-fpt-telecom-tu-nam-2026-737-1413810.htm), [cafef.vn](https://cafef.vn/fpt-giam-20000-ty-doanh-thu-moi-nam-sau-mot-quyet-dinh-vi-sao-ong-truong-gia-binh-se-khong-lo-lang-188260319091806398.chn) — 3 nguồn khớp nhau về hướng và độ lớn.

**Ý nghĩa cho phân tích**: (1) Chuỗi 2018–2025 dưới đây **có thể so sánh nội bộ** (cùng phạm vi hợp nhất bao gồm FTEL). (2) Số liệu quý 2026 (2026-Q1, 2026-Q2) **KHÔNG so sánh YoY được ở cấp doanh thu/biên lợi nhuận gộp** với 2025 — sụt giảm doanh thu -19,6% và biên gộp -530bps trong H1/2026 phần lớn là hiệu ứng kế toán, không phải suy thoái kinh doanh cốt lõi. (3) Đây là rủi ro cần theo dõi độc lập — xem mục Rủi ro #1.

---

## I. Phân tích Kết quả kinh doanh (2018–2025, tỷ VND)

| Chỉ tiêu | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|
| Doanh thu thuần | 23.214 | 27.717 | 29.830 | 35.657 | 44.010 | 52.618 | 62.849 | 70.113 |
| Tăng trưởng DT % | — | 19,4% | 7,6% | 19,5% | 23,4% | 19,6% | 19,4% | 11,6% |
| Lợi nhuận gộp | 8.723 | 10.712 | 11.814 | 13.632 | 17.167 | 20.320 | 23.698 | 25.889 |
| **Biên gộp %** | 37,6% | 38,6% | 39,6% | 38,2% | 39,0% | 38,6% | 37,7% | **36,9%** |
| CP bán hàng+QLDN / DT | 24,1% | 23,7% | 24,2% | 23,0% | 23,6% | 22,6% | 21,0% | 21,3% |
| LN hoạt động | 3.800 | 4.610 | 5.191 | 6.228 | 7.589 | 9.112 | 11.025 | 12.952 |
| **Biên LN hoạt động %** | 16,4% | 16,6% | 17,4% | 17,5% | 17,2% | 17,3% | 17,5% | **18,5%** |
| Doanh thu tài chính | 600 | 650 | 822 | 1.271 | 1.999 | 2.336 | 1.936 | 2.977 |
| CP tài chính (gồm lãi vay) | 361 | 592 | 548 | 1.144 | 1.687 | 1.718 | 1.812 | 1.672 |
| — trong đó CP lãi vay | 238 | 359 | 385 | 484 | 646 | 833 | 552 | 810 |
| **DT tài chính / LNTT %** | 15,6% | 13,9% | 15,6% | 20,1% | 26,1% | 25,4% | 17,5% | **22,8%** |
| LN trước thuế | 3.858 | 4.665 | 5.263 | 6.337 | 7.662 | 9.203 | 11.070 | 13.044 |
| LNST hợp nhất | 3.234 | 3.912 | 4.424 | 5.349 | 6.491 | 7.788 | 9.427 | 11.232 |
| LNST cổ đông công ty mẹ | 2.620 | 3.135 | 3.538 | 4.337 | 5.310 | 6.465 | 7.857 | 9.376 |
| **Biên LNST-mẹ %** | 11,3% | 11,3% | 11,9% | 12,2% | 12,1% | 12,3% | 12,5% | **13,4%** |
| Lợi ích cổ đông thiểu số | 614 | 776 | 886 | 1.012 | 1.181 | 1.323 | 1.571 | 1.856 |
| EPS cơ bản (VND) | 3.903 | 4.220 | 4.120 | 4.349 | 3.847 | 4.661 | 4.292 | 5.216 |

**Nhận xét:**
- Tăng trưởng doanh thu duy trì hai chữ số 7/8 năm liên tiếp (CAGR 2018–2025 ≈ **17,1%/năm**), động lực chính là mảng Công nghệ (dịch vụ CNTT nước ngoài) — không thể tách riêng mảng từ dữ liệu `vnstock_data` hiện có (xem Giới hạn dữ liệu).
- Biên lợi nhuận gộp đạt đỉnh 39,6% (2020), sau đó **xu hướng giảm dần 3 năm liên tiếp**: 39,0% (2022) → 38,6% (2023) → 37,7% (2024) → 36,9% (2025). Cần theo dõi — có thể phản ánh cơ cấu doanh thu dịch chuyển sang mảng biên thấp hơn (dịch vụ CNTT nước ngoài cạnh tranh giá, hoặc tỷ trọng Viễn thông/Giáo dục thay đổi).
- Đòn bẩy chi phí vận hành tốt: CP bán hàng+QLDN/DT giảm từ 24,1% (2018) xuống 21,0–21,3% (2024–2025) → biên LN hoạt động cải thiện đều đặn, đạt đỉnh 18,5% (2025) dù biên gộp giảm.
- **DT tài chính đóng góp tỷ trọng đáng kể và tăng dần vào LNTT**: 15,6% (2018) → 22,8–26,1% (2021–2025), đỉnh 26,1% năm 2022. Đây là khoản thu nhập lãi tiền gửi/lãi từ liên doanh liên kết — không phải rủi ro xấu (FPT có lượng tiền mặt lớn), nhưng làm **chất lượng lợi nhuận phụ thuộc một phần vào biến động lãi suất tiền gửi VN**, không hoàn toàn từ hoạt động lõi.
- EPS cơ bản không tăng đều — giảm năm 2020 (do dịch COVID) và 2022 (do pha loãng từ ESOP/phát hành cổ phiếu thưởng, cần đối chiếu với `IS_BASIC_EARNINGS_PER_SHARE` — đã điều chỉnh hồi tố theo số liệu vnstock_data).

---

## II. Phân tích Bảng cân đối kế toán

| Chỉ tiêu (tỷ VND) | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|
| Tổng tài sản | 29.757 | 33.394 | 41.734 | 53.698 | 51.650 | 60.283 | 72.000 | 88.142 |
| Vốn chủ sở hữu | 14.775 | 16.799 | 18.606 | 21.418 | 25.356 | 29.933 | 35.728 | 43.748 |
| Nợ phải trả | 14.982 | 16.595 | 23.129 | 32.280 | 26.294 | 30.350 | 36.272 | 44.394 |
| Vay ngắn hạn | 6.599 | 7.514 | 12.062 | 17.799 | 10.904 | 13.838 | 14.446 | 19.170 |
| Vay dài hạn | 367 | 350 | 678 | 2.296 | 1.478 | 208 | 501 | 1.904 |
| Tiền + tương đương tiền | 5.169 | 4.295 | 7.156 | 7.388 | 9.000 | 10.583 | 11.905 | 12.960 |
| Phải thu ngắn hạn | 6.427 | 6.536 | 6.265 | 6.882 | 8.503 | 9.674 | 11.382 | 14.402 |
| Hàng tồn kho | 1.341 | 1.284 | 1.290 | 1.507 | 1.966 | 1.593 | 1.857 | 2.194 |
| **Số ngày phải thu (DSO)** | 101,1 | 86,1 | 76,7 | 70,4 | 70,5 | 67,1 | 66,1 | **75,0** |
| **Số ngày tồn kho (DIO)** | 33,8 | 27,6 | 26,1 | 25,0 | 26,7 | 18,0 | 17,3 | 18,1 |
| D/E (Nợ/VCSH), x | 1,01 | 0,99 | 1,24 | 1,51 | 1,04 | 1,01 | 1,01 | 1,01 |
| Current ratio, x | 1,27 | 1,18 | 1,13 | 1,18 | 1,26 | 1,24 | 1,31 | 1,40 |
| Quick ratio, x | 0,72 | 0,62 | 0,49 | 0,41 | 0,61 | 0,61 | 0,59 | 0,60 |
| Hệ số thanh toán lãi vay, x | 15,9 | 12,8 | 13,5 | 12,9 | 11,8 | 10,9 | 20,0 | 16,0 |

**Nhận xét:**
- Quy mô tài sản tăng gấp ~3 lần trong 8 năm (29,8 nghìn tỷ → 88,1 nghìn tỷ), phù hợp tăng trưởng doanh thu.
- **DSO đảo chiều tăng mạnh trong 2025**: giảm liên tục từ 101,1 ngày (2018) xuống đáy 66,1 ngày (2024), rồi **bật tăng lên 75,0 ngày (2025)** — phải thu tăng 26,5% trong khi doanh thu chỉ tăng 11,6%. Đây là dấu hiệu chất lượng lợi nhuận cần theo dõi (xem Rủi ro #2).
- Đòn bẩy nợ ổn định quanh 1,0x (Nợ/VCSH), ngoại trừ đỉnh 1,51x năm 2021 (giai đoạn vay ngắn hạn tăng mạnh cho vốn lưu động, có thể liên quan hoạt động cho vay lại/ giao dịch tài chính nội bộ tập đoàn — không xác minh được chi tiết từ dữ liệu hiện có).
- Vay ngắn hạn chiếm phần lớn tổng nợ vay (~91% năm 2025: 19.170/21.074 tỷ) — rủi ro tái cấp vốn liên tục nhưng hệ số thanh toán lãi vay vẫn rất thoải mái (16–20x năm 2024–2025), rủi ro thanh khoản lãi vay thấp.
- Quick ratio thấp hơn đáng kể so với current ratio (0,6x vs 1,3–1,4x) — chênh lệch lớn cho thấy một phần đáng kể tài sản ngắn hạn không phải tiền/phải thu/đầu tư ngắn hạn thanh khoản cao (có thể là chi phí trả trước, tài sản dở dang xây dựng hạ tầng viễn thông trước 2026) — không tự nó là vấn đề nhưng làm current ratio "đẹp hơn thực tế thanh khoản tức thời".

---

## III. Phân tích Lưu chuyển tiền tệ

| Chỉ tiêu (tỷ VND) | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|
| LCTT từ HĐKD (OCF) | 3.588 | 3.899 | 6.340 | 5.840 | 5.054 | 9.517 | 11.704 | 10.136 |
| Capex | 2.454 | 3.233 | 3.018 | 2.911 | 3.215 | 3.978 | 3.275 | 5.098 |
| **FCF (OCF − Capex)** | 1.135 | 666 | 3.322 | 2.929 | 1.839 | 5.539 | **8.428** | **5.038** |
| **OCF / LNST hợp nhất, x** | 1,11 | 1,00 | 1,43 | 1,09 | 0,78 | 1,22 | 1,24 | **0,90** |
| Biên FCF % | 4,9% | 2,4% | 11,1% | 8,2% | 4,2% | 10,5% | 13,4% | **7,2%** |
| Cường độ Capex/DT % | 10,6% | 11,7% | 10,1% | 8,2% | 7,3% | 7,6% | 5,2% | 7,3% |
| Cổ tức tiền mặt đã trả | 1.708 | 1.484 | 1.899 | 2.254 | 2.222 | 2.931 | 3.292 | 4.574 |

**Nhận xét:**
- FCF dương ở cả 8/8 năm — điểm cộng lớn cho chất lượng dòng tiền, hiếm gặp ngay cả với doanh nghiệp tăng trưởng nhanh.
- Tuy nhiên **2025 là năm dòng tiền yếu nhất trong 3 năm gần đây**: OCF/LNST giảm xuống 0,90x (lần đầu tiên dưới 1,0x kể từ 2022), biên FCF giảm gần một nửa (13,4% → 7,2%) do (a) Capex tăng vọt 55,7% YoY (3.275 → 5.098 tỷ) trong khi doanh thu chỉ tăng 11,6%, và (b) OCF giảm nhẹ trong khi phải thu tăng mạnh (xem mục II).
- Cổ tức tiền mặt đã trả năm 2025 (4.574 tỷ) **vượt FCF của chính năm đó** (5.038 tỷ) — biên an toàn cổ tức mỏng đi so với các năm trước (2024: cổ tức 3.292 tỷ / FCF 8.428 tỷ, hệ số chi trả trên FCF chỉ ~39%; 2025: ~91%). Cần theo dõi nếu capex tiếp tục tăng trong khi duy trì chính sách cổ tức.

---

## 📋 Output Requirements

### 1. Financial Health Score: **7/10** (Trung bình khá — không có dấu hiệu suy giảm nghiêm trọng, nhưng có tín hiệu cảnh báo cần theo dõi)

Chấm điểm bằng nhau trên 3 trụ cột (earnings / assets / cash flow):

| Trụ cột | Điểm (10) | Lý do |
|---|---|---|
| Earnings (Lợi nhuận) | 8/10 | Tăng trưởng DT hai chữ số 7/8 năm, biên LN hoạt động cải thiện đều (16,4%→18,5%), ROE/ROIC cao (28%/17-20%) so với mặt bằng phi tài chính VN. Trừ điểm vì biên gộp giảm 3 năm liên tiếp và tỷ trọng DT tài chính/LNTT khá cao (22,8% năm 2025). |
| Assets (Tài sản/Đòn bẩy) | 7/10 | D/E ổn định ~1,0x, hệ số thanh toán lãi vay rất thoải mái (16-20x), không có rủi ro thanh khoản/vỡ nợ. Trừ điểm vì quick ratio thấp (0,6x), vay ngắn hạn chiếm ~91% tổng nợ vay (rủi ro tái cấp vốn liên tục), và sự kiện thay đổi phạm vi hợp nhất FTEL (2026) làm giảm tính minh bạch/so sánh của bảng cân đối trong ngắn hạn. |
| Cash Flow (Dòng tiền) | 7/10 | FCF dương mọi năm — điểm mạnh cốt lõi. Trừ điểm mạnh vì 2025 cho thấy dấu hiệu suy yếu rõ rệt: OCF/LNST tụt dưới 1,0x, biên FCF giảm gần một nửa, cổ tức tiền mặt vượt FCF trong năm. |

**Điểm tổng hợp: (8+7+7)/3 ≈ 7,3 → làm tròn 7/10.**

### 2. Earnings Quality Judgment: **Moderate (trung bình — không phải "high quality")**

Lý do:
- **Ủng hộ chất lượng cao**: OCF dương và thường ≥ LNST trong 6/8 năm; tăng trưởng doanh thu thực chất (không phải one-off); biên LN hoạt động cải thiện từ đòn bẩy chi phí, không phải từ cắt giảm bất thường.
- **Kéo chất lượng xuống mức "moderate"**:
  1. DSO đảo chiều tăng vọt năm 2025 (66,1 → 75,0 ngày) — phải thu tăng nhanh hơn doanh thu, dấu hiệu điển hình của việc "đẩy doanh thu" cuối kỳ hoặc khách hàng chậm thanh toán.
  2. OCF/LNST giảm dưới 1,0x năm 2025 lần đầu tiên trong 3 năm — lợi nhuận kế toán không được tiền mặt hậu thuẫn đầy đủ trong năm gần nhất.
  3. Tỷ trọng DT tài chính trong LNTT ở mức cao (15,6-26,1% qua các năm, 22,8% năm 2025) — một phần đáng kể lợi nhuận đến từ hoạt động phi lõi (lãi tiền gửi, lãi liên doanh liên kết).
  4. **Thay đổi phạm vi hợp nhất FTEL từ 2026** làm toàn bộ chuỗi doanh thu/biên lợi nhuận 2026 trở đi không so sánh trực tiếp được với lịch sử — cần thời gian (2-3 quý) để đánh giá "LNST-mẹ không đổi" của ban lãnh đạo có đúng như cam kết hay không.
- **Chưa đọc được thuyết minh BCTC (thuyet minh) gốc** để xác minh chi tiết cấu phần "LN khác" và "DT tài chính" theo từng khoản mục cụ thể (lãi tiền gửi vs. lãi từ công ty liên kết vs. khác) — xem Giới hạn dữ liệu.

### 3. Financial Risk Warnings (5 rủi ro chính, đã lượng hóa)

1. **Rủi ro cấu trúc hợp nhất FTEL (cao)**: Từ 2026, FPT mất quyền kiểm soát FTEL (Bộ Công an nắm 50,17%), chuyển sang equity method. Doanh thu/LNTT hợp nhất dự kiến giảm ~16,6%/~10,8% năm 2026 so với 2025 theo hướng dẫn công ty; tổng tài sản đã giảm thực tế 19.552 tỷ (~22%) chỉ trong Q1/2026. Cam kết "NPATMI không đổi" của ban lãnh đạo **chưa được kiểm chứng qua báo cáo kiểm toán năm** — rủi ro nếu tỷ lệ ăn chia lợi nhuận/cổ tức từ FTEL (nay do cổ đông nhà nước kiểm soát) thay đổi bất lợi trong tương lai.
2. **Suy giảm chất lượng phải thu (trung bình-cao)**: DSO tăng từ 66,1 lên 75,0 ngày trong 1 năm (+13,4%), phải thu +26,5% YoY so với DT +11,6% YoY (2025). Nếu xu hướng này tiếp diễn 2 quý liên tiếp, cần hạ mức tin cậy vào chất lượng lợi nhuận.
3. **Biên lợi nhuận gộp xói mòn 3 năm liên tiếp (trung bình)**: 39,0% (2022) → 36,9% (2025), giảm 210 điểm cơ bản trong 3 năm. Nếu biên gộp tiếp tục giảm mà không được bù đắp bởi đòn bẩy chi phí vận hành, biên LN hoạt động sẽ đảo chiều.
4. **Dòng tiền tự do mỏng đi & cổ tức vượt FCF (trung bình)**: Capex 2025 tăng 55,7% YoY lên 5.098 tỷ (7,3% DT) trong khi OCF chỉ tăng nhẹ; cổ tức tiền mặt đã trả (4.574 tỷ) vượt FCF cùng năm (5.038 tỷ) — hệ số chi trả cổ tức/FCF tăng từ ~39% (2024) lên ~91% (2025). Nếu chu kỳ đầu tư (hạ tầng AI/cloud/data center — chưa xác minh được mục đích cụ thể của capex tăng từ dữ liệu hiện có) tiếp tục mở rộng, công ty có thể phải vay thêm hoặc cắt giảm cổ tức.
5. **Phụ thuộc thu nhập tài chính phi lõi (thấp-trung bình)**: DT tài chính chiếm 22,8% LNTT năm 2025 (2.977/13.044 tỷ) — nhạy cảm với xu hướng giảm lãi suất tiền gửi VND; nếu lãi suất huy động giảm mạnh trong 2026-2027, một cấu phần lợi nhuận hiện tại sẽ co lại dù hoạt động lõi không đổi.

### 4. Key Financial Metrics Table (xu hướng 3 năm gần nhất)

| Chỉ tiêu | 2023 | 2024 | 2025 | Xu hướng |
|---|---|---|---|---|
| ROE % | 28,1 | 28,7 | 28,3 | Đi ngang ở mức cao |
| ROA % | 11,6 | 11,9 | 11,7 | Đi ngang |
| ROIC % | 19,2 | 20,7 | 17,0 | ⚠ Giảm rõ rệt sau đỉnh 2024 |
| Biên lợi nhuận gộp % | 38,6 | 37,7 | 36,9 | ⚠ Giảm liên tục |
| Biên LN hoạt động % | 17,3 | 17,5 | 18,5 | ✅ Cải thiện |
| Biên LNST-mẹ % | 12,3 | 12,5 | 13,4 | ✅ Cải thiện |
| Biên FCF % | 10,5 | 13,4 | 7,2 | ⚠ Giảm mạnh |
| D/E (Nợ/VCSH), x | 1,01 | 1,01 | 1,01 | Ổn định |
| DSO (ngày) | 67,1 | 66,1 | 75,0 | ⚠ Đảo chiều tăng |

### 5. Improvement / Deterioration Signals (1–2 năm gần nhất)

**Cải thiện**: (i) biên LN hoạt động và biên LNST-mẹ tiếp tục tăng dù biên gộp giảm, nhờ kiểm soát CP bán hàng+QLDN tốt (21,3% DT, thấp nhất 8 năm); (ii) EPS 2025 (5.216 VND) đạt mức cao nhất lịch sử, +21,5% YoY.

**Suy giảm cần theo dõi**: (i) ROIC giảm từ đỉnh 20,7% (2024) xuống 17,0% (2025) — mức giảm nhanh nhất kể từ 2021; (ii) OCF/LNST và biên FCF cùng suy yếu năm 2025; (iii) DSO đảo chiều tăng lần đầu sau 6 năm giảm liên tục; (iv) **thay đổi cấu trúc hợp nhất FTEL từ Q1/2026** là sự kiện gián đoạn lớn nhất — H1/2026 doanh thu giảm 19,6% YoY (26.269 tỷ so với 32.683 tỷ H1/2025) và biên gộp co lại còn ~32,5% (H1/2026) so với ~37,7% (H1/2025), nhưng LNST-mẹ H1/2026 **thực tế tăng 14,1% YoY** (5.055 tỷ so với 4.432 tỷ) — xác nhận ban đầu cam kết của ban lãnh đạo, tuy vẫn cần theo dõi thêm 2-3 quý để kết luận chắc chắn.

### 6. Peer Comparison

Trong nhóm doanh nghiệp CNTT/công nghệ niêm yết tại VN, **CMC Corporation (CMG)** là peer niêm yết gần nhất có thể đối chiếu công khai (ELC, ITD quy mô quá nhỏ, không đủ tương đồng):

| Chỉ tiêu (2025) | FPT | CMG (CMC Corp) | Nhận xét |
|---|---|---|---|
| Biên lợi nhuận gộp % | 36,9 | 18,7 | FPT có biên gộp gấp ~2x CMG — lợi thế quy mô + tỷ trọng dịch vụ CNTT nước ngoài/viễn thông biên cao hơn |
| Biên lợi nhuận ròng % | 13,4* | 5,5 | FPT vượt trội, phản ánh hiệu quả vận hành và quy mô |
| ROE % | 28,3 | 13,1 | FPT gấp hơn 2 lần CMG |
| ROA % | 11,7 | 4,5 | FPT hiệu quả sử dụng tài sản cao hơn nhiều |
| ROIC % | 17,0 | 7,2 | FPT dẫn đầu rõ rệt |
| D/E (Nợ/VCSH), x | 1,01 | 1,52 | CMG dùng đòn bẩy cao hơn nhưng hiệu quả sinh lời thấp hơn |

*Biên lợi nhuận ròng FPT tính trên LNST cổ đông công ty mẹ/DT thuần để so sánh tương đồng với cách CMG công bố.

**Kết luận đối sánh**: FPT vượt trội CMG ở mọi chỉ số sinh lời then chốt (biên gộp, ROE, ROA, ROIC) với đòn bẩy thấp hơn — củng cố vị thế dẫn đầu ngành CNTT niêm yết Việt Nam về chất lượng tài chính, dù nhóm peer trong nước quá mỏng để kết luận chắc chắn về "trung bình ngành" (chỉ có 1 peer đủ quy mô đối chiếu).

---

## ⚠️ Giới hạn dữ liệu (KHÔNG bịa số — liệt kê những gì chưa lấy được)

1. **Không đọc được thuyết minh BCTC (thuyết minh chi tiết PDF)** cho các khoản mục bất thường: cấu phần chi tiết "DT tài chính" (lãi tiền gửi vs. lãi liên doanh liên kết vs. khác), "LN khác", và bản chất chính xác của khoản tăng vay ngắn hạn năm 2021 (17.799 tỷ, đỉnh D/E 1,51x). Số liệu tổng hợp lấy từ `vnstock_data` đáng tin nhưng không thể diễn giải nguyên nhân gốc ở mức thuyết minh.
2. **Không tách được doanh thu/lợi nhuận theo mảng kinh doanh** (Công nghệ / Viễn thông / Giáo dục & Đầu tư) — `vnstock_data` chỉ cung cấp BCTC hợp nhất cấp tập đoàn, không có phân mảng (segment reporting). Cần lấy thêm từ báo cáo thường niên/BCTC PDF gốc nếu cần.
3. **Chưa xác minh được tỷ lệ sở hữu FTEL chính xác và cơ chế "phần lãi tương ứng" theo equity method từ 2026** qua báo cáo kiểm toán chính thức (chỉ có nguồn báo chí — vietnambiz.vn, vietstock.vn, cafef.vn — đã cross-check 3 nguồn khớp nhau về hướng và độ lớn, nhưng chưa đối chiếu trực tiếp với BCTC kiểm toán bán niên 2026 vì thời điểm phân tích công ty chưa công bố báo cáo soát xét bán niên đầy đủ).
4. **Giao dịch bên liên quan (related-party transactions)** — không lấy được danh sách chi tiết giao dịch với các công ty liên kết/cổ đông lớn (đặc biệt sau khi FTEL chuyển thành công ty liên kết do nhà nước kiểm soát) từ `vnstock_data`; đây là khoản mục quan trọng cần bổ sung DD riêng.
5. **Không có dữ liệu chuẩn ngành/trung bình ngành CNTT VN chính thức** (không có nguồn IBISWorld/Gartner VN) — peer comparison chỉ dựa trên 1 công ty niêm yết đối chiếu được (CMG), độ tin cậy của "trung bình ngành" hạn chế.
6. Cột `operating_expenses` trong `vndata.derived()` trả về NaN cho FPT — đây là hành vi đúng thiết kế (trường này chỉ tính cho ngân hàng), không phải lỗi dữ liệu; CP bán hàng+QLDN trong báo cáo này được tính trực tiếp từ `IS_GENERAL_AND_ADMINISTRATIVE_EXPENSES + IS_SELLING_EXPENSES`.
