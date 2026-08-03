---
name: seasonal
description: "Chiến lược mùa vụ / hiệu ứng lịch cho TTCK VN — sóng trước-sau Tết, tháng cô hồn, mùa ĐHCĐ và chia cổ tức, kỳ review ETF, mùa BCTC. Sinh tín hiệu từ quy luật thời gian trên dữ liệu OHLCV bất kỳ."
category: strategy
---
# Chiến lược mùa vụ / hiệu ứng lịch (Việt Nam)

## Mục đích

Khai thác quy luật lặp theo thời gian của thị trường (hiệu ứng tháng, hiệu ứng thứ trong tuần, sự kiện lịch) để sinh tín hiệu giao dịch. Tại VN, các hiệu ứng mạnh nhất gắn với **lịch âm** (Tết, tháng cô hồn) và **lịch sự kiện doanh nghiệp** (ĐHCĐ, cổ tức, BCTC quý), chứ không phải lịch dương thuần túy.

## Logic tín hiệu

### Hiệu ứng tháng (mặc định)

- Tháng thuận → mở vị thế mua
- Tháng nghịch → đứng ngoài / bán
- Các tháng còn lại → trung tính (bắt buộc trả về 0, không được bỏ qua)

### Hiệu ứng thứ trong tuần (tùy chọn)

- Hiệu ứng thứ Hai / thứ Sáu
- Hiệu ứng đầu tháng / cuối tháng (dòng tiền quỹ, giải ngân định kỳ)

### Chế độ kết hợp

Tín hiệu tháng × tín hiệu thứ; chỉ vào vị thế khi cả hai xác nhận.

## Bảng hiệu ứng lịch tại TTCK Việt Nam

| Hiệu ứng | Mô tả | Cấu hình tham chiếu |
|------|------|---------|
| **Sóng trước Tết** | Dòng tiền và tâm lý tích cực 2-4 tuần trước Tết Nguyên đán; thanh khoản tăng, midcap chạy | Cửa sổ theo **lịch âm**, thường rơi vào tháng 1 dương |
| **Trũng thanh khoản Tết** | Tuần nghỉ Tết và tuần liền sau: thanh khoản cạn, biến động méo — tránh mở vị thế mới | Loại bỏ khỏi mẫu backtest |
| **Sóng sau Tết / "tháng Giêng"** | Kỳ vọng kế hoạch kinh doanh năm mới, mùa ĐHCĐ đến gần | bullish_months=[1,2,3] (cần hiệu chỉnh theo năm Tết sớm/muộn) |
| **Mùa ĐHCĐ & cổ tức** | Tháng 4-6: công bố kế hoạch năm, chia cổ tức/cổ phiếu thưởng, chốt quyền | bullish_months=[3,4] |
| **Sell in May** | Tháng 5 trở đi thường yếu hơn, trùng vùng trống thông tin sau ĐHCĐ | bearish_months=[5,6] |
| **Tháng cô hồn** | Tháng 7 âm lịch (thường rơi vào tháng 8 dương): tâm lý kiêng kỵ mua mới rất phổ biến ở nhà đầu tư cá nhân VN — hiệu ứng có tính tự thực hiện | bearish_months=[8] theo **lịch âm** |
| **Mùa BCTC quý** | Cuối tháng 1, 4, 7, 10 — biến động tăng quanh ngày công bố; hiệu ứng "tin ra là bán" phổ biến | Dùng làm bộ lọc biến động, không phải tín hiệu hướng |
| **Review ETF ngoại** | FTSE và MSCI cơ cấu vào tháng 3, 6, 9, 12 — dòng tiền một lần, đảo chiều sau ngày hiệu lực | Sự kiện, không phải hiệu ứng tháng |
| **Cuối năm** | Tháng 11-12: quỹ chốt NAV, "làm đẹp" danh mục, kỳ vọng kết quả năm | bullish_months=[11,12] |
| **Hiệu ứng thứ Hai** | Lợi suất thứ Hai thấp hơn trung bình | bearish_weekdays=[0] |
| **Hiệu ứng thứ Sáu** | Lợi suất thứ Sáu cao hơn; lưu ý thứ Năm thứ ba là ngày đáo hạn phái sinh, gây méo | bullish_weekdays=[4] |

## Tham số

| Tham số | Mặc định | Mô tả |
|------|--------|------|
| bullish_months | [1, 2, 3, 11, 12] | Tháng thuận |
| bearish_months | [5, 6, 8] | Tháng nghịch (tháng 8 ≈ tháng cô hồn) |
| use_weekday | False | Bật hiệu ứng thứ trong tuần |
| bullish_weekdays | [4] | Thứ thuận (0=Thứ Hai, 4=Thứ Sáu) |
| bearish_weekdays | [0] | Thứ nghịch |
| lunar_adjust | False | Dịch cửa sổ Tết / tháng cô hồn theo lịch âm từng năm |

## Lỗi thường gặp

- **Tết trôi theo năm**: Tết Nguyên đán dao động từ cuối tháng 1 đến giữa tháng 2 dương lịch. Dùng hiệu ứng tháng dương cứng sẽ **trộn lẫn** giai đoạn trước Tết và sau Tết giữa các năm, làm tín hiệu tự triệt tiêu. Muốn khai thác sóng Tết thì phải quy về **số phiên trước/sau ngày giao dịch cuối cùng của năm âm lịch**, không dùng `month`
- **Tháng cô hồn cũng trôi**: tháng 7 âm có thể rơi vào tháng 8 hoặc bắc cầu sang tháng 9 dương
- Kỳ nghỉ Tết làm gián đoạn 5-9 phiên; nếu không xử lý sẽ tạo khoảng trống dữ liệu và giá trị biến động giả
- `pd.DatetimeIndex.month` bắt đầu từ 1 (1 = tháng Một)
- `pd.DatetimeIndex.weekday` bắt đầu từ 0 (0 = Thứ Hai, 4 = Thứ Sáu)
- **Cỡ mẫu**: TTCK VN chỉ có lịch sử từ 2000, thực chất thanh khoản đủ để thống kê từ khoảng 2009. Một hiệu ứng tháng chỉ có ~15 quan sát ⇒ **rất dễ khớp nhiễu**. Bắt buộc báo cáo số quan sát, độ lệch chuẩn và kiểm định ý nghĩa, không chỉ báo lợi suất bình quân
- Hiệu ứng mùa vụ là quy luật thống kê, không phải tín hiệu tất định — dùng làm lớp trọng số, không dùng làm tín hiệu độc lập
- Tháng trung tính (không nằm trong `bullish` lẫn `bearish`) phải trả về 0

## Phụ thuộc

```bash
pip install pandas numpy
# Nếu cần quy đổi lịch âm:
pip install lunardate
```

## Quy ước tín hiệu

- `1` = mua (cửa sổ thuận), `-1` = bán/đứng ngoài (cửa sổ nghịch), `0` = trung tính

Lưu ý: TTCK VN **không bán khống được cổ phiếu cơ sở**, nên tín hiệu `-1` trên cổ phiếu chỉ nên hiểu là "đóng vị thế / đứng ngoài". Chỉ với VN30F mới thực hiện được vị thế short thật.


## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)

1. **Không bịa/cook số liệu.** Mọi số tài chính phải có nguồn thật. Luôn **audit nhanh, cross-check tối thiểu 2 nguồn uy tín** (vd `cafef.vn`, `vietstock.vn`) — dùng **crawl4ai** cào số rồi đối chiếu; nếu nguồn lệch nhau thì nêu rõ, không chọn bừa.
2. **Nếu DataPro VÀ vnstock đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
