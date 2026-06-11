---
name: fund-analysis
description: "Phân tích & sàng lọc quỹ tại VN — quỹ mở (cổ phiếu/trái phiếu/cân bằng) và ETF nội: hiệu suất (Sharpe/Sortino/IR), phân tích phong cách & trôi phong cách, đánh giá nhà điều hành quỹ, chọn ETF, xây danh mục FOF. Nguồn: vnstock Fund (Fmarket: NAV/holdings) + DataPro (giá ETF/chỉ số)."
category: asset-class
---

# Phân tích & sàng lọc quỹ (Việt Nam)

## Mục đích

Đánh giá có hệ thống hiệu suất, phong cách đầu tư và năng lực điều hành của **quỹ mở** (cổ phiếu/trái phiếu/cân bằng) và **ETF niêm yết** tại VN, từ đó xây danh mục FOF (quỹ của các quỹ). Mục tiêu cốt lõi: tìm **nguồn alpha bền vững**, không phải quỹ "có thành tích quá khứ tốt nhất".

Tình huống áp dụng:
- Sàng lọc đa chiều quỹ cổ phiếu / cân bằng
- Quy kết phong cách nhà điều hành & phát hiện trôi phong cách (style drift)
- Đánh giá hiệu quả bám chỉ số (tracking error) của ETF nội
- Phân bổ tài sản & tái cân bằng cho danh mục FOF

## ⚠️ Đặc thù thị trường quỹ Việt Nam (đọc TRƯỚC)

1. **Hai cơ chế giao dịch khác hẳn nhau:**
   - **Quỹ mở** (DCDS, VESAF, SSISCA, VCBF-BCF...): mua/bán **chứng chỉ quỹ (CCQ) theo NAV** tại phiên định kỳ (thường tuần hoặc ngày T), **không khớp trên sàn** → không có khái niệm chiết khấu/phụ trội. Lệnh bán nhận tiền sau vài ngày làm việc.
   - **ETF niêm yết** (E1VFVN30, FUEVFVND, FUESSVFL, FUEVN100...): **giao dịch trên HOSE như cổ phiếu** (T+2, biên độ ±7%) → có giá thị trường, có chiết khấu/phụ trội so với iNAV.
2. **Số quỹ ít, lịch sử ngắn**: thị trường chỉ ~50–60 quỹ mở, nhiều quỹ tuổi đời < 5 năm → khó đủ một chu kỳ tăng–giảm trọn vẹn. Nới ngưỡng nhưng phải ghi rõ hạn chế dữ liệu.
3. **Phí bán bậc thang theo thời gian nắm giữ** (đặc trưng quỹ mở VN): nắm < 12 tháng phí bán cao (~1,5–3%), giảm dần, **> 24 tháng thường 0%** → thiết kế khuyến khích nắm dài. Phí mua nhiều quỹ miễn.
4. **Lãi suất phi rủi ro (Rf)**: dùng **lợi suất trái phiếu Chính phủ VN kỳ hạn 1 năm** (hoặc lãi tiền gửi 12 tháng NH lớn), thường ~2–5%.
5. **Thuế**: cá nhân bán CCQ/ETF chịu **thuế TNCN 0,1% trên giá trị bán** (như cổ phiếu).
6. **Quản lý**: quỹ do **UBCKNN** cấp phép, bắt buộc có **ngân hàng giám sát (custodian)**; NAV được giám sát công bố định kỳ.

## Bộ chỉ tiêu hiệu suất quỹ

**Nhóm lợi suất**:
| Chỉ tiêu | Công thức | Ngưỡng tốt | Ghi chú |
|------|------|----------|------|
| Lợi suất annualized | (1+tổng LN)^(1/số năm)−1 | > 15% (quỹ CP) | Lợi nhuận tuyệt đối |
| Alpha (vượt chuẩn) | LN quỹ − LN benchmark | > 3%/năm | Tương đối benchmark |
| Information Ratio (IR) | Alpha / tracking error | > 0,5 | Độ ổn định của alpha |
| Tỷ lệ thắng | % số tháng vượt benchmark | > 55% | Tính nhất quán |

