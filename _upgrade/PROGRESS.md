# Nâng cấp hệ thống nghiên cứu tự học — Tiến độ

**Kế hoạch đầy đủ:** `~/.claude/plans/anh-c-n-em-xem-enumerated-finch.md`
**Cách nối lại khi hết quota:** `claude --continue` trong thư mục repo. Nếu mất phiên,
mở phiên mới và gõ: *"đọc `_upgrade/PROGRESS.md` + kế hoạch trong `~/.claude/plans/`, tiếp tục từ mục chưa tick"*.

**Quy ước:** mỗi mục = một commit riêng. Không để trạng thái nửa vời qua đêm.
**Trình thông dịch:** `C:\Users\VVVZV\MatthewTrading\.venv\Scripts\python.exe` (venv này có pytest;
`$HOME\.venv` thì **không** có pytest nhưng có trọn bộ gói tài trợ).

---

## Mốc test baseline (chốt 28/08/2026, TRƯỚC khi sửa)

```
11 failed, 3131 passed, 1 skipped, 9 errors — 222s
```

Các fail/error có sẵn, **không** liên quan đến việc nâng cấp:
- `test_dividend_analysis_skill.py` ×3
- `test_loader_retry_helpers.py` ×5 (cache duckdb)
- `test_oauth_token_cache.py` ×3
- `tests/factors/test_registry.py` ×9 error (OSError)

Bất kỳ fail nào **ngoài** danh sách này là do mình gây ra.

---

## Giai đoạn 0 — Chặn máu

- [x] **0.1 Benchmark VN** — `backtest/benchmark.py`, `backtest/engines/base.py`
  - Thêm `vn_equity → VNINDEX.VN`; `_infer_market` nhận `.VN` + source datapro/vnstock_data/vnstock
  - `_fetch_benchmark` định tuyến qua `resolve_loader(market)` thay vì hard-code yfinance
  - Thêm `BenchmarkUnavailable` — benchmark hỏng **raise**, không nuốt exception nữa
  - Fallback nội bộ nay mang nhãn `internal_equal_weight_universe`, không đội lốt benchmark thị trường
  - Xoá `_resolve_ticker` (bị mồ côi do inline vào `resolve_benchmark`)
  - **Nghiệm thu** (`agent/runs/vn_benchmark_check/`, VCB.VN 2024-2025):
    | | trước | sau |
    |---|---|---|
    | `benchmark_return` | 3,70% *(buy-and-hold VCB, không nhãn)* | **57,68%** (VNINDEX) |
    | `information_ratio` | −0,239 | **−1,4808** |
    | `excess_return` | — | **−58,14%** |
  - Benchmark sai nay thoát exit 1 với `BenchmarkUnavailable`, đã kiểm bằng `NOSUCHINDEX.VN`
- [x] **0.2 Optimizer look-ahead** — `backtest/optimizers/base.py`
  - `ret.loc[:dt]` → `ret.loc[:dates[i-1]]` (cửa sổ cắt tại bar TRƯỚC bar đang định cỡ)
  - Shock test: `tests/test_optimizer_lookahead.py` (2 test)
  - **Đã xác minh test fail trên code cũ**: weight `0.25/0.44/0.31` → `0.88/−0.94/1.06` — rò rỉ chi phối hẳn kết quả
- [x] **0.3 Định tuyến thị trường** — `backtest/engines/_market_hooks.py`
  - `_detect_market` giữ mặc định `a_share` (có test cũ khẳng định), nhưng **cảnh báo to một lần/mã**
    khi gặp ticker chữ cái trần (`VCB` → gợi ý `VCB.VN`)
- [ ] **0.4 Chặn mất dữ liệu — ĐANG CHỜ ANH QUYẾT ĐỊNH**
  - ⚠️ Repo `ngductien104-ai/MatthewTrading` là **PUBLIC**. Không được đưa thẳng vault +
    `_*` vào git: sẽ công khai `70_DuAn_CongViec/{NAC,CBR}`, `VNDIRECT/`, `DichVuSSE/`,
    `Database/` (danh mục khách hàng), `_portfolio_review_202608/` (NAV + lệnh thật).
  - Hiện trạng: `git ls-files Obsidian/` = 0. `_vre_committee`, `_mwg_research`,
    `_portfolio_review_202608`, `_fund_panel_202608` đều không track. Chỉ `_fpt_research` có.
  - Mỗi lần ghi đè `Home.md` là mất vĩnh viễn một call.
- [ ] **0.5 Sửa provider chết** — 402 hết số dư = 31 task, 401 = 8, 503 chỉ 4.
  Xoá key chết, thêm preflight credential + số dư.
- [ ] **0.6** Chạy lại full suite, đối chiếu với baseline ở trên.

## Giai đoạn 1 — Sổ cái quyết định *(chưa bắt đầu)*
## Giai đoạn 2 — PIT + backtest cứng *(chưa bắt đầu)*
## Giai đoạn 3 — Playbook + vòng lặp tự động *(chưa bắt đầu)*
