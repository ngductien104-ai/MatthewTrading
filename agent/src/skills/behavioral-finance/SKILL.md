---
name: behavioral-finance
description: "Tài chính hành vi cho TTCK Việt Nam — phản ứng thái quá/dưới mức (overreaction/underreaction), giải thích hành vi cho momentum & đảo chiều, chu kỳ tâm lý NĐT, checklist thiên lệch nhận thức, và khử thiên lệch trong chiến lược định lượng. Bối cảnh: thị trường ~85–90% NĐT lẻ → thiên lệch hành vi đậm, xoay vòng ngành nhanh."
category: analysis
---

# Tài chính hành vi (Việt Nam)

## Mục đích

Chuyển lý thuyết tài chính hành vi thành tín hiệu giao dịch đo được và quy tắc kiểm soát rủi ro. Giả định cốt lõi: người tham gia thị trường lệch khỏi quyết định lý trí một cách hệ thống, và các thiên lệch đó có thể dự báo & khai thác.

> **Đặc thù VN:** thị trường **NĐT lẻ chi phối ~85–90% GTGD** → thiên lệch hành vi (bầy đàn, FOMO, neo giá, sợ thua lỗ) **đậm hơn cả A股/Mỹ**, nhưng **xoay vòng ngành rất nhanh** → cửa sổ momentum ngắn. Cảnh báo dữ liệu: mọi con số mẫu dưới đây là **khung tham chiếu định tính — phải tự backtest trên dữ liệu .VN**, không bê thẳng thành tham số giao dịch.

Tình huống áp dụng:
- Diễn giải hành vi & tối ưu tham số cho chiến lược momentum/đảo chiều
- Tín hiệu ngược khi tâm lý thị trường cực đoan (chéo với [[sentiment-analysis]])
- Cơ chế khử thiên lệch trong xây dựng danh mục
- Bắt mẫu hành vi đặc thù thị trường lẻ VN (đội lái/phím hàng — xem [[social-media-intelligence]])

## Khái niệm cốt lõi

### Phản ứng dưới mức & phản ứng thái quá

**Phản ứng dưới mức (underreaction) → hiệu ứng momentum:**
```
Cơ chế: thiên lệch neo (anchoring) + bảo thủ (conservatism)
  NĐT neo vào thông tin cũ, cập nhật chậm trước thông tin mới.
  Sau khi KQKD vượt kỳ vọng, giá ngấm DẦN chứ không nhảy hết một lần.
Quan sát ở VN (định tính — TỰ KIỂM CHỨNG):
  - KQKD/ước tính vượt kỳ vọng thường còn dư địa tăng vài tuần sau đó (post-earnings drift).
  - Nâng hạng/khuyến nghị từ môi giới lớn có thể kéo momentum 1–3 tháng.
  - LƯU Ý PIT: dữ liệu cơ bản vnstock trễ ~90 ngày → tránh look-ahead khi dựng SUE.
Tín hiệu định lượng:
  SUE (standardized unexpected earnings) > 2σ → mua, nắm ~40–60 phiên (tự hiệu chỉnh).
  Top decile suất sinh lời 20 phiên → tiếp tục nắm ~20 phiên (chu kỳ VN ngắn).
```

**Phản ứng thái quá (overreaction) → hiệu ứng đảo chiều:**
```
Cơ chế: heuristic đại diện + thiên lệch sẵn có (availability)
  NĐT ngoại suy xu hướng gần đây quá đà, bỏ qua hồi quy về trung bình.
  Hoảng loạn/hưng phấn đẩy phản ứng vượt nền tảng cơ bản.
Quan sát ở VN (định tính — TỰ KIỂM CHỨNG):
  - Hồi kỹ thuật sau CHUỖI SÀN do call margin/giải chấp (rũ đòn bẩy xong dễ bật).
  - Mã giảm sâu cả năm (loser cực đoan) có xu hướng mean-reversion năm kế tiếp.
Tín hiệu định lượng:
  Bottom decile suất sinh lời ~250 phiên → mua, nắm dài.
  RSI(5) < 10–15 trên mã/chỉ số → tín hiệu hồi ngắn hạn (5–10 phiên).
Biên độ VN: HOSE ±7%, HNX ±10%, UPCoM ±15% → "chuỗi sàn" tạo đuôi nhiều phiên,
  khác A股 (±10%). Đừng bắt dao khi còn chuỗi sàn do giải chấp ([[regulatory-knowledge]]).
```

