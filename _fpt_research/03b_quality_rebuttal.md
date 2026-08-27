# FPT — Phản biện Vòng 2 (Quality Analyst)

**Ngày**: 2026-08-27
**Đối tượng phản biện**: kết luận Financial Analyst (Health 7/10, ROIC "có manh mối" là thoái hợp nhất FTEL) và Valuation Analyst (TÍCH LŨY, mục tiêu 93.000đ, +28%)

---

## Dữ liệu kiểm chứng bổ sung (chạy trực tiếp qua `vndata.fundamental`, interpreter `.venv`)

Tôi đã kéo lại **ROIC/biên lợi nhuận theo QUÝ** (không chỉ theo năm) và **tổng tài sản theo quý** để định vị chính xác mốc thời gian:

**ROIC theo quý (`RT_PRT_ROIC`, %):**
| Quý | ROIC | Biên gộp |
|---|---|---|
| 2023-Q1 | 18,31 | 39,18 |
| 2023-Q4 | 19,22 | 38,62 |
| 2024-Q1 | 18,37 | 38,66 |
| 2024-Q2 | 18,87 | 38,57 |
| 2024-Q3 | 19,58 | 38,30 |
| **2024-Q4** | **20,74 (đỉnh)** | 37,71 |
| 2025-Q1 | 18,85 | 37,78 |
| 2025-Q2 | 17,09 | 37,55 |
| 2025-Q3 | 17,49 | 37,36 |
| **2025-Q4** | **16,95** | 36,92 |
| 2026-Q1 | 18,54 | 35,82 |
| 2026-Q2 | 16,75 | 34,68 |

**Tổng tài sản theo quý (`BS_TOTAL_ASSETS`, tỷ VNĐ):**
| Quý | Tổng tài sản |
|---|---|
| 2025-Q3 | 82.738 |
| 2025-Q4 | **88.142** |
| **2026-Q1** | **68.586** (giảm 19.556 tỷ, −22,2%) |
| 2026-Q2 | 73.563 |

Số liệu tổng tài sản khớp gần như tuyệt đối với con số Financial Analyst nêu (19.552 tỷ, ~22%) — xác nhận cú sốc bảng cân đối do thoái hợp nhất FTEL **xảy ra đúng giữa Q4/2025 và Q1/2026**, tức có hiệu lực kế toán từ 1/1/2026 như dự kiến.

---

## Câu hỏi 1 — Mốc thời gian: thoái hợp nhất có giải thích được cú giảm ROIC 2025 không?

**KHÔNG. Rút lại giả thuyết "hiệu ứng kế toán" trong báo cáo 03.**

Bằng chứng dứt khoát: ROIC giảm từ đỉnh 20,74% (**Q4/2024**) xuống 16,95% (**Q4/2025**) — toàn bộ cú giảm này diễn ra **trong năm 2025, hoàn toàn trước** thời điểm thoái hợp nhất FTEL có hiệu lực (1/1/2026). Cú sốc bảng cân đối (giảm 19.556 tỷ tổng tài sản) chỉ xuất hiện ở **Q1/2026** — sau khi ROIC đã giảm xong. Thứ tự thời gian không cho phép quy cú giảm 2024→2025 cho việc thoái hợp nhất.

Thêm nữa: nếu thoái hợp nhất THẬT SỰ là nguyên nhân, hiệu ứng mẫu số nhỏ lại (tổng tài sản giảm 22%) đáng lẽ phải làm ROIC **tăng vọt** ngay tại Q1/2026 (lợi nhuận/vốn đầu tư nhỏ hơn = ROIC cao hơn về mặt cơ học). Thực tế: ROIC Q1/2026 chỉ nhích nhẹ lên 18,54% rồi rớt tiếp xuống 16,75% ở Q2/2026 — thấp hơn cả đáy trước thoái hợp nhất. Điều này cho thấy đà xói mòn lợi nhuận trên vốn **vẫn tiếp diễn ngay cả sau khi loại bỏ hiệu ứng mẫu số**, tức đây là vấn đề ở **tử số** (EBIT/NOPAT thực chất giảm so với vốn đầu tư), không phải vấn đề kế toán hợp nhất.

**Kết luận dứt khoát: ROIC giảm 2025 là XÓI MÒN HÀO THẬT, không phải hiệu ứng kế toán.** Đây trực tiếp ảnh hưởng tới điểm moat — xem phần điều chỉnh bên dưới.

---

