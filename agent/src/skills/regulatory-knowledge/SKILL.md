---
name: regulatory-knowledge
description: "Quy tắc giao dịch & pháp lý TTCK Việt Nam cho quant: biên độ HOSE/HNX/UPCOM, chu kỳ T+2, phiên ATO/ATC, cấm bán khống, ký quỹ (margin) & call/force-sell, room ngoại, phái sinh VN30F & chứng quyền (CW), thuế-phí. Kèm bảng so sánh nhanh đa thị trường (A股/HK/US/crypto) cho chiến lược xuyên thị trường."
category: tool
---

# Kiến thức quy tắc & pháp lý (Việt Nam)

## Mục đích

Quant phải hiểu đúng luật chơi của thị trường, nếu không backtest sẽ sai lệch (vd không tính biên độ trần/sàn, giả định bán khống được trong khi VN cấm) và thực chiến vi phạm/sai chi phí. Skill này lấy **TTCK Việt Nam** làm trung tâm; phần cuối có bảng so sánh đa thị trường cho chiến lược xuyên biên giới.

Khung pháp lý: **Luật Chứng khoán 2019**, **NĐ 155/2020/NĐ-CP**, các quy chế giao dịch của **HOSE/HNX**, quy định **UBCKNN**.

## Quy tắc giao dịch TTCK Việt Nam

### Biên độ giá (trần/sàn)

| Sàn | Biên độ thường | Ngày giao dịch đầu tiên / sau tạm ngừng dài |
|------|------|------|
| **HOSE** | ±7% | ±20% |
| **HNX** | ±10% | ±30% |
| **UPCOM** | ±15% | ±40% |

```
Ảnh hưởng backtest/thực chiến:
  Tin lớn → giá kịch TRẦN/SÀN nhiều phiên, "trắng bên mua/bán" → KHÔNG khớp được.
    → lệnh mua khi trần / lệnh bán (cắt lỗ) khi sàn có thể không thực hiện được.
  Mô hình hóa: nếu |return ngày| chạm biên → đánh dấu không khớp, đẩy sang phiên sau.
  Đây là nguồn sai lệch lớn nhất với chiến lược momentum/sự kiện ở VN.
```

### Chu kỳ thanh toán T+2 & KHÔNG có T+0

```
Mua ngày T → cổ phiếu/tiền về tài khoản chiều T+2 → bán được từ T+2.
  (VN rút ngắn từ T+3 về T+2 năm 2022; cổ phiếu về ~13h ngày T+2.)
KHÔNG có giao dịch trong ngày (T+0) với cổ phiếu cơ sở.
Sai lầm backtest kinh điển: tín hiệu ngày T, mua T rồi BÁN NGAY trong T → ảo lãi.
  Đúng: tín hiệu T → khớp mua ~mở cửa T+1 → sớm nhất bán được T+3 (sau khi cổ phiếu T+1 về).

Ngoại lệ T+0: chỉ phái sinh (HĐTL VN30) đóng/mở trong ngày được; cổ phiếu thì không.
```

### Phiên giao dịch & loại lệnh

```
HOSE:  ATO 9:00–9:15 | Khớp liên tục 9:15–11:30 | nghỉ trưa |
       13:00–14:30 | ATC 14:30–14:45 | Khớp lệnh sau giờ & thỏa thuận 14:45–15:00
HNX:   Khớp liên tục 9:00–11:30, 13:00–14:30 | ATC 14:30–14:45 | PLO 14:45–15:00
UPCOM: Khớp liên tục 9:00–11:30, 13:00–15:00 (KHÔNG có ATO/ATC)

Loại lệnh:
  LO  (giới hạn) — phổ biến nhất
  ATO / ATC — khớp tại giá mở/đóng cửa (không ghi giá; ưu tiên khớp; không khớp thì hủy)
  MP / MTL / MOK / MAK — lệnh thị trường (HOSE: MP; HNX: MTL/MOK/MAK)
  PLO — lệnh khớp giá đóng cửa sau giờ (HNX)

Lưu ý backtest:
  - Backtest ngày (daily) mặc định khớp tại GIÁ MỞ CỬA T+1.
  - ATC quyết định giá đóng → chiến lược dùng giá đóng cần lưu ý lực kéo/đạp phiên ATC.
```

