---
name: performance-attribution
description: "Phân tích quy kết hiệu suất (performance attribution) cho danh mục cổ phiếu VN — Brinson phân rã allocation/selection theo ngành HOSE, phân rã alpha/beta & đa nhân tố, đánh giá khả năng định thời điểm (market timing), khung so sánh benchmark. Lưu ý đặc thù: so với VN30-TRI (total return) chứ không phải VN-Index giá; index VN tập trung cao vào ngân hàng & họ Vingroup."
category: analysis
---

# Phân tích quy kết hiệu suất (Việt Nam)

## Mục đích

Phân rã lợi suất vượt trội (excess return) của danh mục thành các nguồn giải thích được: phân bổ ngành, chọn cổ phiếu, độ phơi nhiễm nhân tố, đóng góp từ định thời điểm… Mục tiêu trả lời **"vì sao"** chiến lược lãi/lỗ, chứ không chỉ **"lãi/lỗ bao nhiêu"**.

> **Cảnh báo benchmark đặc thù VN — đọc trước tiên:** **VN-Index là chỉ số GIÁ (price index), không cộng cổ tức.** Một danh mục bluechip nhận cổ tức 3–5%/năm "đánh bại VN-Index" có thể chỉ là do cổ tức, **không phải kỹ năng**. Để quy kết công bằng, dùng **VN30-TRI / VNI-TRI (total return index)** làm benchmark, hoặc cộng lại cổ tức vào VN-Index. Bỏ qua điểm này là sai lầm phổ biến nhất khi đánh giá quỹ VN.

## Mô hình Brinson

### Brinson-Fachler một kỳ

```
Excess return = lợi suất danh mục − lợi suất benchmark

Phân rã thành 3 thành phần:
1. Allocation (phân bổ ngành): lệch tỷ trọng ngành × lệch lợi suất ngành so với benchmark tổng
2. Selection (chọn cổ phiếu trong ngành): chọn mã trong ngành × tỷ trọng ngành benchmark
3. Interaction (tương tác): lệch tỷ trọng × lệch chọn mã
```

**Công thức**:

```
Gọi w_p,i = tỷ trọng ngành i trong danh mục
    w_b,i = tỷ trọng ngành i trong benchmark (vd VN30/VN-Index)
    r_p,i = lợi suất ngành i trong danh mục
    r_b,i = lợi suất ngành i trong benchmark
    R_b   = lợi suất benchmark tổng

Allocation_i  = (w_p,i − w_b,i) × (r_b,i − R_b)
Selection_i   = w_b,i × (r_p,i − r_b,i)
Interaction_i = (w_p,i − w_b,i) × (r_p,i − r_b,i)

Excess = Σ(Allocation_i) + Σ(Selection_i) + Σ(Interaction_i)
```

> **Đặc thù VN — index tập trung rất cao:** VN30/VN-Index bị chi phối bởi **nhóm ngân hàng (~35–45% vốn hóa) và họ Vingroup (VIC/VHM/VRE)**. Vì vậy Allocation effect thường bị thống trị bởi quyết định **over/underweight ngân hàng và BĐS Vingroup**. Lệch tỷ trọng nhỏ ở 2 nhóm này tạo ra phần lớn allocation effect — luôn soi kỹ 2 nhóm này trước.

### Ví dụ Brinson theo ngành (HOSE)

```markdown
### Quy kết Brinson theo ngành

| Ngành | Tỷ trọng DM | Tỷ trọng BM | Lợi suất DM | Lợi suất BM | Allocation | Selection | Interaction |
|------|---------|---------|---------|---------|---------|---------|---------|
| Ngân hàng | 25% | 38% | 12% | 8% | −0,3% | +1,5% | −0,5% |
| BĐS (Vingroup+) | 10% | 18% | −5% | −2% | +0,2% | −0,5% | +0,2% |
| Thép/Tài nguyên | 15% | 6% | 20% | 15% | +0,8% | +0,3% | +0,5% |
| Bán lẻ/Tiêu dùng | 20% | 10% | 18% | 12% | +0,5% | +0,6% | +0,6% |
| Còn lại | 30% | 28% | 9% | 7% | +0,0% | +0,6% | +0,0% |
| **Tổng** | 100% | 100% | 11,5% | 6,8% | **+1,2%** | **+2,5%** | **+0,8%** |

Excess 4,7% = allocation 1,2% + selection 2,5% + interaction 0,8% + dư 0,2%
```

### Brinson nhiều kỳ (linking)