## Câu hỏi 2 — Cost Advantage 2/3 có xứng đáng không khi biên gộp xói mòn 3+ năm, bắt đầu trước GenAI?

Chuỗi biên gộp theo quý xác nhận Financial Analyst đúng và còn cho thấy bức tranh rõ hơn: đỉnh biên gộp thực chất là **2020 (39,60% cả năm)**, đã giảm dần từ 2021, và biên gộp theo quý giảm **liên tục không đứt quãng** từ 39,18% (2023-Q1) xuống 34,68% (2026-Q2) — 13 quý liên tiếp không có một quý nào đảo chiều tăng. ChatGPT/GenAI coding tools mới được doanh nghiệp CNTT ứng dụng đại trà từ khoảng 2023-2024 trở đi — nghĩa là xu hướng xói mòn biên gộp đã bắt đầu **trước** khi GenAI có thể là nguyên nhân chính, và tiếp tục xói mòn nhanh hơn ở giai đoạn 2025-2026 (có thể GenAI là một lực đẩy thêm vào giai đoạn sau, nhưng không phải nguyên nhân khởi phát).

Diễn giải hợp lý hơn: xói mòn có nguồn gốc **cấu trúc, không phải công nghệ** — cạnh tranh giá trong đấu thầu (đặc biệt mảng dịch vụ CNTT nước ngoài đang tăng trưởng nhanh về doanh thu ký mới +32,3% có thể đi kèm chiết khấu để thắng thầu), chi phí nhân sự kỹ sư CNTT tăng nhanh hơn đơn giá hợp đồng, và/hoặc dịch chuyển cơ cấu doanh thu sang các mảng biên thấp hơn (dự án tích hợp hệ thống quy mô lớn, hạ tầng AI Factory vốn có suất đầu tư nặng). Đây là một xu hướng **đã xảy ra và đang tiếp diễn thực tế**, không phải rủi ro tương lai giả định — về bản chất còn đáng lo hơn một rủi ro GenAI thuần lý thuyết vì nó **đã ăn mòn 4,5 điểm % biên gộp trong 3 năm mà chưa có dấu hiệu chặn lại**.

**Điều chỉnh điểm: Cost Advantage hạ từ 2/3 xuống 1/3.** Lợi thế chi phí offshore vẫn tồn tại về mặt tuyệt đối (VN vẫn rẻ hơn onshore), nhưng lợi thế đó đang bị bào mòn liên tục bởi cạnh tranh giá + chi phí nhân sự leo thang — không còn xứng đáng mức "trung bình-mạnh" (2/3) khi xu hướng xói mòn kéo dài, không có bằng chứng đã chững lại.

---

## Câu hỏi 3 — FPT có xứng đáng quay lại P/E trung vị lịch sử 16,26x không?

**KHÔNG đồng ý hoàn toàn với luận điểm của Valuation Analyst — đây là điểm bất đồng cốt lõi giữa MUA và GIỮ.**

Lý do phản đối cụ thể:

1. **"Biên EBITDA perimeter mới 24,6% so với biên cũ 19,8%" là một phép so sánh KHÔNG cùng cơ sở (apples-to-oranges), không phải bằng chứng cải thiện lợi nhuận thực chất.** FPT Telecom — mảng viễn thông có biên lợi nhuận thấp hơn mảng công nghệ — bị loại khỏi hợp nhất từ 1/1/2026. Loại bỏ một mảng kinh doanh biên thấp ra khỏi mẫu số sẽ tự động đẩy biên EBITDA hợp nhất bình quân lên cao hơn **về mặt cơ học/định nghĩa**, không cần bất kỳ cải thiện vận hành nào. Trong khi đó, biên gộp quý gần nhất (2026-Q2: 34,68%) — vốn không bị ảnh hưởng trực tiếp bởi cách hợp nhất FTEL vì đây là số liệu ở cấp báo cáo KQKD trước phân bổ — vẫn tiếp tục giảm, thấp nhất trong toàn bộ chuỗi dữ liệu quan sát được (2018–2026). Nói cách khác: **cùng lúc biên EBITDA "perimeter mới" tăng vì đổi định nghĩa, biên gộp lõi vẫn giảm vì lý do vận hành thật** — hai tín hiệu này mâu thuẫn nhau, và luận điểm bull-case chỉ chọn tín hiệu có lợi.