### Bán khống & ký quỹ (margin)

```
BÁN KHỐNG: KHÔNG được phép cho NĐT (chưa có cơ chế vay & bán khống chính thức).
  → Mọi tín hiệu "short" cổ phiếu KHÔNG thực thi được. Chỉ phòng hộ qua phái sinh VN30F
    (short hợp đồng tương lai chỉ số) hoặc CW put (hạn chế).

KÝ QUỸ (margin):
  - Chỉ áp dụng cổ phiếu ĐỦ ĐIỀU KIỆN (HOSE/HNX/UBCKNN công bố danh sách; loại trừ mã
    mới niêm yết <6 tháng, diện cảnh báo/kiểm soát, biến động bất thường...).
  - Tỷ lệ ký quỹ ban đầu tối thiểu 50% → đòn bẩy tối đa ~2x (1:1).
  - Call margin / force-sell: khi tỷ lệ tài sản đảm bảo giảm dưới ngưỡng CTCK đặt
    (thường call ~ mức ký quỹ duy trì, force-sell khi thủng ngưỡng) → CTCK bán giải chấp.
  - Lãi margin ~ 9–14%/năm (tùy CTCK) → trừ vào lợi nhuận chiến lược dùng đòn bẩy.

Ảnh hưởng: "bán giải chấp margin" hàng loạt khi thị trường giảm mạnh tạo VÒNG XOÁY
  GIẢM (force-sell → giá sàn → call thêm) — rủi ro hệ thống đặc thù VN; nhóm cổ phiếu
  bị dùng làm tài sản cầm cố/đòn bẩy cao dễ bị "đạp sàn" liên phiên.
```

### Room ngoại (giới hạn sở hữu nước ngoài)

```
Trần sở hữu nước ngoài mặc định: ~49% (phần lớn ngành);
  NGÂN HÀNG: 30%; ngành nghề kinh doanh có điều kiện: tỷ lệ riêng;
  một số DN tự nới tới 100% (thường phi tài chính, đã bỏ ngành nghề điều kiện).
Hết room → NĐT ngoại phải mua qua THỎA THUẬN giá premium, hoặc gián tiếp qua ETF VNDIAMOND.
Tín hiệu: cổ phiếu kín room + cầu ngoại mạnh → giá thỏa thuận ngoại cao hơn sàn;
  VNDIAMOND/FUEVFVND thường phụ trội (xem skill etf-analysis).
```

### Phái sinh & chứng quyền

```
HĐTL chỉ số VN30 (VN30F1M/2M/quý): thanh toán TIỀN MẶT, ký quỹ, T+0 (đóng trong ngày),
  giao dịch trên HNX. Dùng để phòng hộ beta / đặt cược chỉ số / thay thế "short".
  Theo dõi BASIS (chênh HĐTL − VN30 spot) làm chỉ báo tâm lý.
HĐTL Trái phiếu Chính phủ: thanh khoản thấp, chủ yếu tổ chức.
Chứng quyền có bảo đảm (CW): CTCK phát hành, niêm yết HOSE, dựa trên cổ phiếu cơ sở;
  đòn bẩy cao, có giá trị thời gian/biến động → KHÔNG phải quyền chọn chuẩn, coi chừng
  time decay và việc nhà phát hành tạo lập.
```

### Thuế & phí giao dịch

```
Thuế TNCN bán chứng khoán: 0,1% trên GIÁ TRỊ BÁN (đánh dù lãi hay LỖ — không phải thuế lãi vốn).
Cổ tức TIỀN MẶT: 5% (khấu trừ tại nguồn). Cổ tức cổ phiếu: 5% khi bán.
Phí giao dịch CTCK: ~0,1%–0,35%/lượt (cạnh tranh, nhiều CTCK ~0,15%).
Phí lưu ký, phí chuyển nhượng: nhỏ.

Chi phí vòng (mua+bán) thực tế ≈ 2× phí CTCK + 0,1% thuế bán ≈ ~0,3–0,5%.
  → Quay vòng 1 lần/tháng ≈ ~4–6%/năm chi phí; chiến lược tần suất cao bị bào mạnh.
```

