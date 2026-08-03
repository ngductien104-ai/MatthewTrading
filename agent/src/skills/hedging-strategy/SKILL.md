---
name: hedging-strategy
description: "Thiết kế chiến lược phòng hộ cho danh mục cổ phiếu VN — phòng hộ beta bằng VN30F, giảm trạng thái, xoay nhóm phòng thủ, phòng hộ chéo (tiền gửi/vàng/USD) và phòng hộ tỷ giá. Tính tỷ lệ hedge, chi phí thực và giới hạn công cụ tại TTCK VN."
category: asset-class
---
# Thiết kế chiến lược phòng hộ (TTCK Việt Nam)

## Tổng quan

Thiết kế phương án phòng hộ có hệ thống cho danh mục đang nắm. Nguyên tắc lõi: **phòng hộ không xoá rủi ro, mà đổi khoản lỗ chưa biết lấy chi phí đã biết.**

**Thực tế công cụ tại VN — đọc kỹ trước khi thiết kế:**

| Công cụ | Có tại VN? | Ghi chú |
|------|------|------|
| Hợp đồng tương lai chỉ số VN30 (VN30F) | ✅ | **Công cụ phòng hộ tuyến tính duy nhất có thanh khoản thật** |
| Hợp đồng tương lai TPCP (5Y/10Y) | ⚠️ Có niêm yết | Thanh khoản gần bằng 0 — coi như không dùng được |
| Quyền chọn cổ phiếu / chỉ số niêm yết | ❌ Không có | Mọi chiến lược Protective Put / Collar / Put Spread **không áp dụng được tại VN** |
| Chứng quyền có bảo đảm (CW) | ⚠️ Chỉ chiều MUA | Chỉ có call warrant, **không có put warrant** ⇒ không dùng để phòng hộ giảm giá |
| Bán khống cổ phiếu cơ sở | ❌ Chưa triển khai | Không thể tạo vị thế short đơn lẻ |
| Chỉ số biến động kiểu VIX | ❌ Không có | Không có sản phẩm giao dịch được trên vol |
| Hợp đồng kỳ hạn ngoại tệ (onshore) | ✅ Qua NHTM | Có hạn mức và điều kiện chứng từ; NDF offshore không dành cho quỹ nội |
| Vàng miếng / nhẫn | ✅ | Không có ETF vàng niêm yết tại VN — phải nắm vật chất |

Hệ quả thiết kế: ở VN, "phòng hộ" thực chất là **bốn lựa chọn** — (1) short VN30F, (2) giảm trạng thái sang tiền, (3) xoay sang nhóm beta thấp, (4) phòng hộ chéo bằng tiền gửi/vàng/USD. Đừng đề xuất Collar hay Put Spread trên cổ phiếu VN; nếu chép khung nước ngoài vào là sai ngay từ gốc.

**Lý do phòng hộ tại VN mạnh hơn ở thị trường khác:** biên độ dao động (HOSE ±7%, HNX ±10%, UPCoM ±15%) khiến khi thị trường sập, cổ phiếu **dư bán sàn trắng bên mua** — bạn *không bán được*. Chu kỳ thanh toán T+2 cũng chặn việc thoát trong phiên. VN30F giao dịch T+0, đóng/mở vị thế trong ngày, là lối thoát duy nhất khi cơ sở bị khoá sàn. Đây là lập luận cốt lõi cho việc duy trì tài khoản phái sinh dù ít dùng.

## Khái niệm cốt lõi

### 1. Phòng hộ beta bằng VN30F

**Nguyên lý:** dùng hợp đồng tương lai chỉ số để triệt tiêu rủi ro hệ thống (beta), giữ lại alpha cổ phiếu riêng lẻ.

