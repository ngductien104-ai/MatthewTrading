---
name: commodity-analysis
description: "Phân tích hàng hóa dưới góc nhìn VN — cân đối cung cầu dầu, định giá vàng (kèm chênh lệch SJC), đồng dự báo chu kỳ, thép/HRC, và nhóm nông sản xuất khẩu chủ lực (gạo, cà phê robusta, hồ tiêu, cao su). Sinh tín hiệu hướng giá và ánh xạ sang CPI + cổ phiếu niêm yết."
category: analysis
---
# Phân tích hàng hóa (góc nhìn Việt Nam)

## Tổng quan

Phân tích hàng hóa trên bốn trục — **cân đối cung cầu, mô hình định giá, chu kỳ tồn kho, cấu trúc kỳ hạn** — và xuất tín hiệu hướng giá dùng được cho backtest.

Điểm khác biệt của VN: nền kinh tế đứng **cả hai phía** của thương mại hàng hóa.
- **Phía nhập khẩu (chịu chi phí)**: dầu thô/xăng dầu thành phẩm, than nhiệt, khí, quặng sắt, than cốc, phân bón đầu vào, nguyên liệu thức ăn chăn nuôi (ngô, khô đậu tương)
- **Phía xuất khẩu (hưởng lợi)**: gạo, cà phê robusta (VN là nước sản xuất số 1 thế giới), hồ tiêu, điều, cao su, thủy sản, gỗ

Vì vậy mọi kết luận về hàng hóa phải trả lời **hai câu hỏi tách biệt**: tác động lên CPI (kênh chi phí) và tác động lên lợi nhuận doanh nghiệp niêm yết (kênh doanh thu). Một cú tăng giá cà phê là *xấu cho CPI* nhưng *tốt cho lợi nhuận* — trộn hai kênh là lỗi phân tích phổ biến nhất.

## Khái niệm cốt lõi

### 1. Cân đối cung cầu dầu thô

**Biến phía cung:**

| Biến | Nguồn | Tần suất | Chiều tác động |
|------|--------|------|---------|
| Sản lượng OPEC+ | Báo cáo tháng OPEC | Tháng | Cắt giảm → giá dầu ↑ |
| Sản lượng dầu đá phiến Mỹ | EIA weekly | Tuần | Tăng sản lượng → giá dầu ↓ |
| Số giàn khoan (Baker Hughes) | Baker Hughes | Tuần | Dẫn báo sản lượng 3-6 tháng |
| Dự trữ chiến lược Mỹ (SPR) | EIA | Tuần | Xả SPR → giá dầu ↓ ngắn hạn |

**Biến phía cầu:**
- Dự báo nhu cầu dầu toàn cầu của IEA (quý)
- Nhập khẩu dầu thô Trung Quốc (hải quan TQ, tháng) — biến cầu biên lớn nhất
- Nhu cầu xăng Mỹ (EIA weekly, implied demand)
- PMI toàn cầu (dẫn báo cầu 1-2 tháng)

```python
if opec_compliance > 0.90 and us_rig_count_declining:
    supply_signal = "thắt"     # thuận giá dầu
elif opec_compliance < 0.80 and us_production_rising:
    supply_signal = "lỏng"     # nghịch giá dầu

if global_pmi > 50 and china_import_yoy > 0.05:
    demand_signal = "mạnh"
elif global_pmi < 48 and china_import_yoy < 0:
    demand_signal = "yếu"
```

### 2. Khung định giá vàng

**Mô hình 4 nhân tố (giá vàng thế giới):**

| Nhân tố | Trọng số | Logic | Chỉ báo |
|------|------|------|------|
| Lãi suất thực | 40% | Lãi suất thực ↓ → chi phí cơ hội nắm vàng giảm → vàng ↑ | Lợi suất TIPS 10Y |
| Chỉ số USD | 25% | USD ↓ → vàng rẻ đi theo đơn vị định giá → vàng ↑ | DXY |
| Cầu trú ẩn | 20% | Rủi ro ↑ → mua phòng thủ → vàng ↑ | VIX + chỉ số rủi ro địa chính trị |
| NHTW mua ròng | 15% | Cầu cấu trúc | Báo cáo quý WGC |

