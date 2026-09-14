# Third Eyes — hướng dẫn vận hành

## Kiểm kê dữ liệu và kiểm tra từng nguồn

Từ thư mục `agent`, chạy `..\.venv\Scripts\python.exe -m src.third_eyes --config ../third-eyes.json inventory` để xem nguồn đã cấu hình, cột dữ liệu, tuổi dữ liệu và số quan sát hợp lệ cho từng rule. Lệnh chỉ đọc bằng chứng local, không query nhà cung cấp và không gọi AI. API tương ứng là `GET /third-eyes/v1/inventory`, dùng Bearer token như các endpoint dữ liệu khác.

`ready_for_detection` chỉ cho biết dữ liệu đủ điều kiện tính bộ phát hiện hiện tại, không chứng nhận sức dự báo. `pending` là chưa kiểm tra, `missing` là thiếu CSV, `schema_mismatch` là query trả về thiếu cột; `insufficient_history` trong `gaps` cho biết rule thiếu lịch sử. Ngoài `max_age_seconds`, giá/ngành EOD có `expected_session_close` và `session_fresh`; thiếu bar của phiên đã đóng tạo gap `missing_latest_session` ngay cả khi tuổi tuyệt đối vẫn còn trong hạn. Báo cáo không tự khám phá file ngoài những nguồn được cấu hình.

Để lấy lại một nguồn, chạy `..\.venv\Scripts\python.exe -m src.third_eyes --config ../third-eyes.json scan --source vnindex_close`. Có thể lặp `--source` để chọn nhiều nguồn. Không truyền lựa chọn này thì giữ hành vi quét tất cả nguồn đã bật. Lệnh scan gọi nguồn thật; không chạy AI. Lỗi schema được lưu cùng danh sách cột có/thiếu để sửa mapping.

Third Eyes giám sát dữ liệu, phát hiện bất thường và gọi đội chuyên gia AI local để giải thích bằng chứng. Hệ thống không đưa lệnh giao dịch. Bản đầu chạy một tiến trình trên Windows; máy ngủ/tắt thì việc giám sát ngừng và được ghi nhận khi phục hồi.

## Khởi chạy

Từ thư mục MatthewTrading:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-third-eyes.ps1
```

Script dùng Python `.venv` của dự án, tạo `third-eyes.json` và token tại `.third-eyes/access-token` nếu chưa có. ExecutionPolicy chỉ áp dụng cho tiến trình này. Mở `http://127.0.0.1:8790/third-eyes/v1/dashboard`, nhập token từ file để xem Radar, Ưu tiên, bằng chứng và tình trạng dữ liệu. Token không được gửi trong URL hoặc lưu trên trình duyệt. Dừng bằng Ctrl+C. Một thư mục trạng thái chỉ có một tiến trình giám sát; API VibeTrading có thể đọc cùng SQLite.

Cấu hình mặc định dùng Ollama `qwen2.5:3b-16k`, model đã được phát hiện trên máy trong lần triển khai. Chỉ endpoint loopback được chấp nhận; không chuyển sang model cloud. Đổi `local_model` nếu cần. Mỗi tác vụ có tổng thời gian tối đa 600 giây, tối đa hai lần gọi; chỉ một tác vụ AI chạy đồng thời. Dữ liệu không bị chặn trong lúc AI phân tích.

## Danh mục và nguồn dữ liệu

Đặt `excel_directory` trong `third-eyes.json` đến thư mục xuất Excel mong muốn. Trước khi chạy, đặt `ACCOUNT_LOOKUP_TOKEN` và, nếu cần, `CUSTOMER_LOOKUP_TOKEN` bằng mã nội bộ đã dùng trong hệ thống. Không đặt các mã này trong cấu hình có thể chia sẻ. Hệ thống tự thêm giá một phút, khối lượng, lợi nhuận quý và tin doanh nghiệp cho các mã trong danh mục. `watchlist` cho phép thêm mã mà không cần Excel. Khi danh mục chưa cấu hình, hệ thống chỉ theo dõi phần thị trường/ngành/vĩ mô.