```
Cộng thẳng từng kỳ sẽ phát sinh dư (do hiệu ứng kép – compounding). Cách xử lý:

Cách 1: cộng số học (arithmetic linking) — đơn giản nhưng còn dư.
Cách 2: Carino logarithmic linking — không dư nhưng phức tạp hơn.

Khuyến nghị thực chiến: với báo cáo quy kết theo THÁNG, cộng số học là đủ; phần dư
thường <0,1%. Khi báo cáo cả năm và dư lớn (do biên độ VN cao, các tháng sóng mạnh),
chuyển sang Carino.
```

## Quy kết theo nhân tố (Factor Attribution)

### Phân rã Alpha–Beta

```
R_p = α + β × R_m + ε

α (alpha): lợi suất vượt trội — kỹ năng nhà quản lý
β (beta): độ phơi nhiễm thị trường — rủi ro hệ thống
ε (epsilon): phần dư — rủi ro phi hệ thống

Hồi quy OLS, tối thiểu ~60 quan sát. R_m = lợi suất VN-Index hoặc VN30
(ưu tiên VN30 nếu danh mục thiên bluechip).
```

#### Quy kết đa nhân tố (mở rộng Fama-French cho VN)

```
R_p − R_f = α + β_mkt×(R_m − R_f) + β_smb×SMB + β_hml×HML + β_mom×MOM + ε

R_f: lợi suất phi rủi ro VN ≈ lãi suất tín phiếu/TPCP kỳ hạn ngắn (không dùng lãi suất Mỹ).

| Nhân tố | Ý nghĩa | Proxy cho TTCK VN |
|------|------|--------|
| MKT | Thị trường | Lợi suất VN-Index (hoặc VN30) − R_f |
| SMB | Phần bù vốn hóa nhỏ | VNSmallcap − VN30 (hoặc rổ smallcap tự dựng − rổ largecap) |
| HML | Phần bù giá trị | Nhóm P/B thấp − nhóm P/B cao |
| MOM | Quán tính | Top tăng 6–12T − Bottom (lưu ý: momentum ở VN yếu/nhiễu hơn do T+2 + lẻ chi phối) |
```

> **Lưu ý xây nhân tố ở VN:** dữ liệu nhân tố dựng sẵn gần như không có sẵn → phải **tự dựng** từ dữ liệu giá + cơ bản (DataPro/vnstock). Mẫu lịch sử ngắn (thị trường non trẻ, nhiều mã mới niêm yết) → t-stat kém ổn định, đừng over-fit. Nhân tố **size (SMB)** và **value (HML)** có hiệu lực rõ ở VN; **momentum** chập chờn do biên độ trần/sàn cắt đuôi xu hướng và dòng lẻ đảo nhanh.

#### Mẫu bảng phơi nhiễm nhân tố

```markdown
### Phân tích phơi nhiễm nhân tố

| Nhân tố | Beta | t-stat | Mức ý nghĩa | Diễn giải |
|------|------|---------|--------|------|
| Thị trường (MKT) | 1,05 | 13,1 | *** | Beta > 1 — danh mục thiên tấn công (đặc trưng DM nhiều midcap VN) |
| Vốn hóa nhỏ (SMB) | 0,35 | 3,8 | *** | Nghiêng smallcap rõ — rủi ro thanh khoản khi thị trường đảo |
| Giá trị (HML) | 0,20 | 2,4 | ** | Nghiêng value nhẹ |
| Quán tính (MOM) | 0,10 | 1,1 | — | Không có ý nghĩa thống kê (momentum VN yếu) |
| **Alpha** | **0,9%/tháng** | **2,6** | ** | **Alpha có ý nghĩa** |

R² = 0,75 → nhân tố giải thích 75% biến động lợi suất.
Alpha 0,9%/tháng ≈ 11%/năm, có ý nghĩa — nhưng kiểm chứng SMB beta cao (rủi ro thanh khoản).
```

## Đánh giá khả năng định thời điểm (Market Timing)

### Mô hình Treynor-Mazuy

```
R_p − R_f = α + β×(R_m − R_f) + γ×(R_m − R_f)² + ε

γ > 0 và có ý nghĩa → có khả năng định thời điểm (tăng beta khi thị trường lên, giảm khi xuống).
γ ≤ 0 → không có khả năng định thời điểm.
```

### Mô hình Henriksson-Merton

```
R_p − R_f = α + β×(R_m − R_f) + γ×max(R_m − R_f, 0) + ε
γ > 0 → beta danh mục cao hơn trong thị trường tăng (định thời điểm thành công).
```

### Chỉ tiêu định thời điểm thực dụng