**Nhóm rủi ro**:
| Chỉ tiêu | Công thức | Ngưỡng tốt | Ghi chú |
|------|------|----------|------|
| Sụt giảm tối đa (MDD) | max(đỉnh−đáy)/đỉnh | < 25% (quỹ CP) | Rủi ro cực đoan |
| Biến động annualized | std(LN ngày)×√252 | < 25% (quỹ CP) | Tổng rủi ro |
| Độ lệch chuẩn phía dưới | std(LN âm)×√252 | < 15% | Rủi ro phía giảm |
| Calmar | LN năm / MDD | > 1,0 | LN trên rủi ro cực đoan |

**Nhóm điều chỉnh rủi ro**:
| Chỉ tiêu | Công thức | Ngưỡng tốt | Ghi chú |
|------|------|----------|------|
| Sharpe | (Rp−Rf)/σp | > 1,0 | LN trên mỗi đơn vị tổng rủi ro |
| Sortino | (Rp−Rf)/σ phía dưới | > 1,5 | Chú trọng rủi ro phía giảm |
| Treynor | (Rp−Rf)/β | — | LN trên rủi ro hệ thống |

```
Rf: lợi suất trái phiếu Chính phủ VN 1 năm (hoặc lãi tiền gửi 12T), ~2–5%
Benchmark:
  Quỹ cổ phiếu        → VN-Index (quỹ large-cap có thể dùng VN30)
  Quỹ cân bằng        → VN-Index × tỷ trọng CP + Rf × tỷ trọng trái phiếu (vd 60/40)
  Quỹ trái phiếu      → lãi tiền gửi 12T hoặc chỉ số trái phiếu
Chu kỳ đánh giá: tối thiểu 3 năm, ưu tiên 5 năm. Quỹ VN nhiều quỹ trẻ → ghi rõ nếu < 3 năm.
```

## Phân tích phong cách (style) & trôi phong cách

VN **chưa có** hệ chỉ số value/growth con đủ tốt để dựng "lưới 9 ô" như TQ/Mỹ. Thay vào đó, quy kết phong cách bằng **hồi quy lợi suất quỹ lên các chỉ số quy mô & nhóm ngành của VN**:

```
Ri = α + Σ βk × R(chỉ số_k) + ε

Rổ chỉ số phong cách (VN):
  Quy mô:  VN30 (large) · VNMIDCAP (mid) · VNSMALLCAP (small)
  Nhóm:    VNFINLEAD/VNFIN (ngân hàng–tài chính) · VNDIAMOND (hết room ngoại)
           · VNCONS (tiêu dùng) · các rổ ICB ngành khác

Diễn giải:
  β lớn nhất  → phong cách/độ phơi nhiễm chủ đạo của quỹ
  R² > 0,85   → phong cách rõ ràng; R² < 0,70 → mờ / thiên về chọn thời điểm
```

**Phát hiện trôi phong cách**:
```
Phương pháp: hồi quy cửa sổ trượt (cửa sổ 60 phiên, bước nhảy 20 phiên)

Tín hiệu trôi:
  |Δβ| > 0,2 giữa các cửa sổ liền kề          → trôi đáng kể
  β lớn nhất đổi chỉ số                        → đổi phong cách
  R² giảm dần kéo dài                          → điều hành lệch benchmark / chọn thời điểm

Kiểu trôi:
  - Trôi dần:   large → mid → small (thường do quy mô tăng buộc xuống cỡ nhỏ hơn)
  - Trôi đột:   đổi nhóm ngành đột ngột (có thể đã đổi nhà điều hành)
  - Trôi chu kỳ: thị trường tăng đuổi tăng trưởng, giảm chuyển phòng thủ (chọn thời điểm)

Kiểm "danh không xứng thực": phong cách công bố ≠ phong cách hồi quy thực tế.
```

## Khung phân tích

### 1. Sàng lọc quỹ (5 bước)

