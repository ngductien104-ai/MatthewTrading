# Phản biện Vòng 2 — Financial Analyst (FPT)
**Ngày**: 2026-08-27
**Đối chiếu với**: bản Quality (moat 9/15, ROE 18,7%→28,7%, hỏi về ROIC -380bps) và bản Valuation (TÍCH LŨY, mục tiêu ~93.000đ, EBITDA perimeter mới 24,6% vs 19,8%)
**Dữ liệu bổ sung dùng cho vòng này**: `vndata.fundamental` cho FPT (đã dùng ở vòng 1) + **FOX (FPT Telecom - niêm yết UPCOM)** để tách bạch tác động perimeter — đây là dữ liệu THẬT lấy trực tiếp từ `vnstock_data`, không suy diễn.

---

## Tóm tắt lập trường sau phản biện

| Nội dung | Vòng 1 | Sau phản biện | Thay đổi? |
|---|---|---|---|
| Financial Health Score 7/10 | Giữ | Giữ | Không đổi |
| Earnings quality = Moderate | Giữ | Giữ, **củng cố thêm bằng chứng mới** (xem Câu 3) | Không đổi hướng, thêm bằng chứng |
| ROIC 2025 giảm là hiệu ứng kế toán FTEL? | Không nêu rõ | **Bác bỏ giả thuyết này bằng số — là xói mòn thật, không liên quan FTEL** | Làm rõ thêm, không phải sửa lỗi |
| Mốc thời gian thoái hợp nhất FTEL (1/1/2026) | Nêu | **Xác nhận đúng, không sửa** | Giữ nguyên |
| EBITDA perimeter mới 24,6% (của Valuation) | Chưa bình luận | **Không tái lập được bằng dữ liệu tôi có — yêu cầu Valuation đối chiếu nguồn** | Câu hỏi ngược, không tự sửa số của mình |

---

## Câu hỏi 1 — Mâu thuẫn mốc thời gian: ROIC 2024→2025 giảm vì gì?

### Kiểm tra mốc thời gian trước

Xác nhận lại: thoái hợp nhất FTEL có hiệu lực **từ 01/01/2026**. Toàn bộ năm tài chính 2025 (và cả 2024) **vẫn hợp nhất 100% FTEL** — không có restatement hồi tố. Vì vậy, về nguyên tắc, cú giảm ROIC 2024→2025 (theo `RT_PRT_ROIC` của FPT: 20,74% → 16,95%, **-379bps**) **không thể** do thay đổi phạm vi hợp nhất. Đây là điểm bản của tôi ở Vòng 1 đã đúng khi KHÔNG gán nguyên nhân này cho FTEL — nhưng tôi chưa tách bạch được nguyên nhân thật, nên bổ sung ở đây.

### Bằng chứng số 1: ROIC giảm dần trong SUỐT năm 2025, không phải một cú nhảy tại điểm giao 2025→2026

Lấy `RT_PRT_ROIC` (ratio %, không phải EBITDA dạng giá trị tuyệt đối dễ dính lỗi TTM) theo quý:

| Quý | 2024-Q3 | 2024-Q4 | 2025-Q1 | 2025-Q2 | 2025-Q3 | 2025-Q4 | 2026-Q1 | 2026-Q2 |
|---|---|---|---|---|---|---|---|---|
| ROIC % | 19,58 | 20,74 | 18,85 | 17,09 | 17,49 | 16,95 | 18,54 | 16,75 |

ROIC **đã giảm từ đỉnh 20,74% (Q4/2024) xuống 17,09% ngay tại Q2/2025** — tức là phần lớn cú giảm xảy ra **trong năm 2025, khi FTEL vẫn còn hợp nhất 100%**. Sang 2026 (đã bỏ FTEL), ROIC dao động 18,54%→16,75% — **không có bước nhảy gián đoạn rõ rệt tại ranh giới 2025/2026** như sẽ thấy nếu FTEL là nguyên nhân cơ học. Ngược lại, biên lợi nhuận gộp (`RT_PRT_GROSS_MARGIN`) MỚI là chỉ tiêu có bước nhảy rõ đúng tại ranh giới này (xem Câu hỏi 2). Kết luận: **ROIC 2025 giảm là xói mòn thật của hoạt động, KHÔNG phải hiệu ứng kế toán từ thoái hợp nhất FTEL.**

### Bằng chứng số 2: Tách tử số (NOPAT) và mẫu số (vốn đầu tư)