**Phân biệt then chốt:**
| Chiều | Phản ứng dưới mức (Momentum) | Phản ứng thái quá (Đảo chiều) |
|------|------------------|------------------|
| Thang thời gian | 1–12 tháng | <1 tuần hoặc >12 tháng |
| Loại thông tin | Sự kiện rõ ràng (KQKD/công bố) | Thông tin mơ hồ (tâm lý/xu hướng) |
| Cửa sổ tốt ở VN | 20–60 phiên | 5–10 phiên (ngắn) / ~1 năm (dài) |

### Checklist thiên lệch nhận thức

**Thiên lệch quyết định cá nhân:**
| Thiên lệch | Biểu hiện | Phát hiện định lượng | Chiến lược khử |
|------|------|----------|------------|
| Sợ thua lỗ (loss aversion) | "Gồng lỗ" mã thua, "chốt non" mã lãi | Thời gian nắm vị thế lỗ > lãi 2–3 lần | Đặt sẵn cắt lỗ, thực thi máy móc |
| Tự tin thái quá | Giao dịch quá nhiều, dồn vị thế | Vòng quay tháng >100%, 1 mã >30% NAV | Giới hạn số lệnh/tháng |
| Neo giá (anchoring) | Neo vào giá vào lệnh / đỉnh lịch sử | KL bất thường quanh giá vốn | Dùng định giá tương đối thay vì giá tuyệt đối |
| Thiên lệch xác nhận | Chỉ đọc tin ủng hộ quan điểm sẵn có | Thông tin 1 chiều, bỏ tin xấu | Bắt buộc đọc luận điểm ngược |
| Thiên lệch hiện tại (recency) | Quá coi trọng sự kiện gần | Lãi/lỗ gần ảnh hưởng quá mạnh cỡ vị thế | Kéo dài cửa sổ đánh giá (≥60 phiên) |
| Hiệu ứng đóng khung | Cùng tin, trình bày khác → quyết định khác | Khác biệt khi nhìn theo % vs lãi/lỗ tuyệt đối | Đánh giá nhất quán trong không gian % |

**Thiên lệch hành vi đám đông (đậm ở VN):**
| Thiên lệch | Biểu hiện | Đặc thù VN | Chỉ báo định lượng |
|------|------|---------|----------|
| Bầy đàn (herding) | Đua trần & bán tháo cùng lúc | Xoay vòng ngành cực nhanh (3–5 phiên) | Tương quan nội ngành > 0,8 |
| Thác thông tin | Bỏ thông tin riêng, theo tín hiệu công khai | Cổ phiếu dẫn dắt trần → cả ngành chạy theo | Suất sinh lời ngành phiên sau khi mã đầu ngành trần |
| Hiệu ứng chú ý | Mua mã đang được chú ý | "Hô hàng"/room/KOL đẩy mã (xem [[social-media-intelligence]]) | GTGD/vòng quay bất thường > 3× trung bình |

### Chu kỳ tâm lý NĐT

```
Sợ hãi → Thận trọng → Lạc quan → Hưng phấn → Cực hưng phấn → Phủ nhận → Hoảng loạn → Sợ hãi
   |         |          |          |             |            |           |
  Đáy      Hồi phục   Giữa sóng   Cận đỉnh      Đỉnh      Bán đầu     Cận đáy

→ Định lượng các pha bằng các trục TÂM LÝ ĐẶC THÙ VN (KHÔNG bê chỉ báo A股/Mỹ):
  khối ngoại mua/bán ròng · dư nợ margin · tài khoản mở mới (VSD) · GTGD & độ rộng ·
  số mã trần/sàn · basis VN30F. Khung điểm tâm lý tổng hợp → dùng [[sentiment-analysis]]
  (đừng dựng lại ở đây). VN KHÔNG có discount quỹ đóng/"All-A turnover" như A股.
```