**Thông số hợp đồng (kiểm lại quy chế HNX/VSD hiện hành trước khi tính tiền thật):**
- Tài sản cơ sở: chỉ số VN30
- Hệ số nhân: **100.000 VND / điểm chỉ số**
- Giá trị 1 hợp đồng = điểm chỉ số × 100.000 VND
- Các mã: VN30F1M (tháng hiện tại), VN30F2M, VN30F1Q, VN30F2Q — **chỉ VN30F1M có thanh khoản đủ để phòng hộ quy mô tổ chức**
- Thanh toán: bằng tiền, theo giá đóng cửa chỉ số ngày đáo hạn (thứ Năm thứ ba của tháng)
- Ký quỹ ban đầu: theo tỷ lệ VSD công bố (thường ~17-20%), CTCK có thể yêu cầu cao hơn

**Tính số hợp đồng:**

```python
# Tỷ lệ phòng hộ phương sai tối thiểu
hedge_ratio = beta_portfolio * (portfolio_value / futures_contract_value)

# Ví dụ: danh mục 20 tỷ VND, beta = 1,15 so với VN30
# VN30 = 1.400 điểm → giá trị 1 HĐ = 1.400 × 100.000 = 140.000.000 VND
# Số HĐ cần short = 1,15 × (20.000.000.000 / 140.000.000) = 164 hợp đồng
# Ký quỹ cần (18%) ≈ 164 × 140.000.000 × 0,18 ≈ 4,13 tỷ VND

# Ước lượng beta — CHUẨN TỔ CHỨC
# Mặc định: 2 năm dữ liệu, khung TUẦN (kiểu Bloomberg), hồi quy với VN30 (không phải VN-Index)
# Khung ngày ở VN nhiễu nặng vì biên độ và thanh khoản mỏng ở midcap
import numpy as np
beta = np.cov(weekly_portfolio_returns, weekly_vn30_returns)[0][1] / np.var(weekly_vn30_returns)
```

**Sai số nền (basis) — vấn đề lớn tại VN:**
- VN30F thường giao dịch **chiết khấu (basis âm)** so với chỉ số cơ sở trong xu hướng giảm, và nới rộng đúng lúc thị trường hoảng loạn (đã có phiên basis âm hơn 30 điểm)
- Short futures khi basis đang chiết khấu sâu = **trả trước phần lớn khoản lợi phòng hộ**. Nói cách khác: phòng hộ vào lúc thị trường đã hoảng thì đắt gấp nhiều lần
- Basis hội tụ về 0 khi đáo hạn ⇒ nếu short lúc basis dương (premium), phần hội tụ là lợi nhuận cộng thêm
- **Luôn báo cáo basis tại thời điểm vào lệnh** như một hạng mục chi phí riêng, không gộp vào phí

**Sai số cơ cấu (basis risk) khi danh mục lệch VN30:**
- VN30F chỉ phòng hộ được phần beta so với VN30. Danh mục thiên midcap/smallcap có R² thấp với VN30 (thường 0,5-0,7) ⇒ phòng hộ để lại rủi ro dư đáng kể
- Bắt buộc báo R² của hồi quy beta. R² < 0,6 thì nói thẳng: "VN30F phòng hộ không hiệu quả cho danh mục này, nên giảm trạng thái thay vì hedge"

### 2. Giảm trạng thái (công cụ phòng hộ phổ biến nhất tại VN)

Không có quyền chọn thì việc **hạ tỷ trọng cổ phiếu** chính là phương án phòng hộ chuẩn mực nhất, và thường rẻ hơn short futures.

| Mức hạ tỷ trọng | Tương đương phòng hộ | Chi phí | Khi nào dùng |
|------|------|------|------|
| Bán 20-30% danh mục | Giảm beta hiệu dụng 20-30% | Phí GD + thuế 0,1% giá bán + chi phí cơ hội | Rủi ro trung hạn, chưa rõ hướng |
| Bán 50% | Nửa trạng thái | Như trên | Vi phạm ngưỡng theo dõi vĩ mô (tỷ giá chạm biên, ERP âm) |
| Về tiền mặt/tiền gửi 100% | Phòng hộ tuyệt đối | Mất toàn bộ upside; lãi tiền gửi bù một phần | Chế độ đình lạm hoặc sự kiện đuôi đã kích hoạt |

