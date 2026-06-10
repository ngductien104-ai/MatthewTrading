---
name: financial-statement
description: "Đọc hiểu BCTC theo chuẩn kế toán Việt Nam (VAS — TT 200/2014/TT-BTC) — quan hệ khớp số 3 báo cáo, chất lượng lợi nhuận (dồn tích vs tiền mặt), phân tích Dupont, 12 cờ đỏ gian lận tài chính. Nguồn dữ liệu vnstock (BCTC) + DataPro (giá)."
category: flow
---

# Đọc hiểu BCTC doanh nghiệp Việt Nam (VAS)

## Tổng quan

Phân tích sâu chất lượng lợi nhuận từ quan hệ khớp số của 3 báo cáo (Kết quả HĐKD, Cân đối kế toán, Lưu chuyển tiền tệ) theo **Thông tư 200/2014/TT-BTC**, nhận diện tín hiệu gian lận tài chính, và phân rã động lực sinh lời bằng Dupont. Dữ liệu lấy từ **vnstock** (`lang='vi'` để phân loại đúng khoản mục) và **DataPro** (giá/khối lượng).

> ⚠️ **Trước khi tính, theo checklist Karpathy:** số CP lưu hành lấy từ `Company.overview().issue_share` (KHÔNG suy từ EPS); lục đúng line-item BCTC `lang='vi'` (đừng đoán khoản mục); bóc khoản một lần (FX/thanh lý/đánh giá lại) trước khi annualize quý.

## Khung 3 báo cáo (VAS)

### Báo cáo Kết quả HĐKD (kiếm được bao nhiêu)

```
Doanh thu bán hàng và cung cấp dịch vụ        (mã 01)
 − Các khoản giảm trừ doanh thu               (02)
 = Doanh thu thuần                            (10)
 − Giá vốn hàng bán                           (11)
 = Lợi nhuận gộp                              (20)  → biên gộp = LN gộp / DT thuần
 + Doanh thu hoạt động tài chính              (21)
 − Chi phí tài chính (trong đó: chi phí lãi vay) (22, 23)
 − Chi phí bán hàng                           (25)
 − Chi phí quản lý doanh nghiệp               (26)
 = Lợi nhuận thuần từ HĐKD                    (30)
 + Lợi nhuận khác (Thu nhập khác − Chi phí khác) (40)
 = Tổng lợi nhuận kế toán trước thuế          (50)
 − Chi phí thuế TNDN (hiện hành + hoãn lại)   (51, 52)
 = Lợi nhuận sau thuế TNDN                    (60)
 → tách: LN cổ đông công ty mẹ / cổ đông không kiểm soát
```

> **Lợi nhuận cốt lõi** (thước đo phân tích, không có trên BCTC): với DN phi tài chính ≈ Lợi nhuận gộp − Chi phí bán hàng − Chi phí QLDN. Mục đích: loại bỏ lãi/lỗ tài chính và khoản bất thường để thấy "lõi" kinh doanh thật.

**Tỷ số then chốt:**

| Tỷ số | Công thức | Khoẻ | Cảnh báo |
|------|------|---------|------|
| Biên gộp | LN gộp / DT thuần | Tuỳ ngành | Giảm 3 quý liên tiếp |
| Biên ròng | LN sau thuế / DT thuần | >10% là tốt | <0% và không cải thiện |
| Tỷ lệ chi phí (BH+QL) | (CPBH+CPQLDN)/DT thuần | <30% | Tăng dần qua các năm |
| LN cốt lõi / LN sau thuế | LN cốt lõi / LN ròng | >80% | <50% → lệ thuộc khoản bất thường |

### Bảng Cân đối kế toán (gia sản có gì)

```
TÀI SẢN = NỢ PHẢI TRẢ + VỐN CHỦ SỞ HỮU

A. TÀI SẢN NGẮN HẠN (100)
   - Tiền và tương đương tiền (110): có bị hạn chế? "vừa nhiều tiền vừa nhiều nợ vay"?
   - Đầu tư tài chính ngắn hạn (120)
   - Phải thu ngắn hạn (130): tăng có nhanh hơn doanh thu không?
   - Hàng tồn kho (140): có ứ đọng? dự phòng giảm giá đủ chưa?
B. TÀI SẢN DÀI HẠN (200)
   - Tài sản cố định; Bất động sản đầu tư
   - Tài sản dở dang dài hạn (xây dựng cơ bản dở dang): có "treo" lâu không chuyển TSCĐ?
   - Đầu tư tài chính dài hạn
   - Lợi thế thương mại (chỉ trên BCTC hợp nhất): rủi ro tổn thất

NGUỒN VỐN
C. NỢ PHẢI TRẢ (300)
   - Nợ ngắn hạn (310): vay ngắn hạn, phải trả người bán, người mua trả trước
   - Nợ dài hạn (330): vay dài hạn, trái phiếu phát hành
   - Nợ vay có lãi = vay ngắn hạn + vay dài hạn + trái phiếu
D. VỐN CHỦ SỞ HỮU (400)
```