## Khung phân tích

### 1. Tín hiệu hiệu ứng phân bổ (disposition effect)

**Nguyên lý:** NĐT có xu hướng bán mã lãi, giữ mã lỗ. Khi vị thế lãi đã xả gần hết → áp lực cung giảm; khi người kẹp lỗ quá sâu → cũng ngại cắt → cung cũng giảm.

```
Áp dụng VN:
  VN KHÔNG có dữ liệu phân phối chip chính thức như nền tảng A股 (东方财富) → XẤP XỈ qua VWAP.
  capital_gain_overhang (CGO) = (giá hiện tại − giá vốn bình quân) / giá vốn bình quân
    với giá vốn ≈ VWAP 60 phiên.
  CGO > 0,2  → lãi chưa thực hiện lớn → cảnh giác áp lực bán do disposition.
  CGO < −0,3 → người kẹp rất sâu → áp lực bán có thể GIẢM (cạn cung cắt lỗ) → ổn định đáy.
  Kết hợp KL: CGO cao + KL tăng = chốt lời/phân phối; CGO thấp + KL tăng = bán tháo/quá bán ngắn hạn.
```

### 2. Chỉ báo tâm lý tổng hợp

> Không dựng lại công thức ở đây — **dùng khung điểm tâm lý 0–100 của [[sentiment-analysis]]** (5 trục VN: khối ngoại, margin, tài khoản, thanh khoản/độ rộng, phái sinh). Vùng cực đoan (>80 / <20) là **chỉ báo NGƯỢC**. Skill này tập trung phần *diễn giải hành vi* phía sau con số.

### 3. Tối ưu momentum theo góc nhìn hành vi

Momentum truyền thống (xếp theo suất sinh lời 12 tháng) kém ổn định ở VN do xoay vòng nhanh. Góc nhìn hành vi gợi ý:

```
Tối ưu 1: Tách momentum TÂM LÝ khỏi momentum CƠ BẢN
  Momentum tâm lý = phần tăng giá gần đây KHÔNG có cơ bản đỡ → dễ đảo chiều ngắn hạn.
  Momentum cơ bản  = tăng giá đồng pha với nâng ước tính KQKD → bền hơn.
  Giao dịch: mua mã "momentum cơ bản mạnh + momentum tâm lý yếu".

Tối ưu 2: Momentum trọng số theo chú ý
  Mã được lẻ chú ý mạnh (đội lái/"hô hàng") đảo chiều nhanh hơn.
  Chỉ báo: GTGD/vòng quay bất thường > 3× trung bình → cắt thời gian nắm momentum 50%.
  Chéo [[social-media-intelligence]] để đo độ nóng MXH & cờ nghi làm giá.

Tối ưu 3: Kết hợp momentum cross-sectional & time-series
  Cross-sectional: sức mạnh tương đối (top 20% xếp hạng suất sinh lời).
  Time-series: xu hướng tuyệt đối (giá > MA60).
  Thỏa cả hai → tín hiệu mạnh; chỉ một → nửa vị thế.
```

### 4. Tín hiệu giao dịch ngược (contrarian) — bản VN

```
Điều kiện MUA khi cực sợ hãi (thỏa ≥3 mục):
  □ VN-Index RSI(5) < 15
  □ GTGD bình quân toàn thị trường cạn kiệt (rút mạnh so trung bình)
  □ Dư nợ margin co mạnh sau call/force-sell (đã rũ đòn bẩy)
  □ Số mã sàn >> số mã trần (sàn la liệt)
  □ Khối ngoại ngừng/đảo chiều bán ròng

Điều kiện BÁN/HẠ khi cực tham lam (thỏa ≥3 mục):
  □ VN-Index RSI(5) > 85
  □ GTGD bùng nổ kỷ lục (FOMO lẻ)
  □ Margin lập đỉnh lịch sử + chạm trần vốn chủ CTCK
  □ Mã trần hàng loạt (đầu cơ nóng)
  □ Tài khoản mở mới (VSD) bùng nổ

⚠️ VN CẤM BÁN KHỐNG cổ phiếu → vế "cực tham lam" là HẠ TỶ TRỌNG / phòng hộ beta bằng
   short VN30F, KHÔNG short cổ phiếu. Contrarian là long-only ở vế mua.
```