**Điểm khác biệt của VN:** lãi suất tiền gửi 12 tháng ~6-8% là mức bù rất cao cho việc đứng ngoài — chi phí cơ hội của tiền mặt tại VN **thấp hơn nhiều** so với thị trường lãi suất 0%. Luôn tính chi phí phòng hộ *ròng sau lãi tiền gửi*.

### 3. Phòng hộ theo cơ cấu (xoay nhóm beta thấp)

Khi không thể/không muốn dùng phái sinh, hạ beta bằng cách đổi cơ cấu:

| Nhóm | Beta điển hình vs VN30 | Vai trò |
|------|------|------|
| Chứng khoán (SSI, VCI, HCM, VND) | 1,3-1,7 | Beta cao nhất — bán đầu tiên khi phòng thủ |
| Bất động sản dân cư | 1,2-1,5 | Nhạy lãi suất và tín dụng |
| Ngân hàng | 1,0-1,2 | Xấp xỉ thị trường, chi phối chỉ số |
| Bán lẻ / tiêu dùng | 0,8-1,1 | Trung tính |
| Điện, nước, khí (POW, NT2, REE, GAS, TDM/BWE) | 0,5-0,8 | Phòng thủ, cổ tức đều |
| Bảo hiểm (BVH, BMI, PVI) | 0,6-0,9 | Hưởng lợi khi lãi suất cao |

Beta trong bảng là *điển hình lịch sử* — bắt buộc tính lại theo dữ liệu thật (2 năm, khung tuần) trước khi dùng, không lấy nguyên số này để báo cáo.

### 4. Phòng hộ rủi ro đuôi tại VN (không có công cụ trực tiếp)

Không có put OTM, không có VIX futures. Các phương án thay thế, xếp theo tính khả thi:

1. **Short VN30F duy trì tỷ lệ nhỏ (10-20% danh mục)**: chi phí = basis + phí + ký quỹ chết vốn. Nhược điểm: lỗ tuyến tính khi thị trường tăng (khác hẳn quyền chọn — không có tính lồi)
2. **Nắm vàng (miếng SJC / nhẫn)**: tương quan thấp với VN-Index, tăng mạnh trong sốc tỷ giá và địa chính trị. Nhược điểm VN-đặc thù: **chênh lệch SJC với giá thế giới có thể tự co lại** do chính sách đấu thầu/nhập khẩu của SBV, làm hỏng phòng hộ đúng lúc cần — ưu tiên vàng nhẫn (chênh thấp hơn) nếu mục tiêu là bám giá thế giới
3. **Tiền gửi kỳ hạn ngắn**: phòng hộ đuôi rẻ nhất về mặt chi phí cơ hội tại VN
4. **Nắm USD / tiền gửi USD**: lãi suất USD trong nước bị áp trần 0%, nên đây là cược thuần vào tỷ giá; hiệu quả trong kịch bản VND mất giá nhưng chịu chi phí cơ hội lớn

**Ghi nhớ:** phòng hộ đuôi kiểu Taleb (mất ít thường xuyên, thắng lớn hiếm khi) **không tái tạo được ở VN** vì thiếu tính lồi của quyền chọn. Đừng hứa hẹn cấu trúc lợi nhuận đó cho khách hàng.

### 5. Phòng hộ chéo

**Cổ phiếu — trái phiếu:**

| Tỷ lệ CP/TP | Biến động kỳ vọng | Bối cảnh phù hợp |
|---------|-----------|---------|
| 80/20 | ~18-22% | Chu kỳ nới lỏng, tín dụng mở |
| 60/40 | ~13-16% | Phân bổ chuẩn |
| 40/60 | ~9-12% | Chu kỳ thắt chặt / hậu sốc |
| 100% tiền gửi | ~0% | Đình lạm, sốc tỷ giá |

