---
name: market-microstructure
description: "Cấu trúc vi mô thị trường (TTCK VN): phân tích chênh mua–bán, chỉ số độc tính dòng lệnh (VPIN / Kyle lambda), thước đo thanh khoản (Amihud / Roll), mô hình tác động giá, phân tích sổ lệnh, và đặc thù vi mô VN — khớp lệnh định kỳ ATO/ATC, giao dịch thỏa thuận (block), biên độ trần/sàn, T+2, room ngoại."
category: analysis
---

# Cấu trúc vi mô thị trường (Việt Nam)

## Mục đích

Nghiên cứu cơ chế hình thành giá ở cấp vi mô: ai đang giao dịch, giao dịch thế nào, và giao dịch tác động ra sao lên giá. Với chiến lược định lượng, điều này quan trọng vì giúp ước lượng chi phí giao dịch chính xác hơn, nhận diện dòng tiền thông minh, và tối ưu thực thi.

Tình huống áp dụng:
- Ước lượng chính xác chi phí giao dịch của chiến lược (thay vì giả định một mức phí phẳng 0,1%)
- Thiết kế chiến lược thực thi lệnh lớn (`TWAP / VWAP / IS`)
- Phát hiện độc tính dòng lệnh (tránh khung giờ bị NĐT có thông tin chi phối)
- Định lượng rủi ro thanh khoản (cảnh báo "trắng bên mua" / nằm sàn)
- Khai thác đặc thù vi mô TTCK VN (khớp định kỳ ATO/ATC, giao dịch thỏa thuận, biên độ trần/sàn)

> **Đặc thù vi mô TTCK VN — đọc trước tiên:**
> - **Biên độ trần/sàn**: HOSE ±7%, HNX ±10%, UPCoM ±15%. Khi mã **dư mua trần / dư bán sàn**, sổ lệnh một chiều → gần như không khớp được; mọi thước đo thanh khoản/tác động đều mất ý nghĩa trong phiên đó.
> - **Thanh toán T+2**: cổ phiếu mua phiên T về tài khoản chiều T+2 → không có hành vi "lướt T0" hợp pháp; cấu trúc dòng lệnh khác hẳn thị trường cho bán khống/T0.
> - **Lô chẵn 100 cp** (HOSE), **bước giá** theo mức giá → tạo sàn tự nhiên cho chênh mua–bán.
> - **Room ngoại**: mã hết room → NĐT nước ngoài không mua được trên sàn (chỉ qua thỏa thuận, thường giá cao hơn).
> - **Không có nhà tạo lập (market maker) bắt buộc** cho cổ phiếu thường → thanh khoản hoàn toàn do lệnh NĐT; mã ngoài VN30 sổ lệnh rất mỏng.

## Khái niệm cốt lõi

### Chênh mua–bán (Bid-Ask Spread)

**Ba cách đo:**
| Thước đo | Công thức | Ý nghĩa |
|------|------|------|
| Quoted spread | `Ask − Bid` | Chênh giá tốt nhất hiển thị trên sổ lệnh |
| Effective spread | `2 × |giá khớp − giá giữa|` | Chênh thực tế NĐT phải trả |
| Realized spread | `2 × hướng × (giá khớp − giá giữa sau 5 phút)` | Lợi nhuận thực của bên cung thanh khoản |

```
Ví dụ minh họa (TTCK VN):
  Mã: VCB (bluechip VN30)
  Giá mua tốt nhất: 90.000   Giá bán tốt nhất: 90.100
  Bước giá ≥50.000đ = 100đ → Quoted spread: 100đ = 0,11%

  Mã: smallcap ngoài VN100 (giá thấp, thanh khoản kém)
  Giá mua: 12.000   Giá bán: 12.100
  Bước giá 10.000–49.950đ = 50đ; ở đây dư 100đ → Quoted spread ≈ 0,83%

Phân rã chênh giá (Roll):
  Spread = chi phí lựa chọn bất lợi + chi phí tồn kho + chi phí xử lý lệnh
  TTCK VN: tỷ trọng lựa chọn bất lợi cao (NĐT cá nhân chiếm ~85% GTGD,
  trộn lẫn dòng tiền thông minh) → khó ước lượng, biến động theo tin.

Yếu tố chi phối chênh giá:
  - Vốn hóa lớn hơn   → spread hẹp hơn (VN30 vs penny)
  - Biến động cao hơn → spread rộng hơn
  - Khối lượng lớn hơn→ spread hẹp hơn (cạnh tranh đặt lệnh nhiều)
  - Bất cân xứng thông tin cao → spread rộng hơn (lựa chọn bất lợi)
  - BƯỚC GIÁ là sàn cứng: mã giá thấp có bước giá chiếm % lớn → spread tối thiểu cao
```

