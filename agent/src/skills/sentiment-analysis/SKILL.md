---
name: sentiment-analysis
description: "Phân tích tâm lý thị trường VN — định lượng tham–sợ qua khối ngoại mua/bán ròng, dư nợ margin toàn thị trường, số tài khoản mở mới, thanh khoản/độ rộng, basis phái sinh VN30F. Thị trường ~85–90% NĐT lẻ → dùng làm chỉ báo ngược ở vùng cực đoan. Nguồn: DataPro (khối ngoại/giá/KL) + VSD/CTCK (margin, tài khoản)."
category: analysis
---

# Phân tích tâm lý thị trường (Việt Nam)

## Mục đích

Định lượng "tham lam & sợ hãi" thành chỉ tiêu đo được. TTCK VN do **NĐT lẻ chi phối (~85–90% giá trị khớp lệnh)** nên tâm lý đám đông biên độ rất lớn — chỉ báo tâm lý ở **vùng cực đoan** thường là **chỉ báo ngược** hiệu quả. Năm trục đặc thù VN: **khối ngoại, dư nợ margin, tài khoản mở mới, thanh khoản & độ rộng, phái sinh**.

> Lưu ý: VN **không** có chỉ số Fear & Greed thống nhất, **không** có thị trường quyền chọn cổ phiếu để tính Put-Call Ratio chuẩn. Đừng bê nguyên khung Mỹ/Trung; dùng các đại lượng dưới đây.

## 1. Khối ngoại (dòng tiền nước ngoài) — ⭐ trục được theo dõi nhất

```
Khối ngoại mua/bán ròng = giá trị nước ngoài mua − bán (theo mã & toàn thị trường).
  Nguồn: DataPro (trường khối ngoại theo mã .VN).

Ý nghĩa:
  - Bán ròng kéo dài (chuỗi tuần/tháng) → áp lực cung + tâm lý dè dặt (giai đoạn 2020–2023
    khối ngoại bán ròng kỷ lục hàng tỷ USD, đè nhóm bluechip VN30).
  - Mua ròng mạnh trở lại, đặc biệt vào bluechip/VNDIAMOND → xác nhận dòng vốn quay lại.

Cách dùng đúng:
  - Xem LŨY KẾ tuần/tháng, bỏ nhiễu ngày lẻ.
  - Tách dòng CHỦ ĐỘNG vs ETF (tạo lập E1VFVN30/FUEVFVND/Fubon/VanEck) — dòng ETF mang
    tính phân bổ thụ động, không phải quan điểm chọn cổ phiếu (xem skill etf-analysis).
  - Trọng số khối ngoại GIẢM dần khi lẻ áp đảo → không còn "tín hiệu thông minh" tuyệt đối
    như giai đoạn trước; kết hợp với margin/thanh khoản.
```

## 2. Dư nợ margin toàn thị trường — đo đòn bẩy & hưng phấn

```
Dư nợ margin (cho vay ký quỹ) toàn thị trường: tổng hợp từ BCTC quý các CTCK / số liệu VSD.

Tín hiệu:
  - Margin LẬP ĐỈNH lịch sử + margin/vốn hóa cao + margin chạm trần vốn chủ CTCK
    → đòn bẩy căng, "hết dư địa bơm" → vùng rủi ro đỉnh (cuối 2021 margin kỷ lục → 2022 sập).
  - Margin co mạnh sau call/force-sell → đã rũ đòn bẩy, gần vùng tạo đáy.

Vòng xoáy giải chấp: thị trường giảm → call margin → force-sell → giá sàn → call thêm
  (xem skill regulatory-knowledge). Khi nghe "căng margin", cảnh giác chuỗi sàn liên phiên.
```

## 3. Số tài khoản mở mới — nhịp tham gia của NĐT lẻ (F0)

```
Số tài khoản chứng khoán mở mới hằng tháng (VSD công bố).

Chỉ báo ngược ở cực đoan:
  - Mở mới BÙNG NỔ kỷ lục (làn sóng "F0" 2021–2022) → hưng phấn đỉnh, dòng tiền lẻ đu đỉnh.
  - Mở mới cạn kiệt, NĐT chán nản rời thị trường → vùng đáy tâm lý.
"Khi bác xe ôm/quán cà phê bàn cổ phiếu" = dấu hiệu đỉnh (phiên bản VN của chỉ báo Buffett).
```

## 4. Thanh khoản & độ rộng thị trường

| Chỉ tiêu | Cực sợ hãi | Cực tham lam |
|------|------|------|
| GTGD bình quân toàn thị trường | Cạn kiệt (rút mạnh so trung bình) | Bùng nổ kỷ lục (FOMO lẻ) |
| Số mã tăng TRẦN / giảm SÀN | Sàn la liệt | Trần hàng loạt (đầu cơ nóng) |
| Độ rộng (mã tăng/mã giảm) | < 0,3 | > 3–5 |
| % mã trên MA50/MA200 | Rất thấp (<20%) | Rất cao (>80%) |

> Thanh khoản là "nhiệt kế" của thị trường lẻ VN: GTGD tăng vọt cùng giá = tiền nóng vào;
> giá tăng nhưng GTGD teo = phân phối/thiếu xác nhận.

## 5. Phái sinh VN30F & chứng quyền

