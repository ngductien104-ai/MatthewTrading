# Third Eyes — nghiệm thu vnstock_data 3.2.9

Ngày 14/09/2026. Kết luận: chưa đưa 3.2.9 vào sử dụng cho Third Eyes; đã khôi phục bản sao 3.2.8 trong venv dự án do lỗi nguồn BCTC. Home venv không được cập nhật.

## Kết quả kiểm tra

| Hạng mục | Kết quả với 3.2.9 |
|---|---|
| Nguồn gói | Catalog API chính thức xác nhận 3.2.9; tải bằng installer chính thức 3.1.2 đã có trong home venv |
| Cài đặt | Thành công, metadata xác nhận 3.2.9 |
| Dependency | `pip check` không có xung đột |
| Test Third Eyes | 25 test đạt; các test dùng dữ liệu giả lập không phát hiện được lỗi upstream dưới đây |
| Lãi suất ON | Available, 2.644 dòng |
| Giá/volume và ngành | Available trong lượt quét live |
| CPI | Vẫn 125 dòng, mới nhất tháng 6/2026; stale |
| BCTC VCB mặc định | Log taxonomy báo provider MAS không map được, dữ liệu không có `id`; adapter hiện tại từ chối |
| BCTC VCB với route KBS | Lỗi bên trong provider: `value_name (value) cannot match an element in the DataFrame columns` |

Không đổi tên cột hoặc bỏ kiểm tra schema để che lỗi taxonomy. Chưa kết luận toàn bộ API 3.2.9 bị lỗi; phạm vi bằng chứng là BCTC VCB đã kiểm tra.

## Khôi phục và tái lập

- Bản sao trước cập nhật: `.third-eyes/package-update-3.2.9/vnstock_data` và dist-info 3.2.8.
- Gói 3.2.9 và báo cáo live vẫn giữ để điều tra: `.third-eyes/source-verification-3.2.9.json`.
- Script cập nhật: `agent/scripts/update_third_eyes_vnstock.py`, chạy bằng home venv có installer chính thức, đích cài luôn là venv dự án.
- Script khôi phục: `agent/scripts/restore_third_eyes_vnstock.py`, chỉ chấp nhận đích hiện ở 3.2.9 và có đủ backup.
- Sau khôi phục: `pip check` đạt; 25 test Third Eyes đạt lại.
- Lượt query xác nhận sau khôi phục lưu tại `.third-eyes/source-verification-restored-328.json`.
- Script kiểm tra nguồn đã bổ sung phiên bản package vào báo cáo cho các lượt chạy mới.

## Sự cố installer đã xử lý

Lệnh có `--extra-index-url` đã chọn gói `vnstock_installer` 99.0.0 từ PyPI, metadata ghi “isolated name-occupancy research; harmless echo only”, không phải installer chính thức. Gói đó đã được gỡ khỏi venv dự án. Các bước tải/cài sponsored sau đó dùng client chính thức có sẵn, qua host `vnstocks.com`, không in credential hoặc signed URL. Không dùng lại lệnh cài không ghim nguồn này.

Monitor liên tục, Ollama và Fincept không được khởi động trong đợt cập nhật. Lần nâng tiếp theo cần kiểm tra thành công schema BCTC, taxonomy và dữ liệu live trước khi thay bản đang hoạt động.