**Tỷ số then chốt:**

| Tỷ số | Công thức | Khoẻ (phi tài chính) |
|------|------|---------|
| Hệ số nợ | Nợ phải trả / Tổng tài sản | 40-60% |
| Thanh toán hiện hành | TS ngắn hạn / Nợ ngắn hạn | 1,5-2,5 |
| Thanh toán nhanh | (TS ngắn hạn − Tồn kho) / Nợ ngắn hạn | >1,0 |
| Tỷ lệ nợ vay | Nợ vay có lãi / Tổng tài sản | <30% |
| Khả năng trả lãi (ICR) | LN thuần HĐKD trước lãi vay / Chi phí lãi vay | >3 lần |

### Báo cáo Lưu chuyển tiền tệ (tiền thật về bao nhiêu)

```
CFO — Lưu chuyển tiền từ hoạt động kinh doanh: tiền thật từ làm ăn
CFI — Lưu chuyển tiền từ hoạt động đầu tư: mua/bán tài sản
CFF — Lưu chuyển tiền từ hoạt động tài chính: vay/trả nợ/cổ tức/phát hành

Công thức vàng (dài hạn): Lợi nhuận sau thuế ≈ CFO
```

**Ma trận chất lượng dòng tiền:**

| CFO | CFI | CFF | Trạng thái doanh nghiệp |
|-----|-----|-----|---------|
| + | − | − | Ưu tú (làm ra tiền, đầu tư, trả nợ) |
| + | − | + | Mở rộng (làm ra tiền, đầu tư, vay thêm tăng tốc) |
| + | + | − | Vững (làm ra tiền, thu hồi đầu tư, trả nợ) |
| − | − | + | Nguy hiểm (lỗ tiền, vẫn đầu tư, sống bằng đi vay) |
| − | + | + | Khó khăn (bán tài sản + vay để cầm cự) |
| − | + | − | Suy thoái (bán tài sản để trả nợ) |

## Quan hệ khớp số 3 báo cáo

### Khớp số cốt lõi

```
1. KQHĐKD → Cân đối kế toán
   LN sau thuế → tăng Lợi nhuận sau thuế chưa phân phối (vốn CSH)
   Phải thu tăng = Doanh thu − Tiền thực thu
   Tồn kho tăng = Mua vào − Giá vốn đã bán

2. KQHĐKD → Lưu chuyển tiền tệ
   LN sau thuế + Khấu hao − Tăng vốn lưu động ≈ CFO
   Nếu chênh lệch lớn → chất lượng lợi nhuận đáng ngờ

3. Cân đối kế toán → Lưu chuyển tiền tệ
   Tiền cuối kỳ = Tiền đầu kỳ + CFO + CFI + CFF
```

### Công thức kiểm chứng (Python)

```python
# Chất lượng lợi nhuận
accrual_ratio = (net_profit_loss_after_tax - cfo) / total_assets
# accrual_ratio > 10% → tỷ trọng lợi nhuận dồn tích cao, chất lượng kém

# Chất lượng doanh thu
receivable_growth = accounts_receivable.pct_change()
revenue_growth = net_sales.pct_change()
# receivable_growth > revenue_growth → chất lượng doanh thu xấu đi

# Nhất quán cân đối kế toán vs dòng tiền
cf_total = cfo + cfi + cff   # ≈ thay đổi tiền & tương đương tiền trong kỳ
```

## Phân tích chất lượng lợi nhuận

### Dồn tích vs tiền mặt

```
Lợi nhuận chất lượng CAO:
- CFO / LN sau thuế > 1,0 (tiền thật lớn hơn lợi nhuận trên giấy)
- Phải thu tăng chậm hơn doanh thu
- CFO dương liên tục

Lợi nhuận chất lượng THẤP:
- CFO / LN sau thuế < 0,5 (nhiều lợi nhuận chưa thành tiền)
- Tỷ lệ Phải thu/Doanh thu tăng liên tục
- Lệ thuộc khoản một lần (lãi tài chính, thanh lý tài sản, đánh giá lại)
```

### Thẻ điểm chất lượng lợi nhuận

| Chỉ tiêu | Tốt (3đ) | Trung bình (2đ) | Kém (1đ) | Trọng số |
|------|----------|----------|---------|------|
| CFO/LN sau thuế | >1,2 | 0,8-1,2 | <0,8 | 25% |
| Phải thu vs Doanh thu | Phải thu chậm hơn | Đồng tốc | Phải thu nhanh hơn | 20% |
| LN cốt lõi/LN ròng | >90% | 70-90% | <70% | 20% |
| Xu hướng CFO | Tăng liên tục | Dao động | Giảm | 20% |
| Vòng quay tồn kho | Nhanh lên | Ổn định | Chậm lại | 15% |

