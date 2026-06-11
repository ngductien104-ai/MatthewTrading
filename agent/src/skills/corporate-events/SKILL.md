---
name: corporate-events
description: "Phân tích sự kiện doanh nghiệp VN theo hướng event-driven — chào mua công khai/M&A, thoái vốn Nhà nước (SCIC), giao dịch nội bộ & cổ đông lớn (rủi ro 'bán chui'), phát hành riêng lẻ/quyền mua/ESOP, mua cổ phiếu quỹ, diện cảnh báo–kiểm soát–hủy niêm yết, vào/ra rổ chỉ số. Nguồn: vnstock (events/insider/shareholders) + DataPro (giá/KL/khối ngoại)."
category: flow
---

# Phân tích sự kiện doanh nghiệp (Việt Nam)

## Mục đích

Khai thác alpha từ sự kiện cấp doanh nghiệp (M&A, thoái vốn, giao dịch nội bộ, phát hành thêm, sự kiện niêm yết). Logic cốt lõi: công bố sự kiện mang **thông tin tăng thêm**, thị trường tiêu hóa cần thời gian → tồn tại lợi suất bất thường có hệ thống quanh sự kiện. Tại VN, biên độ giá, thanh khoản mỏng và **rò rỉ thông tin trước công bố** khiến cửa sổ giao dịch khác hẳn thị trường phát triển.

Khung pháp lý nền: **Luật Chứng khoán 2019**, **NĐ 155/2020/NĐ-CP**, **Thông tư 96/2020** (công bố thông tin), **Thông tư 120/2020** (giao dịch).

## ⚠️ Đặc thù sự kiện DN Việt Nam (đọc TRƯỚC)

1. **Rò rỉ thông tin trước công bố là phổ biến**: giá thường chạy TRƯỚC tin chính thức (nội gián, "đội lái"). Khối lượng đột biến + giá tăng/giảm bất thường trước ngày công bố là dấu hiệu kinh điển. Vào lệnh theo tin đã công bố thường là người mua cuối.
2. **Biên độ giá chặn phản ứng**: HOSE ±7%, HNX ±10%, UPCOM ±15%. Tin tốt/xấu lớn → chuỗi **trần/sàn nhiều phiên liên tiếp**, không khớp được lệnh ("trắng bên mua/bán") → không thể vào/thoát đúng giá. Đây là khác biệt lớn nhất so với A股/Mỹ.
3. **Thoái vốn Nhà nước (SCIC/bộ ngành) là nguồn alpha sự kiện lớn & đặc trưng nhất VN** — không tồn tại ở các thị trường khác cùng quy mô.
4. **"Bán chui" / không công bố giao dịch**: người nội bộ & cổ đông lớn BẮT BUỘC đăng ký trước; vi phạm bị xử phạt/hủy giao dịch (vụ Trịnh Văn Quyết – FLC 1/2022 là điển hình). Giao dịch nội bộ không công bố = cờ đỏ quản trị.
5. **Mua cổ phiếu quỹ ≈ biến mất**: theo Luật CK 2019, mua lại cổ phiếu quỹ **phải giảm vốn điều lệ** → DN gần như không còn dùng treasury buyback để đỡ giá như trước 2021. Đừng kỳ vọng "buyback đỡ giá" kiểu cũ.
6. **ESOP pha loãng mạnh**: phát hành ESOP giá bằng/gần **mệnh giá 10.000đ** (chiết khấu sâu so thị giá) rất phổ biến (MWG, FPT...) → pha loãng EPS, chuyển giá trị sang nội bộ; lock-up thường 1–4 năm.

## Các loại sự kiện & cách giao dịch

### 1. Chào mua công khai / M&A / thâu tóm

