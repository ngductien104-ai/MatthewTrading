# Third Eyes — kiểm kê nền ngày 14/09/2026

Báo cáo từ cấu hình `third-eyes.json` và kho `.third-eyes`, kiểm tra khoảng 22:05 giờ Việt Nam. Không gọi nhà cung cấp trong lần kiểm kê này. Phạm vi là 15 nguồn đã cấu hình; chưa kiểm kê toàn bộ file dữ liệu rời trong workspace.

| Kết quả | Số nguồn | Ý nghĩa |
|---|---|---|
| Available | 1 | `vnindex_close` có metadata lần lấy và lịch sử local |
| Pending | 10 | Chưa có kết quả kiểm tra trong kho cho nguồn cấu hình tương ứng |
| Disabled | 4 | Placeholder chưa bật: company_earnings, us_policy_rate, usd_index, company_disclosures |

`vnindex_close`: 2.492 quan sát đóng bar, từ 16/09/2016 đến 11/09/2026. Hai rule threshold cần tối thiểu 66 quan sát nên đủ lịch sử để tính. Lần kiểm tra nguồn ghi trong kho là 14/09/2026 15:11:37 giờ Việt Nam. Cấu hình cho phép tuổi dữ liệu 5 ngày nên nguồn vẫn đạt tiêu chí freshness hiện tại; điều này không xác nhận đã có bar đóng cửa ngày 14/09.

Chưa có rule orphan trong cấu hình. Đủ lịch sử không đồng nghĩa rule đã backtest đạt hoặc được nâng Priority.

## Đã triển khai

- CLI `inventory` và API có xác thực `/third-eyes/v1/inventory`.
- Báo tuổi dữ liệu, lịch sử theo entity/rule, nguồn tắt/thiếu, rule thiếu nguồn và thiếu lịch sử.
- Phân biệt schema mismatch, lưu cột có/thiếu, kiểm tra cột entity trước khi xử lý.
- CLI `scan --source ID` để kiểm tra một hoặc nhiều nguồn được chỉ định.
- 25 test Third Eyes đạt, gồm 4 test kiểm kê mới. Lần chạy đầu vướng quyền thư mục tạm pytest; lần chạy với thư mục tạm riêng trong workspace đạt.

## Phần tiếp theo

1. Kiểm tra nguồn thật theo từng nhóm, bắt đầu giá/khối lượng và CPI; lưu kết quả có thời gian kiểm tra.
2. Kiểm kê dữ liệu rời để tìm nguồn local có thể bổ sung; xác minh schema và đơn vị trước khi đăng ký.
3. Hoàn thiện freshness theo phiên để phát hiện thiếu bar EOD mới nhất dù chưa vượt giới hạn tuổi tổng quát.
4. Bổ sung source probe có giới hạn, retry/backoff và dữ liệu mẫu cho đủ bốn domain.

Đây là phần đầu của P0/P1; chưa hoàn thành toàn bộ P1, chưa bật monitor liên tục và chưa thay đổi Fincept.