Điểm ≥ 2,5 = chất lượng ưu tú · 1,5-2,5 = cần theo dõi · < 1,5 = kém, nên tránh

## 🚩 Cờ đỏ gian lận tài chính

### 12 tín hiệu cờ đỏ

| # | Cờ đỏ | Cách phát hiện | Mức độ |
|---|------|---------|--------|
| 1 | "Vừa nhiều tiền vừa nhiều nợ vay" | Tiền & ĐTTC ngắn hạn cao + nợ vay cao (cùng >30% DT thuần) — tiền có thể ảo/bị hạn chế | Cao |
| 2 | Phải thu bùng nổ | Phải thu tăng > doanh thu tăng × 1,5, kéo dài ≥2 quý | Cao |
| 3 | Tồn kho bất thường | Tỷ lệ Tồn kho/DT thuần tăng đột ngột >50% | Cao |
| 4 | CFO âm | CFO âm 2 năm liên tiếp nhưng LN sau thuế dương | Cao |
| 5 | Giao dịch bên liên quan lớn | Giao dịch bên liên quan / doanh thu > 30% | Cao |
| 6 | Đổi kiểm toán liên tục | Thay đơn vị kiểm toán 2 lần trong 3 năm | Trung bình |
| 7 | Xây dựng dở dang "treo" | TS dở dang/TSCĐ > 50%, kéo dài ≥3 năm không chuyển TSCĐ | Trung bình |
| 8 | Trả trước người bán bất thường | Tỷ lệ trả trước/doanh thu tăng đột ngột | Trung bình |
| 9 | LN cổ đông không kiểm soát lạ | Tỷ lệ LN cổ đông không kiểm soát/LN ròng dao động mạnh | Trung bình |
| 10 | Ý kiến kiểm toán | Không phải "chấp nhận toàn phần" (ngoại trừ / trái ngược / từ chối) | Cao |
| 11 | Vốn hoá lãi vay / chi phí | Vốn hoá lãi vay hoặc chi phí phát triển lớn để thổi lợi nhuận | Trung bình |
| 12 | Lợi thế thương mại / đánh giá lại | Lợi thế thương mại hoặc đánh giá lại tài sản chiếm tỷ trọng lớn, tài sản mua về không đạt kế hoạch | Trung bình |

> **Lưu ý ý kiến kiểm toán (VSA 700/705/706):** phân biệt **đoạn "Vấn đề cần nhấn mạnh"** (Emphasis of Matter, vd nghi ngờ hoạt động liên tục — going concern) với **ý kiến ngoại trừ**. "Nhấn mạnh" KHÔNG phải ý kiến ngoại trừ và không tự động đưa cổ phiếu vào diện cảnh báo — nhưng vẫn là tín hiệu rủi ro cần soi vốn lưu động và khả năng thanh toán.

### Đánh giá xác suất gian lận tổng hợp

```
Số cờ đỏ    Xác suất gian lận    Khuyến nghị
0-1         Thấp                 Đầu tư bình thường
2-3         Trung bình           Điều tra sâu, thận trọng
4-5         Cao                  Nên tránh
6+          Rất cao              Tránh dứt khoát
```

## Phân tích Dupont

### Phân rã 3 cấp

```
ROE = Biên ròng × Vòng quay tổng tài sản × Đòn bẩy tài chính

ROE = (LN ròng/DT thuần) × (DT thuần/Tổng TS) × (Tổng TS/Vốn CSH)
       Khả năng sinh lời    Hiệu quả vận hành    Mức đòn bẩy
```

### Phân rã 5 cấp

```
ROE = Gánh nặng thuế × Gánh nặng lãi vay × Biên LN hoạt động × Vòng quay TS × Đòn bẩy
    = (LN ròng/LN trước thuế) × (LN trước thuế/EBIT) × (EBIT/DT thuần) × (DT thuần/Tổng TS) × (Tổng TS/Vốn CSH)
```

### Mẫu bảng Dupont

```markdown
### Phân tích Dupont: [Tên DN]

| Chỉ tiêu | Năm N-1 | Năm N | Thay đổi | Đánh giá động lực |
|------|------|------|------|---------|
| ROE | 15,2% | 17,8% | +2,6% | ↑ |
| Biên ròng | 8,5% | 9,2% | +0,7% | Sinh lời cải thiện ✓ |
| Vòng quay TS | 0,85 | 0,88 | +0,03 | Hiệu quả tăng ✓ |
| Đòn bẩy | 2,10 | 2,20 | +0,10 | Đòn bẩy tăng ⚠️ |

Kết luận: ROE tăng chủ yếu do sinh lời cải thiện; đòn bẩy nhích lên cần theo dõi.
```