Ngày chốt được giữ riêng cho từng file. NAV hoặc số liệu không hợp lệ là `null`; không suy diễn thành 0. Các file `.xls` thực chất chứa XLSX được bộ đọc hiện có hỗ trợ; XLS nhị phân cũ trả lỗi định dạng rõ trên trạng thái danh mục. Snapshot không chứa tên hay số tài khoản.

Nguồn mặc định:

- DataPro: bốn chỉ số, giá và khối lượng. Bar ngày chưa đóng không được dùng cho quy tắc cuối ngày. Giá danh mục dùng bar một phút khi nguồn hỗ trợ; thiếu intraday được báo là thiếu nguồn.
- `vnstock_data`: CPI (`time`, `cpi_total` đã được kiểm tra bằng dữ liệu thật); nguồn khác truy cập qua adapter `vndata` hiện có.
- Ngành/độ rộng: quét cổ phiếu HOSE/HNX/UPCOM, ánh xạ ICB, dùng lợi suất bình quân đều trên mã có giao dịch và tỷ lệ trên MA50. Cache 5 phút, lấy bù 5 ngày sau lần tải đầu. Dưới 80% số mã truy vấn thành công thì không tạo chỉ báo tổng hợp.
- Doanh nghiệp: giá, khối lượng, lợi nhuận sau thuế quý và công bố cho danh mục/watchlist. Công bố mới xuất hiện ở Radar như sự kiện định tính; không có xác suất hay hướng tác động giả định.
- Chuỗi quốc tế và chỉ tiêu bổ sung chưa nối nguồn hiển thị `disabled` cho đến khi cấu hình adapter và schema. Đây là khoảng trống độ phủ, không phải dữ liệu bằng 0.

Mỗi source khai báo `id`, `kind`, `domain`, `indicator`, `entity`, `unit`, `group`, cột ngày/giá trị, tần suất và độ tuổi tối đa. CSV, macro và fundamental yêu cầu ánh xạ cột cụ thể; khi schema không khớp, coverage trả các cột tìm được. `entity_column` hỗ trợ một file chứa nhiều ngành/mã. `filter_column`/`filter_value` chọn một chỉ tiêu trong bảng dài. `published_column` ghi thời điểm công bố thực nếu có; có cột này vẫn chưa đủ để chứng nhận lịch sử các lần sửa đổi.