2. **EPS H1/2026 +13,6% YoY không đủ để bác bỏ xói mòn** — tăng trưởng EPS có thể đến từ đòn bẩy tài chính, thu nhập tài chính (Financial Analyst nêu DT tài chính chiếm 22,8% LNTT — một tỷ trọng cao bất thường của lợi nhuận không đến từ hoạt động lõi), hoặc hiệu ứng base thấp sau thoái hợp nhất, không nhất thiết phản ánh sức mạnh định giá (pricing power) đang phục hồi. Biên gộp và ROIC — hai thước đo trực tiếp của sức mạnh cạnh tranh — đều đi ngược chiều với câu chuyện "thị trường hiểu sai".

3. **Một doanh nghiệp có hào đang bị bào mòn (không phải ổn định hay mở rộng) một cách chính đáng phải chịu chiết khấu so với bội số lịch sử**, chứ không phải được thưởng bội số trung vị/đỉnh lịch sử. Bội số P/E trung vị 16,26x được hình thành trong giai đoạn ROIC đang tăng (2018→2024: 14,4%→20,7%) và biên gộp ổn định quanh 38-39%. Áp dụng lại bội số đó cho một giai đoạn ROIC đã giảm về ~17% và biên gộp giảm còn 34,7% — thấp nhất lịch sử quan sát — là **định giá công ty theo quá khứ, không theo quỹ đạo hiện tại**. Đây chính xác là loại "narrative dễ viết, thesis khó bảo vệ" mà một nhà đầu tư giá trị nghiêm túc phải cảnh giác.

**Kết luận cho hội đồng**: Với moat hạ còn 8/15 và bằng chứng xói mòn ROIC/biên gộp là thực chất (không phải kế toán), tôi khuyến nghị hội đồng **không** chấp nhận giả định "trở lại P/E trung vị 16,26x" làm cơ sở cho mục tiêu giá +28%. Nếu Valuation Analyst muốn giữ khuyến nghị MUA/TÍCH LŨY, cần hạ bội số mục tiêu xuống dưới trung vị lịch sử (phản ánh chiết khấu hào đang co lại) hoặc đưa ra bằng chứng cụ thể (không phải suy luận từ đổi định nghĩa perimeter) rằng biên gộp/ROIC đã chạm đáy và sắp đảo chiều. Ở trạng thái dữ liệu hiện tại, quan điểm của tôi nghiêng về **GIỮ**, không phải MUA.

---

## Điều chỉnh điểm Moat: 9/15 → **8/15**

| Loại hào | Điểm cũ | Điểm mới | Lý do thay đổi |
|---|---|---|---|
| Brand | 2 | 2 | Không đổi |
| Network Effects | 1 | 1 | Không đổi |
| **Cost Advantages** | **2** | **1** | Xói mòn biên gộp 13 quý liên tiếp (39,18%→34,68%), bắt đầu trước GenAI, không có dấu hiệu chững — không còn xứng mức 2/3 |
| Switching Costs | 2 | 2 | Không đổi trực tiếp, nhưng **ghi nhận tín hiệu cảnh báo**: DSO xấu đi 66,1→75,0 ngày (theo Financial Analyst) có thể là dấu hiệu FPT phải nới điều khoản thanh toán để giữ khách — cần theo dõi thêm quý tới trước khi hạ điểm |
| Licenses/Resources | 2 | 2 | Không đổi |
| **TỔNG** | **9/15** | **8/15** | |

**Xếp hạng tổng thể vẫn là "TRUNG BÌNH" nhưng ở ngưỡng thấp của dải trung bình**, gần biên giới với "Yếu". Kết luận "phù hợp nắm giữ trung-dài hạn" trong báo cáo 03 cần được hạ mức thận trọng hơn: đây là một doanh nghiệp có nền tảng quản trị tốt (không đổi điểm ban lãnh đạo 8/10) nhưng đang trải qua xói mòn hào có thể đo lường được, chưa có bằng chứng đã chạm đáy — khuyến nghị dài hạn nên là **"theo dõi sát, không giải ngân thêm ở vùng định giá bằng/trên trung vị lịch sử"** thay vì tích lũy chủ động.

## Cập nhật Thesis Breaker

Bổ sung một breaker đã kích hoạt một phần: **biên gộp quý đã phá đáy lịch sử 34,68% (2026-Q2)** — nếu quý tới (2026-Q3) tiếp tục giảm dưới 34%, nâng mức độ cảnh báo xói mòn hào từ "cần giám sát" lên "đã xác nhận", và điểm Cost Advantage nên hạ tiếp xuống 0/3.