### ROE tham chiếu theo ngành VN

> Chỉ là khoảng tham chiếu định tính — **luôn xác minh bằng số thật của DN** (tính ≥2 cách khi nhạy cảm).

| Ngành | Động lực ROE chủ đạo |
|------|---------|
| Ngân hàng | Đòn bẩy cao (hệ số nhân vốn lớn) — báo cáo theo mẫu riêng |
| Bất động sản | Đòn bẩy cao + chu kỳ bàn giao; coi chừng vốn lưu động âm |
| Bán lẻ / Tiêu dùng | Vòng quay cao (biên mỏng, bán nhiều) |
| Công nghệ | Biên ròng cao + vòng quay trung bình |
| Thép / Vật liệu (chu kỳ) | Biên dao động mạnh theo giá hàng hoá — dùng LN chuẩn hoá giữa chu kỳ |

## Mẫu output

```markdown
## Phân tích tài chính: [Tên DN / Mã .VN]

### Tóm tắt 3 báo cáo (đơn vị: tỷ đồng)
| Chỉ tiêu | N-2 | N-1 | N | Xu hướng |
|------|-------|-------|-------|------|
| Doanh thu thuần | ... | ... | ... | ... |
| LN sau thuế | ... | ... | ... | ... |
| CFO | ... | ... | ... | ... |
| Hệ số nợ | ... | ... | ... | ... |

### Điểm chất lượng lợi nhuận
| Chỉ tiêu | Điểm | Diễn giải |
|------|------|------|
| CFO/LN sau thuế | 3/3 | 1,25 — thu tiền tốt |
| ... | ... | ... |
| **Tổng** | **2,7/3** | **Chất lượng ưu tú** |

### Phân rã Dupont
[bảng Dupont]

### Soát cờ đỏ
- [x] Vừa nhiều tiền vừa nhiều nợ → Không
- [x] Phải thu bất thường → Không, tăng chậm hơn doanh thu
- [!] Lợi thế thương mại → 22%, sát ngưỡng, cần theo dõi
- [x] Ý kiến kiểm toán → Chấp nhận toàn phần

### Kết luận
...
```

## Lưu ý

1. **Chuẩn kế toán VAS (TT 200/2014/TT-BTC)**: khác IFRS/US GAAP. So sánh với DN nước ngoài phải điều chỉnh; lưu ý lợi thế thương mại chỉ trên BCTC **hợp nhất** (phân bổ ≤10 năm theo TT 202).
2. **Dữ liệu quý xem cùng kỳ, không xem liên tiếp**: yếu tố mùa vụ lớn (tiêu dùng cao điểm Q4) — biến động quý-trên-quý không phải xu hướng.
3. **Ngân hàng / Chứng khoán / Bảo hiểm dùng mẫu BCTC riêng** (không có Doanh thu thuần/Giá vốn) — quan hệ khớp số truyền thống KHÔNG áp dụng; dùng khung riêng (NIM, NPL, LLR, CAR cho ngân hàng).
4. **Tài sản nặng vs nhẹ**: vòng quay tài sản không so được liên ngành; chỉ so trong cùng ngành.
5. **Thay đổi phạm vi hợp nhất**: mua/bán công ty con làm số cùng kỳ không so được — cần xem số liệu có thể so sánh (comparable).

## Nguồn dữ liệu

- **BCTC → vnstock** (`source="VCI"`, `lang="vi"`):
  - `income_statement(period=...)`, `balance_sheet(...)`, `cash_flow(...)`
  - Trong backtest: đặt `fundamental_fields` với bảng `income` / `balancesheet` / `cashflow`, tên field là **`item_id`** (đã an toàn point-in-time qua loader vnstock).
  - `item_id` thường dùng:
    - KQHĐKD: `net_sales`, `cost_of_sales`, `gross_profit`, `selling_expenses`, `general_and_admin_expenses`, `interest_expenses`, `net_profit_loss_after_tax`, `attributable_to_parent_company`
    - CĐKT: `cash_and_cash_equivalents`, `short_term_investments`, `accounts_receivable`, `inventories_net`, `total_assets`, `liabilities`, `current_liabilities`, `short_term_borrowings`, `long_term_borrowings`, `owners_equity`
    - LCTT: `net_cash_inflows_outflows_from_operating_activities` (CFO), `...investing_activities` (CFI), `...financing_activities` (CFF)
  - Để xem toàn bộ khoản mục: in cột `item_id` của báo cáo tương ứng.
- **Giá / khối lượng / khối ngoại → DataPro** (`source="datapro"`, mã có đuôi `.VN`).
- **Số CP lưu hành → `Company.overview().issue_share`** (không suy từ EPS).
- ⚠️ Bản community vnstock chỉ trả ~4 kỳ năm gần nhất → backtest dài thiếu BCTC năm cũ.