Quét giá trong phiên theo lịch cấu hình; ngoài phiên kiểm tra tối đa một lần mỗi giờ để phục hồi hoặc nhận cập nhật trễ. `holidays` là danh sách ngày nghỉ YYYY-MM-DD do người vận hành cung cấp. Cấu hình 2026 hiện theo [lịch HNX](https://www.gov.hnx.vn/vi-vn/chi-tiet-lich-nghi-gd-60021971.html?_page=1) và [thông báo điều chỉnh 02/01](https://www.gov.hnx.vn/vi-vn/chi-tiet-lich-nghi-gd-60022084.html?_page=1); các thứ Bảy làm bù không được coi là phiên giao dịch. Khi sang năm mới phải nạp lịch chính thức mới, không tự suy diễn từ lịch nghỉ hành chính. Vĩ mô/quý mặc định kiểm tra hằng ngày, công bố mỗi 5 phút.

Mỗi lần quét lỗi tạm thời có exponential backoff và jitter theo `retry_attempts`, `retry_base_seconds`, `retry_max_seconds`, `retry_jitter_seconds`. Sau `max_consecutive_failures`, nguồn vào trạng thái `backoff` đến `retry_after`; lỗi schema không retry. `health.queue_age` lưu tuổi queue mới nhất, cực đại và số mẫu qua restart. Log quay vòng tại `.third-eyes/third-eyes.log`, kích thước/số bản giữ bởi `log_max_bytes` và `log_backup_count`. Giới hạn hai lượt thu thập đồng thời; nhịp cấu hình là mục tiêu, không phải cam kết độ trễ nguồn.

## Quy tắc và kiểm định

Ba họ quy tắc:

1. `threshold`: so giá trị với phân vị của cửa sổ quá khứ.
2. `trend`: so độ dốc hồi quy 5 quan sát với phân vị độ dốc quá khứ.
3. `pattern`: so thay đổi gia tốc (sai phân bậc hai) với phân vị quá khứ.

Ngưỡng loại trừ quan sát đang kiểm tra. `feature_value` là đại lượng thực sự so ngưỡng; `value` là chỉ báo gốc. `threshold_unit` cho biết thang đo. `objective` up/down là giả thuyết nghiên cứu, không phải kết luận chắc chắn về tương lai. Cấu hình ban đầu là quy tắc khám phá ở Radar.

Chạy các lệnh sau từ thư mục `agent` bằng `..\.venv\Scripts\python.exe`:

```powershell
..\.venv\Scripts\python.exe -m src.third_eyes --config ../third-eyes.json scan
..\.venv\Scripts\python.exe -m src.third_eyes --config ../third-eyes.json status
..\.venv\Scripts\python.exe -m src.third_eyes --config ../third-eyes.json dataset --indicator vnindex_volume --entity VNINDEX --target-entity VNINDEX --target-csv ../target.csv --output ../research/vnindex-volume.csv --adjusted-target --historical-universe
..\.venv\Scripts\python.exe -m src.third_eyes --config ../third-eyes.json backtest --rule vnindex_close_high --csv ../research.csv --horizons 1,5,20
..\.venv\Scripts\python.exe -m src.third_eyes --config ../third-eyes.json rules
```

Lệnh `dataset` ghép as-of Observation trong store lên lịch phiên của target CSV, tạo nhãn `target_return_1/5/20`, cờ `event_eligible` và manifest cạnh CSV có hash/version feature/audit. Dữ liệu vĩ mô forward-fill để giữ đơn vị horizon theo phiên nhưng chỉ ngày đầu tiên một vintage có thể được biết mới được phép phát event, tránh nhân một công bố tháng thành nhiều mẫu độc lập. Dataset synthetic được đánh dấu riêng và không thể chứng nhận rule.

CSV nghiên cứu có các cột `time,value,target_close,published_at,received_at,point_in_time,adjusted_target,historical_universe`. Mỗi dòng là một thời điểm quyết định đã ghép chỉ báo theo thời điểm công bố **và** thời điểm tiếp nhận; `target_close` là giá mục tiêu đã điều chỉnh. Timestamp phải có múi giờ trong dữ liệu chuẩn; lịch sử nghiên cứu được chuẩn hóa UTC. Chỉ đặt các cờ audit `true` khi đã xác minh. Chuỗi giá trong CSV quyết định đơn vị horizon: CSV theo phiên cho 1/5/20 phiên; vĩ mô thêm 20/60 phiên. Không dùng horizon 5 bar phút rồi gọi đó là 5 phiên.

Backtest cố định quy tắc trước khi kiểm tra, lấy nửa đầu làm giai đoạn khởi tạo, ba cửa sổ ngoài mẫu với embargo và không chồng lấn nhãn. Báo cáo có tỷ lệ sai, phân vị lợi suất, biến động bất lợi, khoảng tin cậy bootstrap so mức nền và hạn chế. Độ sớm so một sự kiện thật chưa được ước lượng nếu chưa có nhãn thời điểm sự kiện độc lập; không thay bằng horizon rồi gọi là lead time.

Đưa `research_csv: {"rule_id": "path/to/research.csv"}` vào cấu hình để đánh giá lại hằng tuần ngoài phiên. Mỗi báo cáo được lưu thành certificate bất biến, gắn dataset hash, protocol và phiên bản rule. Một giả thuyết đơn dùng `single_hypothesis`; khi `variants_tested > 1` phải khai báo `--multiple-testing-method bonferroni` cùng `--holdout-id`, và CI dùng alpha đã điều chỉnh. Kết quả synthetic luôn không đủ điều kiện.

Rule registry lưu version và lịch sử `candidate → shadow → validated → retired`. Chuyển trạng thái cần lý do; `validated` chỉ nhận certificate thật, đúng fingerprint và eligible, sau bước shadow. Không có tự động nâng trạng thái sau backtest. Lệnh `rule-transition` là thao tác nghiệm thu có chủ ý của người vận hành.

Ưu tiên yêu cầu: rule ở trạng thái `validated`, ≥30 sự kiện độc lập, ≥3 cửa sổ có sự kiện, cận dưới CI đã điều chỉnh của phần cải thiện >0, audit hợp lệ và chỉ báo xác nhận khác nhóm trên cùng đối tượng trong vòng 24h. Một lần tải hồi cứu của nguồn không tự trở thành dữ liệu point-in-time. Universe ngành hiện tại không được coi là thành phần ngành trong quá khứ. Những hạn chế này giữ tín hiệu ở Radar.

## Replay, bằng chứng và Fincept

`replay --jsonl observations.jsonl --output ../replay-new` chạy trong thư mục mới và không gọi nguồn hay LLM. File JSONL chứa Observation theo hợp đồng Python, thứ tự `received_at`, có `observed_at`, `published_at`, `received_at`, giá trị, đơn vị, nguồn, revision, closed và point_in_time. Replay xét thời điểm dữ liệu có thể được biết và giữ phiên bản mới nhất hợp lệ. So sánh định lượng không phụ thuộc văn bản AI.

API `/third-eyes/v1`: `health`, `coverage`, `indicators`, `portfolio`, `signals`, `signals/{id}`, `signals/{id}/ack`, `evidence/{snapshot}`, `events`. Bearer token bắt buộc cho dữ liệu. `events` hỗ trợ `Last-Event-ID` và `after`; ack độc lập trạng thái tín hiệu. Sự kiện được ghi cùng giao dịch SQLite với cập nhật tín hiệu.

Client TypeScript tại `frontend/src/lib/thirdEyes.ts` có fetch, ack và SSE tự nối lại bằng cursor. Để dùng API VibeTrading hiện có, đặt `THIRD_EYES_CONFIG` đến cùng file cấu hình trước khi khởi động VibeTrading; router kế thừa xác thực của VibeTrading và chỉ đọc backend giám sát, không tạo scheduler thứ hai. Với Fincept native, dùng HTTP client của ứng dụng; không bật CORS wildcard. Checkout Fincept chưa có trong workspace nên không sửa giao diện của dự án đó.

Xuất OpenAPI bằng lệnh `openapi`. Hai preset `third_eyes_watch` và `third_eyes_research` dùng loader, DAG, model và SwarmStore hiện có. Executor Third Eyes chuyên biệt gọi Ollama trực tiếp, cung cấp evidence inline, không có shell/tool hay fallback cloud. Chạy preset qua executor Swarm tổng quát bên ngoài Third Eyes sẽ không tự có các giới hạn local này. Mỗi output phải là AgentReport JSON với evidence ID hợp lệ; agent hỏng thì nhiệm vụ phụ thuộc bị chặn.

## Nghiệm thu vận hành 20 phiên

Giai đoạn quan sát 20 phiên phải diễn ra sau khi chọn nguồn/danh mục và bật tiến trình. Theo dõi coverage, tuổi dữ liệu, khoảng gián đoạn, lỗi AI, số Radar/Ưu tiên, độ trùng và phản hồi đã xem. Kết quả test phần mềm không thay thế 20 phiên quan sát hoặc bằng chứng hiệu quả đầu tư. Chưa có chứng nhận rằng ngưỡng nào sinh lợi; chỉ báo thiếu lịch sử giữ nhãn chưa đủ bằng chứng.