**Cảnh báo riêng cho VN:** "trái phiếu" ở VN phải tách hai loại rất khác nhau —
- **TPCP / quỹ TPCP**: tương quan âm với cổ phiếu tương đối ổn định, phòng hộ được
- **TPDN (trái phiếu doanh nghiệp, đặc biệt BĐS)**: tương quan **dương** với cổ phiếu trong khủng hoảng, và mất thanh khoản hoàn toàn (2022-2023 là bằng chứng). **TPDN không phải tài sản phòng hộ** — nó là rủi ro tín dụng đội lốt thu nhập cố định

**Cổ phiếu — hàng hóa:**
- Lạm phát tăng: hàng hóa tăng, cổ phiếu chịu áp lực → nhóm dầu khí (PLX, BSR, GAS, PVS) và cao su, gạo, cà phê là phòng hộ tự nhiên trong danh mục cổ phiếu VN
- Lạm phát giảm: cổ phiếu dẫn dắt, hàng hóa yếu

**Phòng hộ tỷ giá (cho quỹ có nhà đầu tư nước ngoài hoặc nợ USD):**
- Công cụ: hợp đồng kỳ hạn USD/VND qua NHTM. Giá kỳ hạn ≈ giao ngay × (1 + chênh lệch lãi suất VND-USD × t/360)
- Chi phí phòng hộ ≈ **điểm kỳ hạn**, phản ánh chênh lệch lãi suất — khi lãi suất VND cao hơn USD, phòng hộ *có phí*; khi lãi suất VND thấp hơn (giai đoạn 2023-2024), phòng hộ có thể *có lãi carry* nhưng khi đó áp lực mất giá VND lại lớn nhất
- Ràng buộc: hợp đồng kỳ hạn onshore cần chứng từ giao dịch cơ sở theo quy định quản lý ngoại hối. Quỹ đầu tư tài chính thuần thường **không đủ điều kiện** — nêu rõ giới hạn này thay vì giả định hedge được

### 6. Phương pháp tính tỷ lệ phòng hộ

```python
import numpy as np
import pandas as pd
from scipy import stats

# Cách 1: hồi quy OLS (đơn giản nhất)
slope, intercept, r, p, se = stats.linregress(hedge_returns, portfolio_returns)
hedge_ratio_ols = slope
r_squared = r ** 2   # BẮT BUỘC báo cáo — dưới 0,6 thì VN30F không phòng hộ nổi

# Cách 2: phương sai tối thiểu
covariance = np.cov(portfolio_returns, hedge_returns)[0][1]
hedge_ratio_mv = covariance / np.var(hedge_returns)

# Cách 3: EWMA (nhạy hơn với chế độ hiện tại)
lambda_param = 0.94  # mặc định RiskMetrics
ewma_cov = pd.Series(portfolio_returns * hedge_returns).ewm(alpha=1-lambda_param).mean()
ewma_var = pd.Series(hedge_returns**2).ewm(alpha=1-lambda_param).mean()
hedge_ratio_ewma = ewma_cov / ewma_var

# Chọn cách nào:
# Phòng hộ tĩnh (tái cân bằng tháng) -> OLS, khung tuần, 2 năm
# Phòng hộ động (tái cân bằng tuần)  -> EWMA
# Phân tích lý thuyết               -> phương sai tối thiểu
```

### 7. Đánh giá chi phí phòng hộ

| Hạng mục | Short VN30F | Giảm trạng thái | Phòng hộ chéo |
|--------|---------|---------|-----------|
| Chi phí trực tiếp | Phí GD + phí quản lý vị thế + phí quản lý tài sản ký quỹ (VSD/CTCK) | Phí GD + **thuế TNCN 0,1% trên giá bán** | Không |
| Chi phí cơ hội | Ký quỹ chết vốn (~18-20% giá trị hợp đồng) | Mất upside, bù bởi lãi tiền gửi | Lợi suất thấp hơn cổ phiếu |
| Chi phí ẩn | **Basis** (thường là khoản lớn nhất) + chi phí đảo vị thế hàng tháng | Trượt giá khi bán khối lượng lớn | Chi phí tái cân bằng |
| Ước tính năm hoá | 3-8% (chủ yếu do basis và roll) | ~0,3-0,6%/vòng mua-bán + chi phí cơ hội | 1-3% |