**Quy tắc thực chiến:**
- TIPS 10Y < 0%: nền đỡ mạnh cho vàng
- TIPS 10Y > 2%: áp lực lên vàng
- Tương quan DXY–vàng khoảng −0,6, không tuyệt đối (2022 cả hai cùng tăng do cầu trú ẩn)
- NHTW mua > 1.000 tấn/năm: nền đỡ cấu trúc dài hạn

**Lớp riêng của VN — chênh lệch giá vàng trong nước:**
- Giá vàng miếng SJC và vàng nhẫn được giao dịch **tách khỏi giá thế giới** vì độc quyền thương hiệu và hạn chế nhập khẩu vàng nguyên liệu
- Chênh lệch SJC với giá thế giới quy đổi **có thể** là chỉ báo vĩ mô (cầu USD ngầm, mất niềm tin VND) — **nhưng chỉ khi có xác nhận chéo từ tỷ giá.** Bắt buộc kiểm điều kiện kép trước khi diễn giải:

  | Chênh SJC | Tỷ giá USD/VND | Diễn giải đúng |
  |---|---|---|
  | Nới rộng | Đồng thời chịu áp lực (tiêu >90% biên trên, tự do vượt niêm yết >1-2%) | **Tín hiệu stress thật** — cầu USD ngầm, đô-la hóa |
  | Nới rộng | Ổn định | **KHÔNG phải tín hiệu stress** — là méo mó độc quyền/quota. Dùng làm chỉ báo tỷ giá sẽ cho **tín hiệu giả** |
  | Thu hẹp | Bất kỳ | Thường do can thiệp chính sách (đấu thầu, quota), không phải cầu giảm |

- *Bằng chứng thực nghiệm 2026:* chênh SJC duy trì ~13,3 triệu (~10,3%) trong khi USD/VND chỉ biến động +0,07% nửa đầu năm — chênh lệch cao **không** đi kèm stress tỷ giá. Ai dùng chênh SJC đơn lẻ làm chỉ báo trong năm này đều đọc sai.
- Chênh lệch có thể **tự co lại do chính sách** (SBV đấu thầu vàng, cấp quota nhập khẩu, mở rộng đơn vị được bán) — nghĩa là nắm SJC để phòng hộ có rủi ro chính sách một chiều; ưu tiên vàng nhẫn nếu mục tiêu là bám giá thế giới
- Vàng nhẫn bám giá thế giới sát hơn vàng miếng ⇒ nếu mục tiêu là bám vàng thế giới, dùng vàng nhẫn làm tham chiếu
- Cần theo: chênh SJC – thế giới (điểm % và tuyệt đối), chênh vàng nhẫn – thế giới, chênh mua–bán (thanh khoản)

### 3. Đồng — "Dr. Copper" dự báo chu kỳ

- Biến động YoY giá đồng dẫn báo sản xuất công nghiệp khoảng 2-3 tháng
- Tỷ lệ đồng/vàng tương quan dương mạnh với lợi suất TPCP Mỹ 10Y (`r > 0,7`)
- Đồng vượt đỉnh cũ xác nhận phục hồi kinh tế

| Chỉ báo | Nguồn | Ngưỡng |
|------|--------|------|
| Tồn kho đồng LME | LME daily | < 150 nghìn tấn = thắt |
| Tồn kho đồng SHFE | SHFE weekly | Giảm > 10% WoW = thắt |
| Phí gia công TC/RC | SMM | TC < 30 USD/tấn = nguồn quặng thắt |
| Nhập khẩu đồng TQ | Hải quan TQ, tháng | Tăng > 10% YoY = cầu mạnh |

### 4. Chu kỳ tồn kho

**Tồn kho hiện + tồn kho ẩn:**
- Hiện: sàn công bố (LME / SHFE / COMEX), minh bạch, theo dõi được
- Ẩn: kho ngoại quan, kho thương nhân — không thấy nhưng có thể lớn hơn
- Điểm đảo chiều giá thật nằm ở điểm đảo của **tổng** tồn kho