| Chỉ tiêu | Cách tính | Ý nghĩa |
|------|------|------|
| Tỷ lệ bắt sóng tăng (up-capture) | LS danh mục trong pha tăng / LS benchmark | >100% = vượt trội pha tăng |
| Tỷ lệ chịu sóng giảm (down-capture) | LS danh mục trong pha giảm / LS benchmark | <100% = phòng thủ tốt khi giảm |
| Tỷ lệ đoán đúng hướng | % số tháng đoán đúng hướng thị trường | >55% = có kỹ năng |
| Tương quan đổi vị thế vs thị trường | `corr(thay_đổi_vị_thế, lợi_suất_tương_lai)` | >0 = định thời điểm đúng |

> **Đặc thù VN:** khả năng phòng thủ pha giảm bị giới hạn vì **cấm bán khống cổ phiếu**. Một quỹ chỉ-long muốn hạ beta thực sự khi thị trường xấu phải **bán bớt cổ phiếu sang tiền mặt** hoặc **short VN30F (phái sinh)** để phòng hộ. Down-capture thấp thường đến từ kỷ luật tiền mặt/phái sinh, không phải short cổ phiếu. Khi đánh giá timing của quỹ VN, hỏi rõ họ dùng tiền mặt hay VN30F.

## Khung so sánh benchmark

### Chọn benchmark

| Loại chiến lược | Benchmark khuyến nghị | Ghi chú |
|---------|---------|---------|
| Bluechip vốn hóa lớn VN | **VN30-TRI** (total return) | Công bằng nhất — đã gồm cổ tức |
| Toàn thị trường VN | **VNI-TRI** / VN-Index + cổ tức | VN-Index giá đánh giá thấp benchmark thật |
| Midcap | VNMidcap | Rổ vốn hóa vừa HOSE |
| Smallcap | VNSmallcap | Rổ vốn hóa nhỏ HOSE |
| Quỹ chủ động đa ngành | VN-Index (chuẩn ngành dùng) hoặc 80%VN30 + 20%VNMidcap | Theo thông lệ công bố quỹ |
| Quỹ cân bằng cổ phiếu+TP | Tự dựng (vd 70% VN30-TRI + 30% TPCP) | |

> Phần lớn quỹ mở/ETF VN công bố benchmark là **VN-Index** hoặc **VN30-TRI**. Khi báo cáo nội bộ, luôn kèm cả phiên bản total-return để tránh "ăn gian" alpha bằng cổ tức.

### Chỉ tiêu hiệu suất điều chỉnh rủi ro

| Chỉ tiêu | Công thức | Xuất sắc | Tốt | Trung bình |
|------|------|------|------|------|
| Sharpe | `(R_p − R_f) / σ_p` | >1,5 | 1,0–1,5 | 0,5–1,0 |
| Sortino | `(R_p − R_f) / σ_down` | >2,0 | 1,5–2,0 | 1,0–1,5 |
| Calmar | `R_p / MaxDD` | >1,0 | 0,5–1,0 | 0,2–0,5 |
| Information Ratio | `(R_p − R_b) / TE` | >1,0 | 0,5–1,0 | 0,2–0,5 |
| Treynor | `(R_p − R_f) / β` | dùng để so sánh | | |

> **R_f ở VN:** dùng lãi suất phi rủi ro VND — tín phiếu NHNN / lợi suất TPCP 1 năm (tham chiếu, thường ~2–5% tùy chu kỳ), **không** dùng T-bill Mỹ. Biên độ VN cao nên σ_p lớn → Sharpe tuyệt đối của cổ phiếu VN thường thấp hơn cảm giác; so sánh tương đối với benchmark mới có ý nghĩa.

### Phân tích cuốn chiếu (rolling)

```
Dùng cửa sổ cuốn chiếu (vd 12 tháng) để phân tích:
- Rolling Sharpe: độ ổn định chiến lược
- Rolling alpha: alpha có bền không
- Rolling beta: độ phơi nhiễm thị trường có ổn định không
- Rolling information ratio: tính bền của việc vượt benchmark

Cửa sổ gợi ý: 252 phiên cho dữ liệu ngày, 12–36 tháng cho dữ liệu tháng.
Lưu ý VN: chú ý các "đứt gãy chế độ" (2018 thương chiến, 2020 COVID, 2022 trái phiếu/SCB)
— rolling beta/alpha thường nhảy mạnh quanh các mốc này.
```

## Khung phân tích

### Bước 1: Tổng hợp

```
1. Lợi suất lũy kế vs benchmark (dùng bản TRI)
2. Phân rã excess return (theo năm/tháng)
3. Tóm tắt rủi ro (biến động / sụt giảm tối đa / Sharpe)
```