Số phí cụ thể phải tra biểu phí VSD/HNX/CTCK hiện hành tại thời điểm phân tích — **không lấy số trong tài liệu này để tính tiền thật**.

**Khung quyết định có nên phòng hộ:**

```python
hedge_cost_annual = 0.05            # 5%/năm gồm basis + phí + roll
deposit_rate = 0.065                # lãi suất tiền gửi 12T — chi phí cơ hội của phương án "về tiền"
expected_loss_without_hedge = 0.20  # mức lỗ kỳ vọng nếu không phòng hộ
prob_of_loss = 0.30                 # xác suất kịch bản xấu

expected_loss = expected_loss_without_hedge * prob_of_loss   # = 6,0%

# So sánh BA phương án, không phải hai:
# 1. Không làm gì:      lỗ kỳ vọng 6,0%
# 2. Short VN30F:       chi phí 5,0% chắc chắn
# 3. Về tiền gửi:       chi phí cơ hội = upside kỳ vọng bị mất, NHƯNG được +6,5% lãi
# Ở VN phương án 3 rất thường thắng phương án 2 — luôn đưa nó vào so sánh
```

## Khung phân tích

### Quy trình 5 bước

1. **Nhận diện rủi ro**: hệ thống (beta) hay riêng lẻ (sự kiện một mã)? Rủi ro riêng lẻ thì VN30F vô dụng — phải bán mã đó
2. **Chọn công cụ**: đối chiếu bảng công cụ ở đầu tài liệu. Nếu công cụ cần thiết không tồn tại tại VN, nói thẳng và chuyển sang giảm trạng thái
3. **Tính tỷ lệ**: số hợp đồng VN30F, kèm R² của hồi quy beta
4. **Đánh giá chi phí**: gồm basis tại thời điểm vào lệnh; so sánh với phương án về tiền gửi
5. **Theo dõi và điều chỉnh**: beta trôi, hợp đồng đáo hạn hàng tháng (thứ Năm thứ ba), ký quỹ bị gọi bổ sung khi thị trường tăng

### Ánh xạ kịch bản rủi ro → công cụ (VN)

| Kịch bản rủi ro | Công cụ khả thi tại VN | Mức chi phí |
|---------|---------|---------|
| Thị trường giảm diện rộng | Short VN30F1M / hạ tỷ trọng | Trung bình (basis) / thấp |
| Giảm vừa 5-10% | Hạ tỷ trọng 30-50%, xoay nhóm phòng thủ | Thấp |
| Sập >20% (đuôi) | Short VN30F + nắm vàng + tiền gửi | Trung bình, không có tính lồi |
| Lãi suất tăng | Rút ngắn duration trái phiếu, tăng tiền gửi ngắn hạn; **không có HĐTL TPCP thanh khoản** | Thấp |
| VND mất giá | Kỳ hạn USD/VND (nếu đủ điều kiện), nắm cổ phiếu xuất khẩu thu USD | Trung bình |
| Lạm phát vượt dự báo | Tăng dầu khí, hàng hóa, vàng | Chi phí cơ hội |
| Rủi ro giải chấp margin toàn thị trường | Hạ dư nợ margin về 0 TRƯỚC, phòng hộ sau | Thấp — đây là bước quan trọng nhất |
| Sự kiện một mã (room, cổ đông lớn, kiểm toán) | Bán mã đó; VN30F không giúp gì | Phí bán |

## Định dạng đầu ra

