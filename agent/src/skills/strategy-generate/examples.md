# Sinh chiến lược — Ví dụ

## Ví dụ 1: Giao cắt 2 đường MA cổ phiếu VN (vnstock/datapro)

Người dùng: "Làm chiến lược giao cắt 2 đường MA cho VCB, ngắn 5 phiên dài 20 phiên, backtest năm 2025"

Chuỗi lời gọi:
1. load_skill("strategy-generate") → lấy hướng dẫn quy trình
2. write_file("config.json") → cấu hình mã / ngày / tham số
   ```json
   {"source": "auto", "codes": ["VCB.VN"], "start_date": "2025-01-01", "end_date": "2025-12-31", "initial_cash": 1000000, "commission": 0.001, "extra_fields": null}
   ```
3. write_file("code/signal_engine.py") → code chiến lược 2 đường MA
4. bash("python -c \"import ast; ast.parse(open('code/signal_engine.py').read()); print('OK')\"") → kiểm tra cú pháp AST
5. backtest(run_dir=...) → chạy backtest (engine tích hợp sẵn)
6. read_file("artifacts/metrics.csv") → xem kết quả, chấm theo tiêu chí đánh giá
7. (nếu cần sửa) edit_file("code/signal_engine.py", ...) → backtest → read_file

## Ví dụ 2: Chiến lược RSI cổ phiếu Mỹ (yfinance)

Người dùng: "Xây chiến lược RSI cho AAPL, mua khi RSI<30 bán khi RSI>70, backtest 2024"

Chuỗi lời gọi:
1. load_skill("strategy-generate") → lấy hướng dẫn quy trình
2. write_file("config.json") → cấu hình
   ```json
   {"source": "yfinance", "codes": ["AAPL.US"], "start_date": "2024-01-01", "end_date": "2024-12-31", "initial_cash": 1000000, "commission": 0.001, "extra_fields": null}
   ```
3. write_file("code/signal_engine.py") → code chiến lược RSI
4. bash("python -c \"import ast; ast.parse(open('code/signal_engine.py').read()); print('OK')\"") → kiểm tra AST
5. backtest(run_dir=...) → chạy backtest (engine tích hợp sẵn)
6. read_file("artifacts/metrics.csv") → xem kết quả
7. (nếu cần sửa) edit_file → backtest → read_file

## Ví dụ 3: Chiến lược bám xu hướng crypto (okx)

Người dùng: "Chiến lược trend-following BTC-USDT, backtest 2024"

Chuỗi lời gọi:
1. load_skill("strategy-generate") → lấy hướng dẫn quy trình
2. write_file("config.json") → cấu hình
   ```json
   {"source": "okx", "codes": ["BTC-USDT"], "start_date": "2024-01-01", "end_date": "2024-12-31", "initial_cash": 1000000, "commission": 0.001, "extra_fields": null}
   ```
3. write_file("code/signal_engine.py") → code chiến lược xu hướng
4. bash("python -c \"import ast; ast.parse(open('code/signal_engine.py').read()); print('OK')\"") → kiểm tra AST
5. backtest(run_dir=...) → chạy backtest (engine tích hợp sẵn)
6. read_file("artifacts/metrics.csv") → xem kết quả
7. (nếu cần sửa) edit_file → backtest → read_file