```
Chủ động tích trữ (giá↑ lượng↑) → Bị động tích trữ (giá↓ lượng↑) → Chủ động xả kho (giá↓ lượng↓) → Bị động xả kho (giá↑ lượng↓)
     giữa sóng tăng                cuối sóng tăng                 giữa sóng giảm                cuối sóng giảm / đầu sóng tăng
```

| Giai đoạn | Tồn kho | Giá | Tín hiệu |
|------|---------|---------|---------|
| Bị động xả kho | ↓ | ↑ | Mua (điểm mua tốt nhất) |
| Chủ động tích trữ | ↑ | ↑ | Giữ vị thế mua |
| Bị động tích trữ | ↑ | ↓ | Đóng vị thế (cảnh báo) |
| Chủ động xả kho | ↓ | ↓ | Bán hoặc đứng ngoài |

### 5. Cấu trúc kỳ hạn

**Contango (kỳ hạn > giao ngay, thị trường bình thường):** nguồn cung dồi dào, giá phản ánh chi phí lưu trữ + vốn; roll yield âm, bất lợi cho vị thế mua dài. Contango sâu (`tháng xa − tháng gần > 5%`) = dư cung nghiêm trọng.

**Backwardation (kỳ hạn < giao ngay, thị trường đảo):** cung thắt, giao ngay được trả giá cao; roll yield dương. Backwardation sâu (`tháng gần − tháng xa > 3%`) = ép giá hoặc thiếu hụt cực đoan.

```python
spread_ratio = (front_month - second_month) / front_month

if spread_ratio > 0.02:
    signal = "rất thuận"    # thiếu hụt giao ngay
elif spread_ratio < -0.03:
    signal = "nghịch"       # dư cung
else:
    signal = "trung tính"
```

### 6. Tính mùa vụ

**Dầu:** tháng 3-5 kết thúc bảo dưỡng nhà máy lọc + tích trữ cho mùa lái xe → tăng theo mùa; tháng 9-10 mùa bão vịnh Mexico → gián đoạn nguồn cung, biến động cao; tháng 11-12 cầu dầu sưởi → crack spread diesel mạnh.

**Vàng:** tháng 1-2 Tết Nguyên đán + mùa cưới Ấn Độ → cầu vật chất mạnh (VN cộng thêm **ngày vía Thần Tài mùng 10 tháng Giêng âm** — cầu bán lẻ tăng đột biến, PNJ hưởng lợi); tháng 7-8 mùa thấp điểm; tháng 10-11 Diwali + tích trữ Giáng sinh.

**Đồng:** tháng 3-4 vào mùa xây dựng TQ → cầu hồi; tháng 6-7 mùa thấp điểm; tháng 9-10 "tháng vàng tháng bạc" → cầu hồi.

**Nông sản VN (chu kỳ mùa vụ trong nước — quan trọng nhất với cổ phiếu niêm yết):**
- **Cà phê robusta**: thu hoạch Tây Nguyên tháng 10 – tháng 1; áp lực bán ra cao nhất ngay sau thu hoạch; giá thường mạnh vào cuối vụ (tháng 6-9) khi tồn kho nông dân cạn. Theo dõi hạn hán / mưa trái mùa ở Đắk Lắk, Lâm Đồng, Gia Lai
- **Gạo**: vụ Đông Xuân (thu hoạch tháng 2-4, vụ lớn nhất), Hè Thu (tháng 6-8), Thu Đông (tháng 10-11). Giá lúa trong nước và giá gạo 5% tấm xuất khẩu lệch pha với vụ thu hoạch
- **Cao su**: mùa cạo mủ tháng 4-12, ngưng cạo (rụng lá) tháng 2-3 → sản lượng quý 1 thấp theo cấu trúc, đừng đọc thành suy giảm
- **Heo hơi**: giá thường tăng mạnh trước Tết (cầu tiêu dùng đỉnh) và giảm sau Tết; dịch tả lợn châu Phi là biến số phá vỡ mùa vụ

### 7. Kênh truyền dẫn vào Việt Nam (bắt buộc có trong mọi báo cáo)