| Chỉ tiêu | 2024 | 2025 | Tăng trưởng |
|---|---|---|---|
| LN hoạt động (EBIT proxy), tỷ VND | 11.025,1 | 12.951,7 | **+17,5%** |
| Thuế suất hiệu dụng (Thuế TNDN/LNTT) | 14,84% | 13,89% | — |
| NOPAT ước tính = EBIT×(1−thuế suất), tỷ VND | 9.388,7 | 11.151,9 | **+18,8%** |
| Vay ngắn hạn, tỷ VND | 14.446,2 | 19.169,7 | **+32,7%** |
| Vay dài hạn, tỷ VND | 501,1 | 1.903,8 | +280% (nền thấp) |
| Tổng vay, tỷ VND | 14.947,4 | 21.073,5 | **+41,0%** |
| Vốn chủ sở hữu, tỷ VND | 35.727,5 | 43.748,0 | +22,5% |
| **Tổng vốn đầu tư (Nợ vay+VCSH, gộp), tỷ VND** | 50.674,9 | 64.821,5 | **+27,9%** |

Tử số (NOPAT) tăng +18,8%, nhưng mẫu số (vốn đầu tư) tăng +27,9% — chênh lệch ~9,1 điểm phần trăm. Đây là cơ chế toán học trực tiếp giải thích ROIC giảm: công ty huy động vốn (chủ yếu vay ngắn hạn +32,7%) nhanh hơn nhiều so với tốc độ tăng lợi nhuận hoạt động sau thuế.

### Capex 2025: bao nhiêu, tăng bao nhiêu %, đầu tư vào đâu?

- **Capex hợp nhất FPT 2025 = 5.097,9 tỷ VND, tăng 55,7% so với 2024 (3.275,3 tỷ)** — đã nêu ở Vòng 1, xác nhận lại từ `CF_PAYMENTS_FOR_FIXED_ASSETS`.
- Tách phần đóng góp của FTEL (còn hợp nhất 100% trong 2025): **Capex riêng của FOX/FTEL 2025 = 1.750,85 tỷ, tăng 69,6% so với 2024 (1.032,21 tỷ)** — tăng ròng 718,6 tỷ, chiếm **39,4%** mức tăng capex toàn tập đoàn (1.822,6 tỷ). **60,6% còn lại (~1.104 tỷ) đến từ phần Công nghệ/khác** — không tách được chi tiết hơn vì `vnstock_data` không có báo cáo theo mảng (segment reporting).
- Vốn đầu tư của riêng FTEL cũng tăng chậm hơn nhiều so với toàn tập đoàn: Nợ vay+VCSH của FTEL tăng từ 17.268,7 tỷ (2024) lên 18.741,6 tỷ (2025), chỉ **+8,5%** — thấp hơn nhiều mức +27,9% của cả tập đoàn. **Kết luận: phần lớn sự phình to vốn đầu tư năm 2025 đến từ NGOÀI FTEL** (công ty mẹ/mảng Công nghệ) — không phải hiệu ứng viễn thông, càng không phải hiệu ứng thoái hợp nhất.
- **Chưa xác minh được đích đến cụ thể của capex tăng thêm ở mảng Công nghệ** (có khả năng liên quan hạ tầng AI Factory/trung tâm dữ liệu GPU mà FPT công bố công khai trên báo chí, nhưng đây là suy luận dựa trên thông tin công khai ngoài phạm vi `vnstock_data`, CHƯA đối chiếu được với thuyết minh BCTC — ghi nhận là giới hạn dữ liệu, không khẳng định).

### Trả lời trực tiếp câu (b) của điều phối viên

Mốc thời gian trong bản của tôi (hiệu lực 1/1/2026) là đúng và được xác nhận lại bằng dữ liệu quý ở trên. Nếu bản Quality suy luận cú giảm ROIC 2024-2025 có thể do FTEL, thì giả thuyết đó **không được ủng hộ bởi dữ liệu** — đây là xói mòn ROIC thật (nợ vay ngắn hạn phình to nhanh hơn lợi nhuận hoạt động sau thuế, một phần đến từ capex tăng, phần lớn hơn đến từ ngoài FTEL).

---

## Câu hỏi 2 — Biên EBITDA "perimeter mới 24,6% cao hơn 19,8%": có khớp dữ liệu không?

### Bước 1: FTEL có phải mảng biên thấp bị loại bỏ không? — KHÔNG, ngược lại