### Bước 2: Phân rã quy kết

```
1. Brinson (nếu có thông tin ngành — soi trước nhóm ngân hàng & Vingroup)
2. Quy kết nhân tố (alpha / beta / phơi nhiễm)
3. Quy kết định thời điểm (mô hình TM / HM)
```

### Bước 3: Phân tích phong cách (style)

```
1. Phơi nhiễm largecap vs smallcap (VN: smallcap rủi ro thanh khoản cao)
2. Phơi nhiễm growth vs value
3. Phát hiện trôi phong cách (rolling style analysis)
```

### Bước 4: Kết luận & khuyến nghị

```
1. Nguồn chính của excess return
2. Phơi nhiễm rủi ro có hợp lý không (đặc biệt thanh khoản smallcap, tập trung 1–2 mã)
3. Hướng cải thiện
```

## Mẫu output

```markdown
## Báo cáo quy kết hiệu suất (minh họa)

### Tổng quan hiệu suất (vs VN30-TRI)
| Chỉ tiêu | Danh mục | Benchmark | Vượt trội |
|------|------|------|------|
| Lợi suất lũy kế | +85,2% | +52,1% | +33,1% |
| Lợi suất/năm | 12,5% | 8,3% | +4,2% |
| Biến động/năm | 22,5% | 24,0% | − |
| Sharpe | 0,42 | 0,30 | − |
| Information Ratio | 0,71 | − | − |

### Phân rã quy kết
| Nguồn | Đóng góp (/năm) | Tỷ trọng |
|------|-----------|------|
| Phân bổ ngành (allocation) | +1,2% | 29% |
| Chọn cổ phiếu (selection) | +2,5% | 60% |
| Định thời điểm (timing) | +0,5% | 11% |

### Phơi nhiễm nhân tố
[bảng phơi nhiễm nhân tố]

### Kết luận
Excess return chủ yếu đến từ chọn cổ phiếu (60%), kế đến là phân bổ ngành (overweight
thép/bán lẻ, underweight ngân hàng đúng nhịp). Alpha có ý nghĩa (t=2,6) → có năng lực
chọn mã thật. CẢNH BÁO: SMB beta 0,35 (nghiêng smallcap) → rủi ro thanh khoản khi
thị trường đảo; kiểm tra mức tập trung vào vài mã midcap.
```

## Lưu ý quan trọng

1. **Quy kết ≠ dự báo**: quy kết giải thích quá khứ, không bảo đảm lặp lại tương lai.
2. **Benchmark quyết định alpha**: đổi benchmark thì alpha có thể biến mất. **Phải so với bản total-return (VN30-TRI), không phải VN-Index giá** — nếu không, cổ tức bị tính nhầm thành alpha.
3. **Tần suất dữ liệu**: quy kết ngày nhiễu, quy kết tháng ổn định hơn nhưng ít mẫu; quy trình chuẩn là tính theo ngày, báo cáo theo tháng.
4. **Survivorship bias mạnh ở VN**: mã hủy niêm yết / chuyển sàn HOSE→UPCoM (vd HVN, HAG giai đoạn khó khăn, FLC, ROS) dễ bị loại khỏi backtest → tạo alpha giả. Giữ cả mã đã rời sàn.
5. **Đa kiểm định (multiple testing)**: thử 100 chiến lược thì ~5 cái "có ý nghĩa" do ngẫu nhiên (p=0,05); dùng hiệu chỉnh đa so sánh.
6. **Dữ liệu nhân tố tự dựng**: VN không có sẵn factor returns chuẩn → dựng từ DataPro/vnstock; mẫu ngắn, kiểm chứng out-of-sample.
7. **Quy kết trong báo cáo backtest**: `metrics.csv` đã có chỉ tiêu cơ bản sau backtest; skill này bổ sung lớp quy kết sâu hơn.
8. **Tập trung danh mục**: VN dễ tập trung quá mức vào 1–2 mã thanh khoản (HPG/FPT/MWG…). Khi 1 mã đóng góp >40% excess, "selection skill" có thể chỉ là 1 cú đặt cược đúng — soi kỹ.


## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)

1. **Không bịa/cook số liệu.** Mọi số tài chính phải có nguồn thật. Luôn **audit nhanh, cross-check tối thiểu 2 nguồn uy tín** (vd `cafef.vn`, `vietstock.vn`) — dùng **crawl4ai** cào số rồi đối chiếu; nếu nguồn lệch nhau thì nêu rõ, không chọn bừa.
2. **Nếu DataPro VÀ vnstock đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