```
Ngưỡng CHÀO MUA CÔNG KHAI bắt buộc (NĐ 155/2020): khi mua để đạt/vượt
  25% rồi 35% / 45% / 55% / 65% / 75% số CP có quyền biểu quyết.

Chênh lệch chào mua (merger arb spread):
  spread = (giá chào mua − giá thị trường) / giá thị trường
  LN năm hóa = spread / thời gian dự kiến hoàn tất (năm)

Đánh giá xác suất thành công:
  - Đã có chấp thuận UBCKNN / tỷ lệ chấp thuận ĐHĐCĐ → cao
  - Đối tác chiến lược/ngoại có cam kết → cao
  - Vướng room ngoại / cần nới room → rủi ro
```
Thực chiến VN: M&A thường đi qua **phát hành riêng lẻ cho đối tác chiến lược** hơn là chào mua thị trường (Sabeco–ThaiBev 2017, các thương vụ ngân hàng–đối tác Nhật/Hàn). "Thâu tóm ngầm" gom dưới ngưỡng công bố rồi mới lộ diện cũng hay xảy ra → theo dõi biến động cơ cấu cổ đông lớn.

### 2. Thoái vốn Nhà nước (SCIC / bộ ngành) — ⭐ alpha sự kiện đặc trưng VN

```
Cơ chế: SCIC/bộ chủ quản bán phần vốn Nhà nước qua ĐẤU GIÁ công khai
        (hoặc dựng sổ/bán thỏa thuận) tại mức GIÁ KHỞI ĐIỂM công bố trước.

Mẫu hình giá điển hình:
  Có tin vào danh sách thoái vốn → gom dần (kỳ vọng đấu giá cao)
  Công bố giá khởi điểm > thị giá → giá thị trường được kéo lên gần giá khởi điểm
  Đấu giá thành công giá cao (đối tác chiến lược trả premium kiểm soát) → tin ra là đỉnh ngắn hạn

Điểm soi:
  - Tỷ lệ Nhà nước còn lại & lộ trình (thoái hết hay từng phần)
  - Có nhà đầu tư chiến lược tranh mua quyền kiểm soát không (premium lớn)
  - Room ngoại còn không (chiến lược ngoại cần room)
```
Tham chiếu lịch sử: thoái vốn **VNM (SCIC, 2017)**, **Sabeco (2017)** tạo sóng lớn; nhóm DN Nhà nước trong diện thoái vốn (đầu ngành tiện ích/hạ tầng) là nơi săn sự kiện.

### 3. Giao dịch cổ đông nội bộ & cổ đông lớn

```
Nghĩa vụ công bố:
  - Người nội bộ (HĐQT, BKS, BĐH, kế toán trưởng) & người liên quan: ĐĂNG KÝ
    giao dịch & công bố TRƯỚC tối thiểu 3 ngày làm việc; báo cáo kết quả sau.
  - Cổ đông lớn (≥5%): công bố khi tỷ lệ sở hữu thay đổi qua các mốc ≥1%.

Tín hiệu MUA VÀO của nội bộ (thường tích cực):
  Mạnh: Chủ tịch/CEO/cổ đông kiểm soát đăng ký mua lượng lớn bằng tiền thật
  Yếu:  một thành viên đăng ký mua nhỏ (đôi khi mang tính "trấn an")

Tín hiệu BÁN RA (thường tiêu cực, cần lọc):
  - Lọc BỎ: bán do GIẢI CHẤP margin/cầm cố (bị động, không phải quan điểm)
  - Giữ LẠI: bán chủ động khi giá cao, hoặc bán ngay sau khi vừa "mua trấn an"

Cờ đỏ quản trị:
  - "Bán chui" (giao dịch không đăng ký/không công bố) → rủi ro quản trị nghiêm trọng
  - Đăng ký mua nhưng "không mua được do điều kiện thị trường" lặp lại → làm giá kỳ vọng
  - Lãnh đạo bán mạnh trong khi DN phát tín hiệu lạc quan → mâu thuẫn lợi ích
```

### 4. Phát hành thêm: riêng lẻ / quyền mua / ESOP / cổ phiếu thưởng