**a) Dầu thô → giá xăng dầu trong nước → CPI**
- Giá bán lẻ trong nước được **điều hành theo chu kỳ 7 ngày** (Bộ Công Thương phối hợp Bộ Tài chính), có đệm bởi **Quỹ bình ổn giá (BOG)** và trong giai đoạn căng thẳng có thể giảm **thuế bảo vệ môi trường**
- ⇒ **Không mô hình hóa truyền dẫn 1:1**. Cú sốc dầu thế giới vào CPI VN có độ trễ và bị chính sách làm phẳng
- Nhóm giao thông chiếm khoảng 9-10% rổ CPI — nêu rõ hệ số co giãn đang dùng và nguồn của nó
- Cổ phiếu: PLX, OIL (phân phối), BSR (lọc dầu, hưởng crack spread), GAS, PVS, PVD, PVT (thượng nguồn/dịch vụ) hưởng lợi; HVN, VJC, vận tải, xi măng chịu chi phí

**b) Khí & than → điện & phân bón**
- Giá khí đầu vào quyết định biên của DPM, DCM (urê); giá than nhiệt quyết định biên nhiệt điện than (QTP, PPC, HND)
- Giá bán lẻ điện của EVN là **quyết định chính sách**, thường được canh theo dư địa mục tiêu CPI ⇒ điều chỉnh giá điện vừa là biến chi phí doanh nghiệp vừa là biến CPI có chủ đích

**c) Quặng sắt + than cốc → thép**
- Biên gộp của HPG, HSG, NKG phụ thuộc chênh lệch giá HRC/thép xây dựng với quặng + than cốc, độ trễ tồn kho khoảng 1 quý
- Biến số chính sách: **lượng thép Trung Quốc xuất vào VN** và tiến trình các vụ kiện chống bán phá giá — đây là biến biên lợi nhuận do chính sách, không phải cung cầu thuần

**d) Nông sản → hai chiều**
- Chiều doanh thu: LTG, TAR (gạo); PHR, DPR, GVR (cao su); VHC, ANV, FMC (thủy sản); nhóm cà phê/hồ tiêu phần lớn chưa niêm yết nhưng tác động vĩ mô vùng Tây Nguyên và tín dụng nông nghiệp
- Chiều CPI: nhóm hàng ăn & dịch vụ ăn uống chiếm khoảng 33-34% rổ CPI — biến động lớn nhất đến từ **giá thịt heo**, kế đến là gạo
- Giá thức ăn chăn nuôi (ngô, khô đậu tương nhập khẩu) → biên của DBC, BAF, HAG, MML với độ trễ 1-2 quý

**Nguồn dữ liệu hàng hóa cho VN:**
- Giá xăng dầu điều hành: Bộ Công Thương / PLX
- Giá heo hơi, giá lúa, giá cà phê, giá tiêu: các trang chuyên ngành + cafef/vietstock (cross-check tối thiểu 2 nguồn)
- Xuất khẩu theo mặt hàng: Tổng cục Hải quan (tháng), Hiệp hội Lương thực VN (VFA), Vicofa (cà phê), VASEP (thủy sản)
- Giá vàng SJC/nhẫn: SJC, PNJ, DOJI — luôn ghi rõ giá mua hay giá bán
- Hàng hóa thế giới: qua `yfinance` (dầu, vàng, đồng) hoặc `web-reader`; Sở Giao dịch Hàng hóa VN (MXV) cho hợp đồng liên thông

## Khung phân tích

### Sáu bước

1. **Cung cầu định hướng**: dư cung hay thiếu hụt? Biến biên đang chạy chiều nào?
2. **Tồn kho định nhịp**: đang ở giai đoạn nào của chu kỳ tồn kho? Sắp đảo chưa?
3. **Cấu trúc kỳ hạn xác nhận**: contango hay backwardation? Có khớp với nhận định cung cầu không?
4. **Phủ lớp mùa vụ**: mùa vụ đang thuận hay nghịch? (dùng cả mùa vụ thế giới và mùa vụ trong nước)
5. **Kiểm chứng vĩ mô**: USD / lãi suất / khẩu vị rủi ro có ủng hộ nhận định không?
6. **Ánh xạ VN**: tách rõ tác động lên CPI và tác động lên lợi nhuận từng nhóm cổ phiếu, kèm độ trễ