```
Bước 1: Lọc cứng
  □ Thành lập ≥ 3 năm (quỹ VN trẻ: nới ≥ 2 năm + ghi rõ hạn chế lịch sử)
  □ Quy mô (AUM) ≥ ~100 tỷ đồng (quá nhỏ → rủi ro đóng quỹ/thanh khoản CCQ)
  □ Cùng một nhà điều hành ≥ 2 năm
  □ Quy mô CCQ ổn định (không sụt giảm bất thường nhiều kỳ liên tiếp)

Bước 2: Xếp hạng hiệu suất
  □ LN annualized 3 năm > trung vị cùng loại
  □ Sharpe 3 năm > top 30% cùng loại
  □ MDD < trung vị cùng loại
  □ Information Ratio > 0,3

Bước 3: Kiểm phong cách
  □ Phong cách thực tế khớp công bố (R² > 0,8)
  □ Điểm trôi phong cách thấp (ổn định)
  □ Phong cách 1 năm gần đây khớp 3 năm

Bước 4: Đánh giá nhà điều hành
  □ Điều hành quỹ cùng loại ≥ 3 năm
  □ Lịch sử các quỹ từng quản đều có alpha dương
  □ Vòng quay danh mục hợp lý (quá cao → giao dịch nhiều, bào phí)
  □ Độ tập trung hợp lý (top 10 nắm giữ ~40–70%)

Bước 5: Kiểm phí
  □ Phí quản lý ≤ 2,0% (quỹ CP chủ động); ETF ~0,65–0,8%
  □ Phí bán bậc thang về 0% khi nắm dài (≤ ~24 tháng); ưu tiên phí mua thấp/miễn
  □ Phí giám sát + quản trị hợp lý (~0,1–0,3%)
```

### 2. Đánh giá nhà điều hành quỹ

```
Trục cốt lõi:
  1. Năng lực tạo alpha:
     Alpha annualized trong nhiệm kỳ (so benchmark)
     Alpha thị trường tăng vs thị trường giảm (quỹ giỏi có alpha cả khi giảm)

  2. Kiểm soát rủi ro:
     MDD quỹ vs MDD benchmark
     Downside capture < 0,8  → giỏi hãm đà giảm
     Upside capture  > 1,0   → không tụt lại khi thị trường tăng

  3. Chọn cổ phiếu vs chọn thời điểm (mô hình Treynor–Mazuy):
     Ri−Rf = α + β(Rm−Rf) + γ(Rm−Rf)² + ε
     α > 0 → có năng lực chọn cổ phiếu
     γ > 0 → có năng lực chọn thời điểm
     Thực nghiệm: phần lớn nhà điều hành mạnh chọn cổ phiếu, hiếm ai chọn thời điểm tốt.

  4. Đặc điểm danh mục:
     Vòng quay: thấp = nắm dài; cao = giao dịch nhiều (bào phí, rủi ro thanh khoản)
     Độ tập trung top 10: > 70% = tập trung; < 40% = phân tán
     Độ lệch ngành so benchmark (theo ICB)

Tín hiệu đổi nhà điều hành:
  - Người mới cùng công ty, phong cách tương tự → ảnh hưởng nhỏ
  - Người mới phong cách khác hẳn → đánh giá lại, quan sát 1–2 quý
  - Nhân sự chủ chốt rời đi → cân nhắc rút, theo dõi sản phẩm khác của họ
```

### 3. Chọn ETF (niêm yết)