### Chỉ số độc tính dòng lệnh

**VPIN (Volume-Synchronized Probability of Informed Trading):**
```
Nguyên lý: thay thời gian đồng hồ bằng "thời gian khối lượng" để đo xác suất giao dịch có thông tin

Các bước tính:
  1. Gom lệnh theo lô khối lượng cố định (Volume Bucket)
     Kích thước lô V = KLGD bình quân ngày / 50 (mỗi lô ~5–10 phút)

  2. Phân loại khối lượng mua/bán trong mỗi lô (Bulk Volume Classification):
     buy_volume  = V × Φ(ΔP / σ)   (CDF chuẩn tắc)
     sell_volume = V − buy_volume

  3. Tính mất cân bằng dòng lệnh:
     OI_i = |buy_volume_i − sell_volume_i|

  4. VPIN = Σ(OI_i) / (n × V)   (cửa sổ trượt n = 50 lô)

Diễn giải:
  VPIN < 0,3   → bình thường, tỷ trọng giao dịch có thông tin thấp
  VPIN 0,3–0,5 → cảnh giác, dòng tiền thông minh đang tăng
  VPIN > 0,5   → nguy hiểm, xác suất cao sắp có thông tin lớn

Ứng dụng TTCK VN:
  VPIN tăng đột biến ở một mã có thể báo trước:
  - giao dịch nội gián trước tin lớn (phát hành, M&A, KQKD đột biến)
  - tổ chức/"đội lái" gom hàng hoặc phân phối
  Cẩn trọng với mã smallcap bị làm giá: VPIN nhiễu do khối lượng "tự mua tự bán".
```

**Kyle's Lambda (hệ số tác động giá)**:
```
Mô hình: ΔP = λ × OrderFlow + ε
  với OrderFlow = khối lượng mua − khối lượng bán

Cách ước lượng:
  1. Tính ΔP và OrderFlow theo cửa sổ 5 phút
  2. Hồi quy ΔP = α + λ × OrderFlow
  3. λ = mức thay đổi giá do một đơn vị dòng lệnh gây ra

Diễn giải:
  λ lớn → thanh khoản kém, tác động cao
  λ nhỏ → thanh khoản tốt, lệnh lớn khớp rẻ

Phân nhóm TTCK VN (giá trị minh họa — phải HIỆU CHỈNH trên dữ liệu thực):
  Bluechip VN30        : λ thấp nhất (sổ lệnh dày)
  Midcap (VNMidcap)    : λ trung bình
  Smallcap / penny     : λ cao, dễ "đẩy" trần/sàn chỉ với lệnh vừa
```

### Thước đo thanh khoản

| Thước đo | Công thức | Ưu điểm | Nhược điểm |
|------|------|------|------|
| Amihud illiquidity | `|R_t| / GTGD_t` | Chỉ cần dữ liệu ngày | Nhạy với lợi suất cực trị |
| Roll implied spread | `2√(−Cov(R_t, R_{t−1}))` | Chỉ cần dữ liệu ngày | Vô hiệu khi hiệp phương sai dương |
| Tỷ lệ phiên lợi suất 0 | số phiên R=0 / tổng phiên | Trực quan | Quá thô |
| Vòng quay (turnover) | KLGD / free float | Đơn giản | Không phản ánh tác động giá |
| Giá trị giao dịch | GTGD bình quân ngày | Thanh khoản tuyệt đối | Không phản ánh tác động tương đối |