| Chỉ tiêu FY2025 | FPT hợp nhất | FOX/FTEL (100%, đứng riêng) |
|---|---|---|
| Doanh thu thuần, tỷ VND | 70.112,8 | 19.506,7 |
| Biên lợi nhuận gộp % | 36,9 | **49,8** |
| Biên EBIT % (LN hoạt động/DT) | 18,5 | **20,1** |
| Biên EBITDA % (EBITDA/DT) | 19,83 | **26,87** |
| ROIC % | 17,0 | **20,9** |

FTEL có biên gộp, biên EBIT, biên EBITDA và ROIC đều **cao hơn** mức bình quân hợp nhất của FPT (điển hình của viễn thông cố định: khấu hao hạ tầng lớn nhưng dòng tiền/EBITDA rất dày). Về mặt cơ học, loại một mảng có biên CAO HƠN ra khỏi hợp nhất phải làm biên bình quân phần còn lại THẤP ĐI, không phải cao lên.

### Bước 2: Dữ liệu thực tế quý 2026 xác nhận hướng giảm, không phải tăng

| Quý | 2025-Q1 | 2025-Q2 | 2025-Q3 | 2025-Q4 | 2026-Q1 | 2026-Q2 |
|---|---|---|---|---|---|---|
| Biên gộp % (`RT_PRT_GROSS_MARGIN`) | 37,78 | 37,55 | 37,36 | 36,92 | **35,82** | **34,68** |
| Biên EBIT % (`RT_PRT_EBIT_MARGIN`) | 16,64 | 16,24 | 16,18 | 15,67 | **15,67** | **15,63** |

Ngay tại ranh giới hợp nhất 2025→2026, biên gộp có bước giảm rõ rệt (36,92%→35,82%, mất ~110bps chỉ trong 1 quý) — đúng hướng dự đoán về mặt cơ học ở Bước 1: bỏ FTEL (biên cao) → biên còn lại giảm. Biên EBIT cũng đi ngang-giảm nhẹ (15,67%→15,63%), **không hề tăng lên 24,6%**.

*Lưu ý kỹ thuật quan trọng*: trường `RT_VALUE_EBITDA` (giá trị tuyệt đối tỷ VND) trong bảng ratio theo quý có vẻ là số **TTM (trượt 12 tháng)**, không phải EBITDA riêng của quý đó — chia trực tiếp cho doanh thu 1 quý cho ra kết quả vô lý (>80-100%, tôi đã thử và loại bỏ). Tôi chỉ dùng `RT_PRT_EBIT_MARGIN`/`RT_PRT_GROSS_MARGIN` (đã chuẩn hoá % sẵn, đáng tin hơn) để tránh đúng bẫy dữ liệu mà CLAUDE.md của repo đã cảnh báo cho khối `RT_VALUE_*`.

### Kết luận cho Câu hỏi 2

Với dữ liệu tôi có (biên gộp/EBIT chuẩn hoá theo quý + số liệu chuẩn của FTEL đứng riêng), **tôi không tái lập được con số "biên EBITDA perimeter mới 24,6% > 19,8%" của Valuation**. Ngược lại: (a) FTEL là mảng biên cao hơn bình quân, loại nó ra phải làm biên giảm chứ không tăng; (b) dữ liệu quý thực tế 2026 cho thấy biên gộp/EBIT đều giảm nhẹ, không có dấu hiệu nhảy vọt lên 24,6%.

**Đề nghị Valuation cung cấp cách tính cụ thể** — có thể do: (i) dùng số EBITDA hướng dẫn quản trị (guidance) cho cả năm 2026 chưa kiểm toán, khác với số quý thực tế Q1-Q2/2026 tôi đang dùng; hoặc (ii) cộng ngược một khoản lãi định giá lại một lần (fair value gain khi ghi nhận khoản đầu tư vào FTEL theo equity method lần đầu, phát sinh do chênh lệch giá trị sổ sách vs giá trị hợp lý tại thời điểm mất quyền kiểm soát — một nghiệp vụ kế toán chuẩn theo IFRS 10/VAS tương đương khi một công ty con trở thành công ty liên kết). Nếu là trường hợp (ii), đây là **khoản lợi nhuận kế toán một lần, không lặp lại — không nên dùng để đại diện cho biên lợi nhuận bền vững của "perimeter mới"**, và luận điểm "thị trường hiểu sai FPT" của Valuation cần xem lại.

**Về câu hỏi "hai bức tranh ngược nhau" (Moderate vs biên cải thiện)**: không mâu thuẫn về bản chất — vì bằng chứng "biên cải thiện" của Valuation chưa được tôi xác nhận lại được từ dữ liệu ratio chuẩn hoá. Nếu Valuation đúng và tôi sai (khả năng: công thức EBITDA khác nhau hoặc nguồn dữ liệu khác), cần đối chiếu công thức cụ thể trước khi kết luận lại. Với dữ liệu tôi có trong tay hiện nay, tôi **bảo lưu** đánh giá "Moderate" — không có bằng chứng số nào ở đây khiến tôi nâng lên "high quality".