```
Basis VN30F = giá HĐTL VN30 − VN30 spot:
  Basis ÂM sâu kéo dài (futures discount) → kỳ vọng bi quan/phòng hộ mạnh → có thể đảo chiều.
  Basis DƯƠNG cao (futures premium) → lạc quan thái quá.
Khối lượng phái sinh tăng vọt khi cơ sở giảm → NĐT đổ sang short phái sinh phòng hộ (sợ hãi).
Chứng quyền (CW): khối lượng/độ nóng CW call tăng đột biến → đầu cơ đòn bẩy cao (tham).
```

## 6. Mạng xã hội & diễn đàn (định tính)

```
Kênh VN: F319, Fireant, diễn đàn Vietstock, các nhóm "phím hàng" Facebook/Zalo/Telegram,
  KOL chứng khoán YouTube/TikTok.
Đo: độ nóng thảo luận (tần suất nhắc mã vs nền), tỷ lệ hô mua/bán, mức độ đồng thuận KOL.
Chỉ báo ngược: đồng thuận hô mua >80% + "room" rần rần + chê người thận trọng = nguy hiểm.
Nhiễu: đội lái/"phím hàng" có chủ đích, bot → lọc kỹ, chỉ dùng định tính bổ trợ.
```

## Khung điểm tâm lý tổng hợp

```
Tâm lý tổng hợp (chuẩn hóa 0–100, vùng cực đoan dùng chỉ báo NGƯỢC):
  ≈ 0,25×khối_ngoại + 0,25×margin + 0,20×thanh_khoản/độ_rộng
    + 0,15×tài_khoản_mở_mới + 0,15×basis_phái_sinh

0–20  Cực sợ hãi   → vùng tích lũy (mua dần, cần nền cơ bản, không bắt dao rơi do vỡ nợ)
20–40 Sợ hãi       → tăng dần tỷ trọng
40–60 Trung tính   → chỉ báo tâm lý kém tác dụng, nhìn yếu tố khác
60–80 Tham lam     → giảm dần tỷ trọng
80–100 Cực tham lam → hạ về vùng an toàn (đừng short xu hướng mạnh; phòng hộ qua VN30F)
```

## Mẫu output

```markdown
## Tâm lý thị trường VN (minh họa)

### Bảng đo
| Chỉ tiêu | Giá trị | Phân vị | Tín hiệu |
|------|------|------|------|
| Khối ngoại ròng (tuần) | −1.200 tỷ | 15% | Bán ròng (đè) |
| Dư nợ margin | gần đỉnh LS | 90% | Đòn bẩy căng |
| Tài khoản mở mới (tháng) | cao | 80% | Lẻ hưng phấn |
| GTGD bình quân | bùng nổ | 85% | FOMO |
| Basis VN30F | dương cao | 75% | Lạc quan |

### Điểm tổng hợp: 72/100 (vùng tham lam)

### Diễn giải
Lẻ hưng phấn (margin + tài khoản + thanh khoản đỉnh) nhưng khối ngoại BÁN RÒNG →
phân kỳ: dòng tiền lẻ đỡ giá còn ngoại thoát. Rủi ro đảo chiều khi margin hết dư địa.

### Hành động
- Hạ tỷ trọng về vùng an toàn; không đu trần.
- Phòng hộ beta bằng short VN30F thay vì cố short cổ phiếu (VN cấm bán khống).
- Chờ margin rũ bớt / khối ngoại ngừng bán để mua lại.

### Cảnh báo
Chỉ báo tâm lý là chỉ báo NGƯỢC, không phải công cụ định thời điểm chính xác — xu hướng
mạnh có thể giữ trạng thái cực đoan rất lâu.
```

## Lưu ý quan trọng

1. **Chỉ báo ngược ≠ định thời điểm chính xác**: tâm lý có thể neo cực đoan rất lâu; đừng short/long chỉ vì tâm lý.
2. **Kết hợp tâm lý + xu hướng**: tham lam trong uptrend mạnh là bình thường; sợ hãi trong downtrend cũng vậy.
3. **Khối ngoại đã giảm trọng số**: lẻ áp đảo → tín hiệu ngoại không còn "thông minh tuyệt đối"; luôn chéo với margin/thanh khoản.
4. **Margin & tài khoản có độ trễ**: margin theo quý (BCTC CTCK), tài khoản theo tháng (VSD) → là bức tranh trễ, dùng cho bối cảnh hơn là tín hiệu ngày.
5. **Phân kỳ lẻ vs ngoại** là một trong những tín hiệu cảnh báo đỉnh giá trị nhất ở VN (lẻ FOMO trong khi ngoại + tự doanh thoát).
6. **Nhiễu mạng xã hội**: "phím hàng"/đội lái có chủ đích → chỉ dùng định tính, lọc kỹ.

## Nguồn dữ liệu (VN)

| Việc cần | Nguồn |
|------|------|
| **Khối ngoại mua/bán ròng** (mã & thị trường), giá, KL, GTGD, độ rộng | **DataPro** (`source="datapro"`, mã `.VN`; trường khối ngoại) |
| Dư nợ margin toàn thị trường | BCTC quý các CTCK / tổng hợp VSD (số liệu trễ; nhập tay/nguồn ngoài) |
| Số tài khoản mở mới | **VSD** công bố hằng tháng (nguồn ngoài) |
| Basis & khối lượng VN30F, chứng quyền | DataPro/HNX (phái sinh), HOSE (CW) |
| Tâm lý mạng xã hội (định tính) | F319/Fireant/Vietstock/nhóm MXH (nguồn ngoài, lọc nhiễu) |

Khi thiếu dữ liệu trực tiếp: nêu hạn chế, đưa khung phân tích, KHÔNG bịa số.