```
Tính Amihud (TTCK VN):
  ILLIQ = (1/D) × Σ(|R_d| / GTGD_d)   (D = số phiên, theo tháng)
  Chuẩn hóa: ILLIQ × 10^6 cho dễ đọc

  Ứng dụng:
    - Nhân tố thanh khoản: mã thanh khoản thấp thường có phần bù lợi suất dài hạn
      (liquidity premium) — NHƯNG ở VN dễ trùng với rủi ro làm giá, cần lọc kỹ.
    - Giám sát thanh khoản: ILLIQ tăng vọt → cảnh báo thanh khoản cạn kiệt.
  Lưu ý: ngưỡng phân loại cao/thấp phải hiệu chỉnh trên rổ .VN, không bê nguyên
  ngưỡng từ thị trường khác.
```

## Khung phân tích

### 1. Mô hình tác động giá

**Tác động tuyến tính (Almgren-Chriss)**:
```
Mô hình: impact = η × σ × (Q / V)^0,6
  η: hệ số tác động
  σ: biến động ngày
  Q: khối lượng giao dịch (cp)
  V: KLGD bình quân ngày (cp)

Ví dụ minh họa:
  Bán 100.000 cp một bluechip VN30
  KLGD bình quân 5.000.000 cp, biến động ngày 1,8%
  impact = 1,0 × 0,018 × (100000/5000000)^0,6
         ≈ 0,018 × 0,0085 ≈ 0,015% (1,5bp, chấp nhận được)

  Bán 100.000 cp một mã smallcap
  KLGD bình quân 500.000 cp, biến động ngày 3,0%
  impact = 1,0 × 0,03 × (100000/500000)^0,6
         ≈ 0,03 × 0,076 ≈ 0,23% (23bp, nên chẻ lệnh)

Phương pháp chẻ lệnh:
  TWAP: đều theo thời gian → đơn giản nhưng bỏ qua trạng thái thị trường
  VWAP: theo phân bố khối lượng → khớp nhịp thị trường tốt hơn
  IS:   tối thiểu Implementation Shortfall → tối ưu nhưng cần tối ưu hóa thời gian thực
```

**Tác động phi tuyến (mô hình căn bậc hai)**:
```
impact = σ × √(Q / (ADV × T))
  σ: biến động ngày
  Q: tổng quy mô lệnh
  ADV: giá trị giao dịch bình quân ngày
  T: số phiên thực thi

Áp dụng cho: lệnh lớn (Q/ADV > 5%). Ở VN, mã mid/small chạm ngưỡng này rất sớm.
```

### 2. Phân tích sổ lệnh (LOB)

```
Thước đo độ sâu:
  Độ sâu mức 1: khối lượng chờ tại giá mua/bán tốt nhất
  Độ sâu 3 mức: tổng khối lượng 3 mức đầu (HOSE công bố 3 bước giá mỗi chiều)
  Bất cân xứng độ sâu: (Bid − Ask) / (Bid + Ask)
    > 0 → bên mua mạnh hơn, giá có xu hướng tăng
    < 0 → bên bán mạnh hơn, giá có xu hướng giảm

Độ đàn hồi (resilience):
  Tốc độ sổ lệnh hồi phục sau cú sốc lệnh lớn
  Hồi nhanh → thanh khoản tốt, tác động tạm thời
  Hồi chậm → thanh khoản kém, tác động kéo dài

Đặc điểm sổ lệnh theo khung phiên HOSE:
  - Mỏng nhất quanh ATO (09:00–09:15) — bất cân xứng thông tin cao nhất
  - Cải thiện dần phiên sáng khi tổ chức tham gia
  - Tốt nhất đầu phiên chiều (13:00–14:15) — phần lớn thông tin đã được tiêu hóa
  - Phiên ATC (14:30–14:45) độ sâu biến động mạnh (tranh giá đóng cửa, quỹ/ETF cơ cấu)

Tín hiệu mất cân bằng sổ lệnh:
  OIR = (Bid_vol − Ask_vol) / (Bid_vol + Ask_vol)
  OIR trượt 5 phút > 0,3 → tín hiệu tăng ngắn hạn (độ chính xác ~55–60%)
  Lưu ý VN: chỉ thấy 3 bước giá; lệnh lớn hay bị treo rồi hủy (kê giá ảo) → lọc nhiễu OIR.
```