---

## Câu hỏi 3 — FTEL đóng góp bao nhiêu vào OCF hợp nhất 2025? Chênh lệch tiền mặt thực nhận theo equity method?

### Bước 1: Định lượng đóng góp của FTEL vào OCF hợp nhất FPT 2025

| Chỉ tiêu 2025, tỷ VND | Giá trị |
|---|---|
| OCF hợp nhất FPT (toàn tập đoàn) | 10.136,0 |
| **OCF riêng của FOX/FTEL (100%, đứng riêng)** | **3.708,0** |
| **Tỷ trọng FTEL trong OCF hợp nhất FPT** | **36,6%** |

Vì hợp nhất kế toán đưa **100% dòng tiền hoạt động của công ty con vào báo cáo hợp nhất** (bất kể tỷ lệ sở hữu kinh tế), toàn bộ 3.708,0 tỷ OCF của FTEL đã được cộng gộp vào OCF 10.136,0 tỷ của FPT năm 2025 — **chiếm hơn 1/3 tổng dòng tiền hoạt động hợp nhất**. Đây là con số rất lớn, xác nhận mức độ trọng yếu của sự kiện thoái hợp nhất đối với hồ sơ dòng tiền tương lai của FPT.

### Bước 2: Ước tính tiền mặt thực nhận theo equity method (2026 trở đi)

Từ 2026, FPT sẽ không còn được cộng dòng tiền hoạt động của FTEL vào OCF hợp nhất. Thay vào đó, FPT chỉ ghi nhận tiền mặt thực nhận khi FTEL chia cổ tức, theo đúng tỷ lệ sở hữu kinh tế 45,66%.

| Chỉ tiêu | Giá trị |
|---|---|
| Cổ tức tiền mặt FTEL đã trả cho TOÀN BỘ cổ đông, năm 2025, tỷ VND | 2.541,7 |
| Tỷ lệ sở hữu của FPT tại FTEL | 45,66% |
| **Ước tính cổ tức FPT thực nhận từ FTEL (nếu giữ nguyên mức chi trả 2025), tỷ VND** | **≈ 1.160,9** |

**Chênh lệch tiền mặt "biến mất" khỏi tầm nhìn dòng tiền của FPT** (so sánh mức đóng góp cũ 100% OCF vs mức nhận mới qua cổ tức, giả định payout không đổi):

**3.708,0 − 1.160,9 ≈ 2.547,1 tỷ VND/năm**

Đây là con số định lượng cụ thể cho "thesis-breaker" mà Valuation nêu (dòng cổ tức từ FTEL về công ty mẹ nay phụ thuộc quyết định của cổ đông kiểm soát Bộ Công an). **~2.547 tỷ đồng/năm là quy mô rủi ro cụ thể** — tương đương khoảng **25,1% FCF năm 2025 của FPT (5.038,1 tỷ)** hoặc **55,7% khoản cổ tức tiền mặt FPT đã trả năm 2025 (4.573,8 tỷ)**. Nói cách khác, nếu FTEL (dưới sự kiểm soát mới của Bộ Công an) quyết định giữ lại lợi nhuận để tái đầu tư hạ tầng thay vì chia cổ tức như trước — một quyết định hoàn toàn hợp lý với một cổ đông nhà nước ưu tiên hạ tầng an ninh mạng/viễn thông quốc gia hơn là tối đa hoá cổ tức cho cổ đông thiểu số — thì FPT có thể mất toàn bộ 1.160,9 tỷ tiền mặt dự kiến này, cộng dồn với xu hướng biên FCF đã mỏng đi (7,2% năm 2025, cổ tức/FCF đã ở mức 91%) đã nêu ở Vòng 1.

### Trả lời trực tiếp: FPT còn đủ FCF trả cổ tức không?

