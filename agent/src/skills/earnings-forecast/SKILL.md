---
name: earnings-forecast
description: "Dự phóng lợi nhuận & phân tích kỳ vọng thị trường VN (top-down/bottom-up, SUE, PEAD, % hoàn thành kế hoạch ĐHCĐ, momentum điều chỉnh dự phóng) để bắt cơ hội vượt/hụt kỳ vọng. Nguồn: vnstock (EPS thực) + DataPro (phản ứng giá) + báo cáo phân tích."
category: analysis
---
# Dự phóng lợi nhuận & kỳ vọng thị trường (Việt Nam)

## Tổng quan

Xây tín hiệu giao dịch quanh **chênh lệch giữa lợi nhuận thực và kỳ vọng thị trường**. Logic cốt lõi: giá ngắn hạn bị dẫn dắt bởi "chênh kỳ vọng" (expectation gap) — bắt được CHÊNH KỲ VỌNG có giá trị hơn dự báo con số tuyệt đối. Hai trục: ① tự dự phóng vs kỳ vọng để tìm chênh lệch; ② bám momentum điều chỉnh dự phóng của giới phân tích.

> ⚠️ **Trước khi tính (Karpathy):** bóc khoản một lần (lãi tỷ giá/thanh lý/đánh giá lại/hoàn nhập dự phòng) → dùng **LN cốt lõi** trước khi đo SUE; số CP lưu hành từ `Company.overview().issue_share` (không suy từ EPS); EPS thực từ vnstock, đừng đoán.

## Khái niệm cốt lõi

### 1. Dự phóng từ trên xuống (Top-Down)

**Chuỗi dự phóng:**

```
Tăng trưởng GDP → giá trị gia tăng ngành → tăng trưởng doanh thu ngành → DT công ty đầu ngành → giả định biên LN → dự phóng EPS
```

**Ví dụ VN (ngành thép):**

| Lớp | Chỉ tiêu | Logic dự phóng |
|------|------|---------|
| Vĩ mô | GDP +6,5% | Đầu tư công + BĐS hồi phục → cầu thép xây dựng |
| Ngành | Sản lượng thép +8% | Giải ngân hạ tầng, xuất khẩu HRC |
| Công ty | HPG.VN | Sản lượng +10%, giá bán đi ngang → DT ~+10% |
| Biên LN | Biên gộp 13% | Biên thép − quặng/than cải thiện |
| EPS | ~X đồng | LN ròng / issue_share |

**Dùng cho:** định vị chu kỳ LN toàn thị trường, beta ngành, phối hợp chiến lược vĩ mô.

### 2. Dự phóng từ dưới lên (Bottom-Up)

**Ba cách tách doanh thu:**

```python
# Cách 1: tách lượng × giá
revenue = volume * price
# vd HPG = sản lượng thép (triệu tấn) × giá bán (đồng/tấn)

# Cách 2: tách theo mảng/khách hàng
revenue = sum(segment_revenue for segment in business_lines)
# vd FPT = CNTT (xuất khẩu + trong nước) + Viễn thông + Giáo dục/đầu tư

# Cách 3: tách theo cửa hàng/người dùng
revenue = stores * revenue_per_store        # hoặc users * ARPU
# vd MWG = số cửa hàng × doanh thu/cửa hàng; ngân hàng = dư nợ tín dụng × NIM
```

**Điểm then chốt về biên LN:**
- Biên gộp: biến động giá nguyên liệu, nâng cấp cơ cấu sản phẩm
- Tỷ lệ chi phí: hiệu ứng quy mô (DT tăng → tỷ lệ chi phí giảm), đầu tư R&D
- Thuế suất: CIT phổ thông 20%, ưu đãi (công nghệ cao/KCN/dự án mới) thấp hơn — coi chừng ưu đãi hết hạn

### 3. % Hoàn thành kế hoạch ĐHCĐ (đặc thù VN — dùng khi consensus mỏng)

Ở VN, dữ liệu consensus phân tích thường mỏng (nhất là mid/small-cap). **Thay thế bằng KẾ HOẠCH lợi nhuận do ĐHCĐ thông qua** (công bố mùa ĐHCĐ tháng 3-4):

```python
ty_le_hoan_thanh = LN_luy_ke / KH_LN_nam        # so với tiến độ thời gian
# Q1 lý tưởng ~25%, 6T ~50%, 9T ~75%. 
# Vượt tiến độ nhiều → khả năng vượt KH → dư địa điều chỉnh tăng kỳ vọng
# Tụt xa tiến độ → rủi ro hụt KH (lưu ý mùa vụ: nhiều DN dồn LN nửa cuối năm)
```