### Lịch nghỉ & gián đoạn

Nghỉ **Tết Nguyên đán** dài (~1 tuần+), Giỗ Tổ (10/3 ÂL), 30/4–1/5, Quốc khánh 2/9 → tín hiệu bị ngắt quãng; thị trường phái sinh/quốc tế vẫn chạy → xử lý khoảng trống dữ liệu khi chạy chiến lược xuyên thị trường.

## Ma trận ràng buộc cho backtest (VN làm chuẩn)

| Quy tắc | **Việt Nam** | A股 | HK | US | Crypto |
|------|------|------|------|------|------|
| Biên độ | ±7/10/15% | ±10/20/30% | Không | LULD ngắt | Không |
| Chu kỳ / T+0 | T+2, KHÔNG T+0 | T+1 | T+0 | T+0 (margin) | T+0 24/7 |
| Bán khống | **Cấm** (chỉ VN30F) | Khó/đắt | Dễ | Dễ | Hợp đồng |
| Đòn bẩy | Margin ~2x (mã đủ ĐK) | Margin | Margin | Margin/PDT | Tới 100x+ |
| Lô | 100 cp (HOSE) | 100 cp | 1 lô | 1 cp | nhỏ |
| Giờ/ngày | ~4,5h | ~4h | ~5,5h | ~6,5h | 24/7 |
| Chi phí vòng | ~0,3–0,5% (gồm thuế bán 0,1%) | ~0,16% | ~0,26% | ~$0 | ~0,04–0,1% |

> Chiến lược xuyên thị trường: đối chiếu lịch nghỉ (Tết VN ≠ nghỉ US), rủi ro tỷ giá (VND/USD), và việc tín hiệu "short" KHÔNG thực thi được ở chân VN — thay bằng VN30F.

## Thuế khi NĐT VN đầu tư ra nước ngoài (tham khảo)

- Cổ tức cổ phiếu Mỹ: khấu trừ tại nguồn 30% nếu không có/không nộp W-8BEN (VN chưa có hiệp định thuế song phương ưu đãi rộng với Mỹ như nhiều nước) → kiểm tra điều kiện thực tế của nền tảng.
- Lãi vốn nước ngoài & quy đổi VND: tuân thủ quy định quản lý ngoại hối; nền tảng đầu tư quốc tế tại VN còn hạn chế pháp lý → nêu rõ cảnh báo tuân thủ khi tư vấn.

## Lưu ý quan trọng

1. **Quy tắc thay đổi theo thời điểm**: T+3→T+2 (2022), quy định margin/danh sách ký quỹ cập nhật định kỳ; backtest theo đúng quy tắc của giai đoạn lịch sử.
2. **Trần/sàn chặn lệnh** là sai lệch backtest lớn nhất ở VN — chiến lược quay vòng cao/đu trần phải mô hình hóa chuỗi không khớp.
3. **Vòng xoáy giải chấp margin**: rủi ro hệ thống khi giảm mạnh; cổ phiếu đòn bẩy cao dễ "đạp sàn" liên phiên — đưa vào quản trị rủi ro.
4. **Không bán khống**: mọi tín hiệu short cổ phiếu phải chuyển sang VN30F hoặc bỏ; đừng để backtest "ăn gian" phần short.
5. **Phiên đặc biệt**: ATO/ATC và phiên sau giờ khác khớp lệnh liên tục — chiến lược theo giá mở/đóng cần phân biệt.
6. **Chi phí thuế trên giá trị bán**: 0,1% đánh cả khi lỗ → tần suất cao bị bào; tính vào net return.

## Phụ thuộc

```bash
pip install pandas numpy
```