Nếu biên FCF tiếp tục ở mức 7,2% (kịch bản giữ nguyên, thận trọng) áp trên doanh thu 2026 đã giảm quy mô (~50.591 tỷ ước tính ex-FTEL, xem Câu 2), FCF 2026 ước tính ≈ 50.591 × 7,2% ≈ **3.643 tỷ** — thấp hơn đáng kể so với mức cổ tức tiền mặt đã trả năm 2025 (4.573,8 tỷ). Nếu FPT giữ nguyên mức cổ tức tuyệt đối, hệ số chi trả cổ tức/FCF ước tính sẽ vượt 100% (~125%) — tức là phải dùng thêm vốn vay hoặc giảm mức cổ tức. Đây là phép ngoại suy đơn giản (giữ biên FCF % không đổi trên doanh thu perimeter mới), **chưa tính đến khoản cổ tức nhận từ FTEL theo equity method (~1.160,9 tỷ ước tính ở trên)** — nếu cộng khoản này vào, FCF khả dụng thực tế có thể đỡ hơn, nhưng vẫn phụ thuộc hoàn toàn vào quyết định chia cổ tức của HĐQT FTEL mới, không còn nằm trong tầm kiểm soát của FPT.

Đây là con số cụ thể tôi đưa thêm để củng cố thesis-breaker của Valuation — không mâu thuẫn với kết luận TÍCH LŨY của họ, nhưng đề nghị Valuation đưa biến số này (xác suất FTEL duy trì payout ratio dưới cổ đông nhà nước mới) vào bear case, thay vì chỉ nêu định tính.

---

## Những gì tôi GIỮ NGUYÊN từ Vòng 1 (có bằng chứng số củng cố thêm)

1. Financial Health Score 7/10 — giữ.
2. Earnings quality "Moderate" — giữ, củng cố thêm bằng phát hiện FTEL chiếm 36,6% OCF hợp nhất (rủi ro tập trung dòng tiền cao hơn ước tính ở Vòng 1).
3. Timeline thoái hợp nhất FTEL hiệu lực 1/1/2026 — giữ, xác nhận đúng bằng dữ liệu quý (bước nhảy biên gộp đúng tại ranh giới này).
4. 5 rủi ro tài chính chính nêu ở Vòng 1 — giữ nguyên, rủi ro #1 (FTEL) nay được lượng hóa cụ thể hơn (~2.547 tỷ/năm chênh lệch tiền mặt).

## Những gì tôi BỔ SUNG (không phải sửa lỗi, mà làm rõ nguyên nhân)

1. Nguyên nhân ROIC giảm 2024→2025: xói mòn thật do vốn đầu tư (chủ yếu vay ngắn hạn +32,7%) tăng nhanh hơn NOPAT (+18,8%) — không liên quan thoái hợp nhất FTEL.
2. Định lượng cụ thể mức độ phụ thuộc dòng tiền vào FTEL: 36,6% OCF hợp nhất 2025, ước tính mất ~2.547 tỷ tiền mặt/năm nếu chuyển hoàn toàn sang equity method với payout không đổi.

## Câu hỏi ngược gửi Valuation

Đề nghị Valuation công bố cách tính cụ thể cho con số "biên EBITDA perimeter mới 24,6%" — vì dữ liệu ratio chuẩn hoá (`RT_PRT_GROSS_MARGIN`, `RT_PRT_EBIT_MARGIN`) và số liệu đứng riêng của FTEL đều cho thấy hướng ngược lại (biên giảm khi bỏ FTEL, không tăng). Nếu con số 24,6% đến từ một khoản lãi định giá lại một lần (fair value gain khi chuyển sang equity method), cần loại khoản này ra khỏi luận điểm "chất lượng lợi nhuận cải thiện".

## Giới hạn dữ liệu bổ sung ở vòng phản biện này

- Không xác minh được công thức chính xác vnstock_data dùng để tính `RT_PRT_ROIC` (đã thử tái lập bằng NOPAT/Invested Capital với vài biến thể, không khớp tuyệt đối con số 20,74%/16,95% dù cùng hướng và độ lớn hợp lý) — kết luận về nguyên nhân dựa trên xu hướng và tỷ lệ tăng trưởng tương đối, không phải khớp đúng công thức tuyệt đối.
- Không có báo cáo theo mảng (segment reporting) của FPT để tách chính xác phần capex/vốn đầu tư tăng thêm ngoài FTEL thuộc mảng Công nghệ, Giáo dục hay Đầu tư khác.
- Chưa xác minh được cách Valuation tính "biên EBITDA perimeter mới 24,6%" — đang chờ đối chiếu công thức/nguồn cụ thể từ Valuation.
- Ước tính cổ tức FPT nhận từ FTEL (~1.160,9 tỷ) giả định tỷ lệ chi trả cổ tức của FTEL năm 2026 giữ nguyên như 2025 — đây là giả định, chưa có công bố chính thức về chính sách cổ tức của FTEL dưới cổ đông kiểm soát mới (Bộ Công an).