→ Theo dõi "% hoàn thành kế hoạch" mỗi quý là chỉ báo kỳ vọng phổ biến nhất trên TTCK VN.

### 4. Lợi nhuận bất ngờ chuẩn hóa (SUE)

```python
SUE = (EPS_thuc - EPS_ky_vong) / std(EPS_thuc - EPS_ky_vong)
# EPS_ky_vong = consensus phân tích (trung vị) HOẶC KH ĐHCĐ quy về quý khi thiếu consensus
# std = độ lệch chuẩn chênh lệch dự phóng ~8 quý gần nhất
# EPS_thuc dùng LN CỐT LÕI (đã bóc one-off)
```

| Khoảng SUE | Ý nghĩa | Hành động |
|---------|------|---------|
| SUE > +2,0 | Vượt mạnh | Tín hiệu mua mạnh |
| +1,0 ~ +2,0 | Vượt nhẹ | Tín hiệu mua |
| −1,0 ~ +1,0 | Đúng kỳ vọng | Không tín hiệu |
| −2,0 ~ −1,0 | Hụt nhẹ | Tín hiệu bán/giảm |
| < −2,0 | Hụt mạnh | Tín hiệu bán mạnh |

### 5. Trôi giá sau công bố KQKD (PEAD)

**Hiện tượng:** sau khi công bố BCTC, giá tiếp tục trôi theo hướng vượt/hụt kỳ vọng trong ~30-60 phiên.

```python
# Logic chiến lược (chỉ LONG — NĐT lẻ VN không bán khống được, T+2)
holding_period = 40       # số phiên nắm giữ
sue_threshold = 1.5       # ngưỡng SUE
max_positions = 10
rebalance_on = "earnings_date"   # đảo danh mục quanh ngày công bố
```

**Lưu ý PEAD ở VN:**
- **Chỉ làm phía MUA** — NĐT lẻ không bán khống; mã hụt mạnh thì TRÁNH/giảm, không short.
- Mùa BCTC dồn dập (cuối tháng 4 & tháng 7) → tín hiệu PEAD nhiễu lẫn nhau, cần phân tán.
- **Chậm/không nộp BCTC đúng hạn = cờ ĐỎ** (rủi ro cảnh báo/đình chỉ giao dịch).

### 6. Momentum điều chỉnh dự phóng của giới phân tích

```python
# 1. Tỷ lệ điều chỉnh kỳ vọng (ERM)
ERM = (so_bao_cao_nang - so_bao_cao_ha) / tong_bao_cao_phu_song
# ERM > +0,3 = momentum dương; < −0,3 = âm

# 2. Mức thay đổi kỳ vọng
eps_change_pct = (consensus_moi - consensus_30d_truoc) / abs(consensus_30d_truoc)

# 3. Độ phân tán kỳ vọng
dispersion = std(EPS_cac_analyst) / mean(EPS_cac_analyst)
# > 0,3 = phân hóa cao (bất định); < 0,1 = đồng thuận mạnh
```

**Chiến lược:** Mua khi ERM > +0,3 và eps_change_pct > +5% và dispersion < 0,25. Hiệu lực ~60-90 phiên (momentum suy giảm dần). Lưu ý hiệu ứng bầy đàn của analyst → nhận diện ĐIỂM ĐẢO có giá hơn bám xu hướng.

## Khung phân tích

### Bốn bước
1. **Dựng dự phóng:** chọn Top-Down hoặc Bottom-Up → xuất EPS dự phóng.
2. **Lấy kỳ vọng:** consensus phân tích (nếu có) HOẶC KH LN của ĐHCĐ + % hoàn thành.
3. **Tính chênh lệch:** SUE hoặc % lệch; xác định hướng vượt/hụt (dùng LN cốt lõi).
4. **Sinh tín hiệu:** theo ngưỡng SUE; quản vị thế theo cửa sổ PEAD.

### Lịch BCTC Việt Nam (mốc quan trọng)

| Thời điểm | Sự kiện | Hành động |
|------|------|---------|
| ~30/1 | BCTC quý 4 (chưa kiểm toán) | KQKD cả năm sơ bộ → SUE năm |
| ~31/3 | BCTC năm KIỂM TOÁN (hạn 90 ngày) | Xác nhận SUE, soát chênh kiểm toán & one-off |
| Tháng 3-4 | Mùa ĐHCĐ: công bố **KẾ HOẠCH LN năm** + cổ tức | Lập mốc kỳ vọng cả năm |
| ~30/4 | BCTC quý 1 | SUE Q1, % hoàn thành KH, PEAD |
| ~30/7 | BCTC quý 2 | SUE Q2, % hoàn thành 6T |
| Cuối T8 | BCTC bán niên SOÁT XÉT (hạn 60 ngày) | Điều chỉnh sau soát xét |
| ~30/10 | BCTC quý 3 | Q3 xác nhận kỳ vọng cả năm |