```
Phát hành RIÊNG LẺ (cho đối tác chiến lược):
  Giá phát hành vs thị giá:
    Chiết khấu sâu cho chiến lược ngoại/uy tín → thường tích cực (xác nhận giá trị)
    Chiết khấu sâu cho bên liên quan mờ ám → cảnh giác (chuyển giá trị/pha loãng)
  Lock-up tối thiểu 1 năm (chiến lược 3 năm) → giảm áp lực bán ngay.

Phát hành QUYỀN MUA (rights issue):
  Giá quyền mua < thị giá → giá điều chỉnh kỹ thuật ngày GDKHQ (giống chia tách).
  Pha loãng: tỷ lệ thực hiện càng cao, chiết khấu càng sâu → pha loãng càng lớn.
  Soi mục đích dùng vốn: thâu tóm/mở rộng dự án tốt = +; "bổ sung vốn lưu động"
  chung chung / trả nợ = trung tính–tiêu cực.

ESOP:
  Giá ~ mệnh giá 10.000đ << thị giá → chiết khấu cực sâu, PHA LOÃNG rõ.
  Đánh giá: % ESOP/tổng CP, điều kiện ràng buộc (KPI lợi nhuận), lock-up.
  ESOP lặp lại hằng năm tỷ lệ lớn không gắn KPI = chuyển giá trị sang nội bộ.

Cổ phiếu thưởng / cổ tức cổ phiếu:
  KHÔNG phải thu nhập — chỉ chia nhỏ; giá điều chỉnh giảm ngày GDKHQ.
  (Chi tiết ở skill dividend-analysis.)
```
Công thức pha loãng nhanh: `EPS_sau ≈ EPS_trước × (CP cũ) / (CP cũ + CP phát hành thêm)` (chưa tính lợi ích từ vốn huy động).

### 5. Mua cổ phiếu quỹ (lưu ý quy định mới)

Theo Luật CK 2019, mua lại cổ phiếu quỹ **phải giảm vốn điều lệ** (trừ vài ngoại lệ: mua lại CP lẻ, CP của người lao động nghỉ việc theo quy chế ESOP, sửa lỗi giao dịch). Hệ quả: công cụ "mua cổ phiếu quỹ đỡ giá" gần như không còn → đừng dựng kỳ vọng buyback như giai đoạn trước 2021. Nếu DN vẫn công bố mua lại để giảm vốn, đọc kỹ mục đích (cô đặc EPS thật vs tín hiệu suông).

### 6. Diện cảnh báo / kiểm soát / hạn chế / hủy niêm yết

```
Thang cảnh báo của HOSE/HNX (mức độ tăng dần):
  CẢNH BÁO        → chậm nộp BCTC, LN sau thuế/LNST chưa phân phối âm...
  KIỂM SOÁT       → vi phạm nặng hơn, lỗ 2 năm liên tiếp, kiểm toán ngoại trừ
  HẠN CHẾ GIAO DỊCH → chỉ giao dịch phiên chiều
  ĐÌNH CHỈ GIAO DỊCH
  HỦY NIÊM YẾT BẮT BUỘC → lỗ 3 năm liên tiếp / lỗ lũy kế vượt vốn điều lệ /
                          kiểm toán TỪ CHỐI hoặc ý kiến trái ngược / vi phạm CBTT nghiêm trọng

Chiến lược NÉ (khuyến nghị):
  - Loại khỏi danh mục mọi mã đang ở diện kiểm soát/hạn chế trở lên
  - Sàng sớm mã rủi ro: lỗ quý gần nhất + doanh thu sụt mạnh + kiểm toán ngoại trừ
  - Cổ phiếu hủy niêm yết HOSE/HNX thường rớt xuống UPCOM, thanh khoản cạn

Đầu cơ "thoát hiểm" (rủi ro rất cao, chỉ nghiên cứu):
  Mã có khả năng đưa ra khỏi diện cảnh báo (đã có lãi trở lại + tái cơ cấu thực chất)
  → vị thế nhỏ (<5%), cắt lỗ kỷ luật. Tránh "bắt dao rơi" họ FLC/HAG/HNG/POM khi chưa rõ.
```

### 7. Vào / ra rổ chỉ số & ETF

Cổ phiếu được **thêm vào VN30 / VNDIAMOND / VNFINLEAD** → các ETF bám buộc phải mua (và ngược lại khi bị loại) → cơ hội sự kiện quanh ngày hiệu lực. Soi danh sách dự kiến thêm/loại trước kỳ review (VN30 review tháng 1 & 7). Chi tiết cơ chế ETF & dòng tiền tạo lập ở skill `etf-analysis`.

## Cửa sổ thời gian sự kiện (đặc thù VN)