## Mẫu output

```
=== Chẩn đoán tâm lý thị trường ===
Ngày: 2026-06-19
Điểm tâm lý: 72/100 (thiên lạc quan)  [nguồn: khung sentiment-analysis]
Pha hiện tại: chuyển từ lạc quan sang hưng phấn

=== Tín hiệu thiên lệch hành vi ===
Phát hiện phản ứng thái quá: N mã tăng >15% trong 5 phiên → xác suất đảo chiều ngắn hạn cao
Hiệu ứng phân bổ: tỷ lệ xả mã lãi còn thấp → áp lực cung phía trên còn
Bầy đàn: tương quan nội ngành 0,85 → đua theo mã dẫn dắt, dễ phân hóa sắp tới

=== Khuyến nghị chiến lược ===
Momentum: rút thời gian nắm 60→30 phiên (độ chú ý thị trường cao)
Tín hiệu ngược: chưa kích hoạt (tâm lý chưa cực đoan)
Tỷ trọng: giữ ~70%, ưu tiên mã "momentum cơ bản mạnh + tâm lý yếu"; phòng hộ beta qua VN30F nếu cần

=== Checklist khử thiên lệch ===
□ Có đang tự tin thái quá vì vừa lãi? → soát mức tập trung danh mục
□ Có neo vào giá vào lệnh? → định giá lại bằng P/E, P/B hiện tại
□ Có bỏ qua tin xấu? → ép đọc báo cáo/luận điểm ngược
```

## Lưu ý

1. **Lẻ chi phối ở VN**: tín hiệu thiên lệch đậm hơn Mỹ, nhưng xoay vòng ngành nhanh hơn → cửa sổ momentum NGẮN hơn.
2. **Độ trễ chỉ báo tâm lý**: dư nợ margin theo quý (BCTC CTCK), tài khoản mở mới theo tháng (VSD) → là bức tranh trễ, không dùng cho intraday.
3. **Thay đổi cấu trúc**: làn sóng F0 2021–2022 → sập 2022 (margin + SCB–TPDN); khối ngoại bán ròng kỷ lục 2020–2023; tự doanh/quỹ + thuật toán tăng → hiệu lực tín hiệu hành vi truyền thống có thể yếu đi, re-test định kỳ.
4. **Nhân tố hành vi tương quan nhân tố truyền thống**: CGO/disposition tương quan ~0,3–0,5 với momentum → kiểm soát đa cộng tuyến (xem [[factor-research]], [[multi-factor]]).
5. **Rủi ro overfitting**: "câu chuyện hành vi" rất dễ giải thích hậu nghiệm → bắt buộc kiểm out-of-sample.
6. **Tâm lý cực đoan hiếm**: cực sợ/cực tham chỉ xuất hiện vài lần/năm → dung lượng chiến lược ngược hạn chế.
7. **Cấm bán khống**: mọi tín hiệu "bán/đảo chiều cực đoan" thực thi bằng hạ tỷ trọng / VN30F, không short cổ phiếu; T+2,5 (không bán mã vừa mua).

## Phụ thuộc

```bash
pip install pandas numpy scipy
```


## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)

1. **Không bịa/cook số liệu.** Mọi số tài chính phải có nguồn thật. Luôn **audit nhanh, cross-check tối thiểu 2 nguồn uy tín** (vd `cafef.vn`, `vietstock.vn`) — dùng **crawl4ai** cào số rồi đối chiếu; nếu nguồn lệch nhau thì nêu rõ, không chọn bừa.
2. **Nếu DataPro VÀ vnstock đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