```
Tiêu chí cốt lõi:
  1. Tracking error (so chỉ số tham chiếu):
     std(LN ngày ETF − LN ngày chỉ số) × √252
     ETF nội thường 0,5–2%/năm (cao hơn ETF Mỹ do thanh khoản rổ + dòng khối ngoại)

  2. Phí: quản lý ~0,65–0,8% + giám sát/lưu ký. Chênh phí tích lũy nhiều năm là đáng kể.

  3. Thanh khoản (giao dịch trên HOSE):
     GTGD bình quân ngày càng cao càng tốt
     Spread mua–bán hẹp → chi phí giao dịch thấp
     Chiết khấu/phụ trội so iNAV nhỏ → định giá sát

  4. Quy mô: AUM lớn → rủi ro đóng quỹ thấp, tạo lập sôi động hơn

ETF nội tham chiếu (chỉ số bám):
  | ETF        | Chỉ số bám   | Đặc điểm |
  |------------|--------------|----------|
  | E1VFVN30   | VN30         | Bluechip large-cap, thanh khoản tốt nhất |
  | FUEVFVND   | VNDIAMOND    | Cổ phiếu hết room ngoại (NĐT nước ngoài ưa chuộng) |
  | FUESSVFL   | VNFINLEAD    | Ngân hàng – tài chính dẫn dắt |
  | FUEVN100   | VN100        | Large + mid, rộng hơn VN30 |
  (đối chiếu phí/quy mô/TE tại thời điểm phân tích — số liệu thay đổi liên tục)
```

### 4. Xây danh mục FOF

```
Bước 1: Phân bổ đại loại tài sản
  Thận trọng: quỹ CP 30% + quỹ trái phiếu 50% + tiền/quỹ tiền tệ 20%
  Cân bằng:   quỹ CP 50% + quỹ trái phiếu 30% + quỹ cân bằng 10% + tiền 10%
  Tăng trưởng: quỹ CP 70% + quỹ trái phiếu 20% + tiền 10%

Bước 2: Chọn quỹ trong từng lớp
  Mỗi lớp chọn 2–3 quỹ (phân tán rủi ro nhà điều hành).
  Phần cổ phiếu: ghép phong cách bổ sung nhau (large-cap + mid/small + chủ đề như VNDIAMOND).
  Phần trái phiếu: ưu tiên chất lượng tín dụng, không đuổi lợi suất cao rủi ro.

Bước 3: Quy tắc tái cân bằng
  Định kỳ: rà mỗi quý.
  Kích hoạt: bất kỳ lớp tài sản lệch mục tiêu > 5% → tái cân bằng.
  Ưu tiên dùng dòng tiền mới / phân phối để bù lớp thiếu → giảm phí bán (nhớ phí bán bậc thang!).

Bước 4: Giám sát cảnh báo
  □ Một quỹ xếp hạng cuối 30% cùng loại 2 quý liên tiếp → quan sát
  □ Đổi nhà điều hành → đánh giá lại
  □ Trôi phong cách → cân nhắc thay bằng quỹ ổn định cùng loại
  □ Quy mô CCQ biến động bất thường (tăng/giảm mạnh) → rủi ro thanh khoản
```

## Mẫu output

```markdown
=== Hồ sơ quỹ === (số liệu minh họa)
Tên: DC Chứng khoán Năng động (DCDS) — quỹ mở cổ phiếu
Điều hành: Dragon Capital   Loại: cổ phiếu, large-cap
AUM: ... tỷ đồng   Phong cách: large-cap blend

=== Hiệu suất (3 năm) ===
LN annualized: ...%  (top ...% cùng loại)
Sharpe: ...          (top ...% cùng loại)
MDD: −...%           (trung vị cùng loại −...%)
Information Ratio: ...
Calmar: ...
Tỷ lệ thắng: ...% (số tháng vượt VN-Index)

=== Phân tích phong cách ===
Phong cách hồi quy: large-cap (β cao nhất ở VN30, R²=...)
Trôi phong cách: thấp (1 năm khớp 3 năm)
Độ tập trung top 10: ...%
Vòng quay: ... (nắm dài / giao dịch nhiều)

=== Đánh giá ===
Ưu: chọn cổ phiếu tốt (α dương), phong cách ổn định
Nhược: ... (vd kiểm soát MDD bình thường)
Đề xuất: phù hợp làm cấu phần large-cap trong FOF, tỷ trọng 15–20%

Lưu ý: Đây là nghiên cứu, không phải khuyến nghị đầu tư.
```

## Lưu ý quan trọng