### 3. Cơ chế "trắng bên mua" / nằm sàn và phòng ngừa

```
Đặc điểm (thay cho "flash crash" ở thị trường có market maker):
  1. Giá rơi nhanh về giá sàn (−7% HOSE) trong thời gian ngắn
  2. Khối lượng phình rồi cạn (thanh khoản bốc hơi)
  3. Chênh mua–bán giãn mạnh; bên mua biến mất ("trắng bên mua")
  4. Mã nằm sàn, dư bán sàn chất đống → KHÔNG khớp được (đặc thù VN: khóa sàn)

Tác nhân:
  - Lệnh bán lớn + thanh khoản mỏng → xuyên thủng nhiều bước giá tức thì
  - Call margin dây chuyền (force-sell) → bán giải chấp kéo theo bán giải chấp
    (cú sập do margin cuối 2022 là ví dụ điển hình: hàng loạt mã nằm sàn nhiều phiên)
  - Cộng hưởng tâm lý NĐT cá nhân → bán tháo đồng loạt
  - Bán chéo ETF/quỹ → rút chứng chỉ quỹ + bán cổ phiếu thành phần khuếch đại đà giảm

Biện pháp phòng ngừa:
  1. Dùng lệnh giới hạn (LO) thay lệnh thị trường (MP) — đặt giá tối đa chấp nhận
  2. Giám sát VPIN: vượt 0,5 → ngừng giao dịch
  3. Ngưỡng thanh khoản: loại mã Amihud quá cao
  4. Giám sát spread: giãn đột ngột >5 lần bình thường → tạm dừng đặt lệnh
  5. Tránh khung giờ: không đẩy lệnh lớn quanh ATO và sát ATC
  6. Quản trị margin: hạ tỷ lệ vay trước vùng rủi ro để tránh bị force-sell ở giá sàn
```

### 4. Đặc thù vi mô TTCK VN

```
Khớp lệnh định kỳ MỞ CỬA (ATO 09:00–09:15):
  - Lệnh ATO/LO tham gia xác định giá mở cửa; HOSE: trong phiên định kỳ
    KHÔNG được hủy/sửa lệnh → ý định thật bộc lộ rõ hơn phiên liên tục.
  - Tín hiệu: dư mua áp đảo dư bán trước 09:15 → khả năng mở cửa tăng giá.
  - Rủi ro: lệnh ATO không có giá; khớp tại giá mở cửa, có thể lệch kỳ vọng.

Khớp lệnh định kỳ ĐÓNG CỬA (ATC 14:30–14:45):
  - Giá đóng cửa quyết định trong 15 phút; tập trung cơ cấu của tổ chức và quỹ chỉ số/ETF.
  - HOSE: trong ATC cũng KHÔNG được hủy/sửa lệnh.
  - Tín hiệu: KL phiên ATC > 10% cả ngày → tổ chức/ETF đang cơ cấu.
  - Ứng dụng:
    * Thuật toán VWAP nên hoàn tất phần lớn trước 14:25, để phần nhỏ vào ATC.
    * Tránh đặt lệnh lớn sát 14:45 (bất định giá cao).
  - Lưu ý: UPCoM KHÔNG có ATO/ATC (chỉ khớp liên tục); HNX có ATC, không có ATO.

Giao dịch thỏa thuận (block / put-through):
  - Tín hiệu chiết khấu = (giá thỏa thuận − giá tham chiếu) / giá tham chiếu
    Chiết khấu < −5%: bên bán nóng lòng thoát → tiêu cực ngắn hạn
    Quanh giá sàn/tham chiếu: có thể chỉ là sang tay, không phải phân phối
  - Bên mua là tổ chức/quỹ uy tín → tín hiệu tích cực
  - Cùng một công ty chứng khoán đứng hai chiều → có thể là sang tay nội bộ (trung tính)
  - Thỏa thuận khối ngoại: thường dùng khi mã HẾT ROOM (mua sàn không được).
```