### Mẫu chấm điểm tổng hợp

```python
commodity_score = {
    "supply_demand":  +1,   # cung cầu thắt
    "inventory_cycle": +2,  # bị động xả kho (giai đoạn tốt nhất)
    "term_structure": +1,   # backwardation nhẹ
    "seasonality":     0,   # mùa vụ trung tính
    "macro_env":      -1,   # USD mạnh là lực cản
}
# Tổng = +3/5 = +0,6 → thiên thuận, nhưng chưa phải tín hiệu mạnh
```

## Định dạng đầu ra

```
## Báo cáo hàng hóa — [Tên hàng hóa]

### Cấu trúc cung cầu
- Phía cung: [dư / cân bằng / thiếu] — [số liệu cụ thể, nguồn]
- Phía cầu: [mạnh / ổn / yếu] — [số liệu cụ thể, nguồn]
- Bảng cân đối: [tăng tồn X tấn / rút tồn X tấn]

### Chu kỳ tồn kho
- Giai đoạn hiện tại: [chủ động tích trữ / bị động tích trữ / chủ động xả / bị động xả]
- Tồn kho hiện: [LME X tấn, SHFE X tấn, thay đổi tuần]

### Cấu trúc kỳ hạn
- Chênh lệch tháng gần–xa: [contango X% / backwardation X%]
- Roll yield: [dương / âm]

### Điểm tổng hợp
| Trục | Điểm (−2~+2) | Căn cứ |
|------|------------|------|
| Cung cầu | +1 | Tỷ lệ tuân thủ OPEC 92% |
| Tồn kho | +2 | Tồn kho LME thấp nhất 18 tháng |

### Ánh xạ Việt Nam
- Kênh CPI: [nhóm hàng nào, tỷ trọng rổ, độ trễ dự kiến, có bị chính sách làm phẳng không]
- Kênh lợi nhuận: [mã hưởng lợi / mã chịu chi phí, độ trễ tồn kho, mức nhạy biên gộp]
- Rủi ro chính sách: [điều hành giá, thuế, quota, phòng vệ thương mại]

### Hướng giao dịch
- Hướng: [thuận / nghịch / trung tính]
- Độ tin cậy: [cao / trung bình / thấp]
- Rủi ro: [cụ thể]
```

## Lưu ý

- Nguồn dữ liệu hàng hóa phân mảnh (EIA / OPEC / LME / SHFE / Hải quan VN / hiệp hội ngành). Skill này cung cấp khung phân tích; số liệu lấy qua `web-reader`, `yfinance` hoặc crawl thủ công
- Giá hợp đồng tương lai có chi phí đảo vị thế — so sánh giữa các kỳ hạn phải hiệu chỉnh roll
- Quy luật mùa vụ là bình quân thống kê, có thể bị cơ bản của năm cụ thể đè bẹp hoàn toàn
- Vàng có cả tính hàng hóa lẫn tính tài chính; ngắn hạn phần tài chính (lãi suất/USD) chi phối. Riêng tại VN còn cộng **rủi ro chính sách** lên chênh lệch SJC
- Tính tài chính của đồng mạnh lên từ 2020 (dùng làm hedge vĩ mô), phân tích cơ bản thuần có thể không đủ
- Dữ liệu tồn kho có độ trễ và không thấy được tồn kho ẩn — đối chiếu với hành vi giá và basis
- **Với VN, tuyệt đối tách hai kênh CPI và lợi nhuận.** Cùng một cú sốc giá có thể vừa là tin xấu vĩ mô vừa là tin tốt vi mô — nói rõ cả hai, đừng gộp thành một kết luận
- Khung này phục vụ nghiên cứu/backtest, không phải khuyến nghị đầu tư


## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)

1. **Không bịa/cook số liệu.** Mọi số tài chính phải có nguồn thật. Luôn **audit nhanh, cross-check tối thiểu 2 nguồn uy tín** (vd `cafef.vn`, `vietstock.vn`) — dùng **crawl4ai** cào số rồi đối chiếu; nếu nguồn lệch nhau thì nêu rõ, không chọn bừa.
2. **Nếu DataPro VÀ vnstock_data đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