```
## Phương án phòng hộ — [Tên danh mục]

### Tổng quan danh mục
- Quy mô: [X tỷ VND]
- Beta danh mục: [X,XX] so với VN30 (2 năm, khung tuần) — R² = [0,XX]
- Rủi ro chính: [hệ thống / tập trung ngành / đuôi / margin]
- Dư nợ margin hiện tại: [X tỷ, tỷ lệ X% NAV]

### Phương án đề xuất
- Công cụ: [short VN30F1M / hạ tỷ trọng X% / xoay nhóm / kết hợp]
- Tỷ lệ phòng hộ: [X,XX]
- Số hợp đồng: [N] — ký quỹ cần [X tỷ]
- Độ phủ: [X%] (toàn phần / một phần)
- Basis tại thời điểm vào lệnh: [X điểm, chiết khấu/premium] → chi phí ẩn ước [X%]

### Đánh giá chi phí
- Chi phí trực tiếp: [X triệu VND/năm]
- Chi phí năm hoá: [X%]
- Ký quỹ chiếm dụng: [X tỷ VND]
- **So sánh phương án thay thế**: về tiền gửi 12T lãi [X%] → chi phí ròng của việc hedge là [X%]

### Phân tích kịch bản
| Biến động TT | Lãi/lỗ không hedge | Lãi/lỗ có hedge | Hiệu quả |
|---------|-----------|-----------|---------|
| Giảm 10% | −X | −X | Giảm lỗ X |
| Giảm 20% | −X | −X | Giảm lỗ X |
| Tăng 10% | +X | +X | Mất X upside |

### Lưu ý thực thi
- Thời điểm vào: [điều kiện cụ thể — tránh vào khi basis chiết khấu sâu]
- Tần suất tái cân bằng: [tháng / tuần / theo sự kiện]
- Lịch đảo vị thế: thứ Năm thứ ba hàng tháng (ngày đáo hạn VN30F1M)
- Điều kiện thoát phòng hộ: [tiêu chí rủi ro đã giải toả]
```

## Lưu ý

- **VN không có quyền chọn niêm yết**: mọi đề xuất Protective Put / Collar / Put Spread trên cổ phiếu VN đều sai. CW chỉ có chiều mua, không phòng hộ giảm giá được
- **Thanh khoản phái sinh chỉ tập trung ở VN30F1M**; các kỳ hạn xa gần như không có đối ứng — đừng thiết kế phòng hộ nhiều tháng bằng hợp đồng quý
- **Basis là chi phí lớn nhất và biến động nhất** tại VN, không phải phí giao dịch. Phòng hộ mua vào lúc thị trường đã hoảng loạn thường đắt đến mức vô nghĩa
- **Beta không ổn định**: beta thường thấp trong pha tăng và cao trong pha giảm — nghĩa là phòng hộ thiếu hụt đúng lúc cần nhất. Với midcap/smallcap VN, hiện tượng này còn mạnh hơn
- **Ưu tiên hạ dư nợ margin trước khi phòng hộ.** Ở VN, phần lớn tổn thất trong các nhịp sập đến từ giải chấp cưỡng bức chứ không phải từ beta. Phòng hộ bằng VN30F trong khi vẫn giữ margin cao là chữa triệu chứng
- Thuế 0,1% trên giá bán (không phụ thuộc lãi/lỗ) làm phương án giảm trạng thái đắt hơn thoạt nhìn với danh mục quay vòng nhiều
- Tương quan phòng hộ chéo có thể vọt về 1 trong khủng hoảng — TPDN là ví dụ điển hình đã hỏng tại VN năm 2022
- Rà soát lại beta, R² và chi phí ít nhất hàng tháng
- Khung này phục vụ nghiên cứu/backtest, không phải khuyến nghị đầu tư và không bao gồm thực thi lệnh


## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)

1. **Không bịa/cook số liệu.** Mọi số tài chính phải có nguồn thật. Luôn **audit nhanh, cross-check tối thiểu 2 nguồn uy tín** (vd `cafef.vn`, `vietstock.vn`, `hnx.vn`, `vsd.vn`) — dùng **crawl4ai** cào số rồi đối chiếu; nếu nguồn lệch nhau thì nêu rõ, không chọn bừa.
2. **Nếu DataPro VÀ vnstock đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
- Biểu phí phái sinh, tỷ lệ ký quỹ và quy chế hợp đồng thay đổi theo thời gian — tra VSD/HNX tại thời điểm phân tích, không dùng số trong tài liệu này.