> Mã chậm/không nộp đúng hạn → **cờ đỏ** (HOSE/HNX có thể đưa vào diện cảnh báo/kiểm soát).

### Tham số danh mục chênh kỳ vọng

```python
config = {
    "universe": "VN30 / VNINDEX large-cap",   # thanh khoản + phủ sóng phân tích tốt hơn
    "signal": "SUE > +1.5 hoặc ERM > +0.3 hoặc vượt tiến độ KH mạnh",
    "max_positions": 20,
    "position_weight": "equal",
    "holding_period": 40,                       # phiên
    "rebalance": "earnings_calendar",
    "stop_loss": -0.08,
    "long_only": True,                          # NĐT lẻ VN không short
}
```

## Mẫu output

```markdown
## Dự phóng lợi nhuận — [Mã .VN] [Tên DN]

### Dự phóng
- Phương pháp: [Top-Down / Bottom-Up]
- EPS dự phóng: [X đồng] (LN cốt lõi)
- Cơ sở: [DT +X%, biên LN X%, giả định then chốt]

### So với kỳ vọng
- Kỳ vọng: [consensus EPS X đồng (N báo cáo)] HOẶC [KH LN năm + % hoàn thành lũy kế]
- Chênh lệch: [+X% / −X%] · SUE: [+X,X] · Phân tán: [X,X]

### Momentum phân tích
- ERM: [+X,X] (30 ngày: N nâng / M hạ) · Δ kỳ vọng: [+X%]

### Tín hiệu
- SUE: [mua mạnh/mua/không/bán/bán mạnh] · Momentum: [+/0/−] · Cửa sổ PEAD: [có/không]

### Rủi ro
- [one-off bóp méo EPS, thay đổi chính sách KT, pha loãng, chậm nộp BCTC...]
```

## Lưu ý

- **Dùng LN cốt lõi**: bóc one-off (thanh lý tài sản, lãi tỷ giá, hoàn nhập dự phòng, lãi tài chính bất thường) trước khi tính SUE — xem skill `financial-statement`.
- **Consensus VN mỏng**: mid/small-cap ít báo cáo phủ sóng (<3) → ý nghĩa thống kê yếu; ưu tiên VN30/large-cap, hoặc thay bằng KH ĐHCĐ + % hoàn thành.
- **Mùa vụ**: nhiều DN dồn LN nửa cuối năm (BĐS bàn giao Q4, bán lẻ cao điểm) → đừng ngoại suy quý-trên-quý; xem cùng kỳ.
- **PEAD chỉ LONG**: không bán khống ở VN; tín hiệu hụt → tránh/giảm.
- **Chậm nộp BCTC** là cờ đỏ độc lập (rủi ro cảnh báo/đình chỉ).
- Khung này phục vụ nghiên cứu/backtest, không phải khuyến nghị đầu tư.

## Nguồn dữ liệu

- **EPS/LN THỰC → vnstock nguồn KBS**: `eps` (`earnings_per_share_vnd`) & `net_profit_loss_after_tax` / `attributable_to_parent_company` (bảng `income`); `trailing_eps`, tăng trưởng `profit_before_tax`/`net_revenue` (bảng `ratio`).
- **Phản ứng giá sau công bố / drift PEAD → DataPro** (`source="datapro"`, mã `.VN`): so giá từ ngày công bố qua 40 phiên.
- **Kế hoạch LN ĐHCĐ + consensus/báo cáo phân tích → firecrawl/`web-reader`**: nghị quyết ĐHCĐ, báo cáo SSI/HSC/VCSC/VND, Vietstock, Wichart/FiinPro (consensus + ngày công bố KQKD).
- **issue_share → `Company.overview().issue_share`** (không suy từ EPS).
- ⚠️ vnstock cho EPS THỰC, KHÔNG cho consensus dự phóng — phần kỳ vọng phải lấy từ báo cáo phân tích/KH ĐHCĐ.


## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)

1. **Không bịa/cook số liệu.** Mọi số tài chính phải có nguồn thật. Luôn **audit nhanh, cross-check tối thiểu 2 nguồn uy tín** (vd `cafef.vn`, `vietstock.vn`) — dùng **crawl4ai** cào số rồi đối chiếu; nếu nguồn lệch nhau thì nêu rõ, không chọn bừa.
2. **Nếu DataPro VÀ vnstock đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