1. **Thiên kiến sống sót**: quỹ đã giải thể/sáp nhập thường bị loại khỏi dữ liệu → trung bình lịch sử bị thổi phồng.
2. **Lịch sử ngắn (đặc thù VN)**: nhiều quỹ < 5 năm, chưa qua chu kỳ giảm sâu → đừng ngoại suy hiệu suất giai đoạn tăng thành "năng lực".
3. **Hiệu ứng quy mô**: quỹ AUM lớn khó thực thi chiến lược mid/small-cap (thanh khoản mỏng) → alpha có thể giảm.
4. **Phí bán bậc thang**: vào/ra ngắn hạn quỹ mở bị phí bán cao bào mòn lợi nhuận — luôn tính phí bán theo thời gian nắm giữ dự kiến.
5. **Phí bào lợi nhuận dài hạn**: chênh phí quản lý 1% giữa quỹ chủ động và ETF, tích lũy 10 năm tạo khác biệt lớn về LN.
6. **ETF "bám" mà lệch lớn**: tracking error ETF nội có thể cao bất thường do dòng khối ngoại + thanh khoản rổ; soi TE thực tế thay vì tin nhãn.
7. **Quỹ cổ phiếu ≠ ETF về định giá**: quỹ mở giao dịch tại NAV (không chiết khấu/phụ trội); ETF có chiết khấu/phụ trội so iNAV — đừng lẫn hai cơ chế.

## Nguồn dữ liệu (VN)

| Việc cần | Nguồn |
|------|------|
| **Danh sách quỹ mở, loại quỹ, công ty QLQ, NAV, hiệu suất** | **vnstock `Fund()`** (nguồn Fmarket): `Fund().listing()` → `short_name`, `fund_type`, `owner_name`; `Fund().filter(symbol)` |
| Lịch sử NAV quỹ mở (tính LN/Sharpe/MDD) | **vnstock** `Fund().details.nav_report(symbol)` (vd `symbol="DCDS"`, `"VESAF"`, `"VCBF-BCF"`) |
| Top cổ phiếu nắm giữ | **vnstock** `Fund().details.top_holding(symbol)` |
| Phân bổ ngành của danh mục | **vnstock** `Fund().details.industry_holding(symbol)` |
| Phân bổ loại tài sản (CP/trái phiếu/tiền) | **vnstock** `Fund().details.asset_holding(symbol)` |
| **Giá ETF niêm yết** (E1VFVN30, FUEVFVND, FUESSVFL, FUEVN100...) | **DataPro** (`source="datapro"`, mã `.VN`) — như cổ phiếu, để tính TE/chiết khấu |
| Giá chỉ số benchmark (VN-Index, VN30, VNMIDCAP, VNDIAMOND...) | **DataPro** (`VNINDEX.VN`, `VN30.VN`...) |
| Cơ bản cổ phiếu trong danh mục (soi holdings) | **vnstock KBS** (`ratio`/`income`); phân ngành ICB qua `Listing.symbols_by_industries()` |
| Rf (lợi suất TPCP 1 năm / lãi tiền gửi 12T) | nguồn vĩ mô; xem skill `macro-analysis` |

> **vnstock `Fund()` chỉ phủ quỹ mở phân phối qua Fmarket.** ETF niêm yết lấy GIÁ qua DataPro; NAV/iNAV ETF công bố tại website công ty QLQ.

Khi không có dữ liệu trực tiếp: nêu hạn chế và đưa khung phân tích, KHÔNG bịa số hiệu suất/NAV.

## Phụ thuộc

```bash
pip install pandas numpy scipy vnstock
```


## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)

1. **Không bịa/cook số liệu.** Mọi số tài chính phải có nguồn thật. Luôn **audit nhanh, cross-check tối thiểu 2 nguồn uy tín** (vd `cafef.vn`, `vietstock.vn`) — dùng **crawl4ai** cào số rồi đối chiếu; nếu nguồn lệch nhau thì nêu rõ, không chọn bừa.
2. **Nếu DataPro VÀ vnstock đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