## Mẫu output

Báo cáo phân tích vi mô (minh họa — số liệu phải lấy từ DataPro/nguồn thật):
```
=== Chẩn đoán thanh khoản ===
Mã: <bluechip VN30>
Ngày: 2026-03-28
GTGD bình quân ngày: <x> tỷ đồng   Vòng quay: <x>%
Amihud: <x> (thanh khoản cao)
Effective spread: <x>% (<x>bp)
Kyle Lambda: <x>

=== Phân tích dòng lệnh ===
VPIN: <x> (bình thường)
Mất cân bằng sổ lệnh (OIR): <±x> (lệch nhẹ bên mua)
Mua ròng lệnh lớn / khối ngoại: <±x> tỷ đồng

=== Ước lượng chi phí giao dịch ===
Quy mô lệnh dự kiến: <x> cp (~<x> tỷ đồng)
Tác động giá ước tính: <x>%
Phí môi giới: 0,15%
Thuế chuyển nhượng (chỉ chiều BÁN): 0,10%
Tổng chi phí 1 chiều mua: ~0,15–0,20% | bán: ~0,25–0,30%

=== Đề xuất thực thi ===
Chiến lược gợi ý: VWAP
Cửa sổ thực thi: 13:00–14:25 (tránh ATO và sát ATC)
Số lát chẻ lệnh: 5–8
Độ nhạy thời gian: thấp (VPIN bình thường, không gấp)
```

## Lưu ý quan trọng

1. **Yêu cầu dữ liệu cao**: phân tích vi mô cần dữ liệu tick / sổ lệnh; dữ liệu ngày thường chỉ đủ cho thước đo thô như Amihud / Roll.
2. **Dữ liệu tick/intraday VN**: lấy qua DataPro (`get_tick`, `get_minute`) hoặc bảng giá môi giới; HOSE chỉ công bố **3 bước giá** mỗi chiều (không có Level-2 sâu 10 mức như một số thị trường).
3. **Hiệu chỉnh VPIN**: kích thước lô ảnh hưởng lớn đến kết quả, phải điều chỉnh theo thanh khoản từng mã — một tham số không hợp cho mọi mã.
4. **Khác biệt thị trường**: **T+2** và **biên độ trần/sàn** khiến vi mô VN khác hẳn mô hình sách giáo khoa thị trường Mỹ (không bán khống đại trà, không market maker bắt buộc).
5. **Ảo giác thanh khoản**: một số mã smallcap có vòng quay cao do **làm giá / tự mua tự bán**, không phản ánh thanh khoản thật — đừng tin con số turnover đơn thuần.
6. **Khóa trần/sàn**: khi mã nằm sàn (dư bán sàn) hoặc nằm trần, sổ lệnh một chiều → mọi tín hiệu OIR/spread/impact đều vô nghĩa trong phiên đó.
7. **Room ngoại**: mã hết room → cầu nước ngoài dồn sang thỏa thuận (giá cao hơn); tín hiệu sổ lệnh trên sàn không phản ánh hết cầu thực.
8. **Chỉ để phân tích**: tín hiệu vi mô phục vụ ước lượng chi phí & chọn thời điểm thực thi, không phải để chạy HFT (hủy/kê lệnh ảo có thể bị xử lý vi phạm).


## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)

1. **Không bịa/cook số liệu.** Mọi số tài chính phải có nguồn thật. Luôn **audit nhanh, cross-check tối thiểu 2 nguồn uy tín** (vd `cafef.vn`, `vietstock.vn`) — dùng **crawl4ai** cào số rồi đối chiếu; nếu nguồn lệch nhau thì nêu rõ, không chọn bừa.
2. **Nếu DataPro VÀ vnstock đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