```
T−N (trước công bố):
  Theo dõi KL & giá bất thường (dấu hiệu rò rỉ). Vào trước tin = rủi ro nội gián/làm giá.
T (ngày công bố):
  Tin lớn → trần/sàn, có thể "trắng bảng" → KHÔNG khớp được; đừng đuổi giá trần.
T+1..T+vài phiên:
  Sóng tin có thể kéo dài qua chuỗi trần/sàn rồi mới khớp lệnh được — chờ phiên có
  thanh khoản thật để vào/thoát.
T+N (dài hạn):
  Lock-up phát hành riêng lẻ/ESOP đáo hạn → áp lực bán; đánh dấu lịch mở khóa.
```

## Nguồn dữ liệu (VN)

| Việc cần | Nguồn |
|------|------|
| Lịch & nội dung sự kiện DN (ĐHĐCĐ, phát hành, chia thưởng, GDKHQ...) | **vnstock** `Company.events()` (lọc theo `category`/`event_title_vi`) |
| Giao dịch nội bộ & người liên quan | **vnstock** `Company.insider_deals()`; danh sách lãnh đạo `Company.officers()` |
| Cơ cấu cổ đông lớn & thay đổi sở hữu | **vnstock** `Company.shareholders()` |
| Lịch sử tăng vốn / phát hành (pha loãng) | **vnstock** `Company.capital_history()`; `issue_share` từ `Company.overview()` |
| Giá / khối lượng / **khối ngoại mua-bán ròng** (rò rỉ, lực mua) | **DataPro** (`source="datapro"`, mã `.VN`; trường khối ngoại) |
| Diện cảnh báo/kiểm soát/hủy niêm yết, thoái vốn, chào mua | Công bố HOSE/HNX/UBCKNN, SCIC (event-based; vnstock `events` không phủ hết → đọc tin chính thức) |

Khi không có dữ liệu trực tiếp: nêu hạn chế, đưa khung phân tích, KHÔNG bịa số liệu sự kiện.

## Mẫu output

```markdown
=== Sự kiện === (minh họa)
Mã: VNM.VN — SCIC công bố tiếp tục thoái vốn
Loại: thoái vốn Nhà nước (đấu giá)
Quy mô: ...% vốn   Giá khởi điểm: ... đ (vs thị giá ... đ)

=== Đánh giá tín hiệu ===
Độ mạnh: cao (có chiến lược ngoại tranh quyền kiểm soát)
Mẫu hình kỳ vọng: kéo về giá khởi điểm → tin đấu giá thành công có thể là đỉnh ngắn hạn
Cờ rủi ro: room ngoại còn lại / chuỗi trần chặn điểm vào

=== Hành động ===
Cửa sổ: trước ngày chốt đấu giá; thoát quanh ngày kết quả
Tỷ trọng: ≤ 5–8% (trần một sự kiện)
Cắt lỗ: theo kỷ luật dưới giá tham chiếu công bố

Lưu ý: Đây là nghiên cứu, không phải khuyến nghị giao dịch.
```

## Lưu ý quan trọng

1. **Rò rỉ & nội gián**: giá chạy trước tin là chuẩn mực ở VN — bám tin đã công bố dễ thành người mua cuối; trọng số cao cho KL/giá bất thường TRƯỚC sự kiện.
2. **Trần/sàn chặn lệnh**: backtest/thực chiến phải mô hình hóa chuỗi trần-sàn không khớp được, nếu không sẽ ảo tưởng vào/thoát đúng giá.
3. **Quản trị doanh nghiệp**: "bán chui", ESOP pha loãng vô tội vạ, phát hành riêng lẻ cho bên liên quan giá bèo → trừ điểm nặng; nhóm DN có lịch sử này (họ đầu cơ) rủi ro sự kiện đặc biệt cao.
4. **Tỷ trọng & kỷ luật**: chiến lược event-driven đơn lẻ ≤ 10% danh mục; sự kiện đổ vỡ (M&A bị bác, đấu giá ế) có thể gây chuỗi sàn 20%+.
5. **Né diện kiểm soát/hủy niêm yết**: ưu tiên phòng thủ hơn đầu cơ "thoát hiểm"; cổ phiếu hủy niêm yết rớt UPCOM thanh khoản cạn, khó thoát.

## Phụ thuộc

```bash
pip install pandas numpy vnstock
```
