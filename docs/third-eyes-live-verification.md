# Third Eyes — kiểm tra nguồn thật 14/09/2026

Đã chạy một lần, nạp observation/snapshot/coverage vào `.third-eyes`. Không khởi động scheduler, model AI hoặc Fincept.

| Nhóm | Nguồn kiểm tra | Kết quả |
|---|---|---|
| Thị trường | DataPro: giá/volume VNINDEX, VN30INDEX, HNXINDEX, UPCOMINDEX | Cả 8 nguồn available; khoảng 2.493–2.495 dòng mỗi nguồn |
| Vĩ mô | vnstock_data CPI | Query thành công, 125 dòng đầu vào; mới nhất 30/06/2026, stale và không dùng phát tín hiệu mới |
| Vĩ mô | vnstock_data lãi suất liên ngân hàng ON | 2.644 dòng đầu vào, mới nhất 11/09/2026, available theo giới hạn tuổi 5 ngày |
| Ngành | ICB relative strength từ universe và lịch sử giá | Available; bảng tổng hợp 2.457 dòng trước lọc |
| Thị trường | Breadth từ cùng bảng ngành | Available; chỉ dùng các dòng VN_MARKET sau lọc |
| Doanh nghiệp | Giá VCB mẫu | Available, 2.493 dòng, đến 14/09/2026 |
| Doanh nghiệp | Lợi nhuận sau thuế quý VCB mẫu | Available; BCTC đầu vào 884 dòng, chỉ nạp chỉ tiêu đã lọc; đến Q2/2026 |

VCB là mã mẫu kiểm tra, không phải vị thế danh mục được xác nhận. Các cấu hình mới dùng tiền tố `sample_vcb`; watchlist và danh mục vẫn trống. Bốn placeholder cũ vẫn disabled.

Lỗi đã phân biệt: sandbox chặn xác thực vnstock, chạy lại với mạng được duyệt thành công; mặc định `interbank_rate(period='all')` trả 404 nhưng `period='ON'` truy vấn thành công. Cấu hình mới ghi rõ kỳ hạn ON và cột `interest`.

Đã đối chiếu phiên bản trong cả home venv và project venv: `vnstock=4.0.7`, `vnstock_data=3.2.8`, `vnai=2.5.9`. PyPI xác nhận vnstock 4.0.7 mới nhất. Bộ kiểm tra cập nhật sponsored thông báo vnstock_data 3.2.9; chưa nâng phiên bản trong đợt này. Không suy ra nguyên nhân CPI cũ là do phiên bản thư viện.

## Bằng chứng và chạy lại

- `.third-eyes/source-verification-20260914.json`: kết quả quét ban đầu.
- `.third-eyes/interbank-verification-20260914.json`: kết quả ON và inventory tổng hợp sau cùng.
- Script: `agent/scripts/verify_third_eyes_sources.py`, nhận `--config`, `--output`, và `--source` lặp được. Chạy tuần tự, checkpoint sau mỗi nguồn; không tự khởi động monitor. Mỗi lần chạy lại đường dẫn output sẽ cập nhật báo cáo tại đường dẫn đó.
- 25 test Third Eyes đạt trong lần kiểm tra này.

Available chỉ nói nguồn trả dữ liệu đáp ứng cấu hình; không chứng nhận backtest. Dữ liệu ngành dùng universe hiện tại, chưa có thành phần lịch sử đã audit. Ngày công bố/vintage chưa xác minh nên các kết quả chưa đủ để chứng nhận sức dự báo. Chuỗi CPI cũ được giữ nguyên nhãn stale; không nới giới hạn tuổi để biến nó thành nguồn mới.
