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
- [x] **0.4 Chặn mất dữ liệu** — kho nghiên cứu nay có version control
  - ⚠️ Repo `ngductien104-ai/MatthewTrading` là **PUBLIC** → không được đưa vault/`Database`/
    `VNDIRECT`/`_portfolio_review*` vào đây. Anh chọn phương án **repo GitHub riêng tư thứ hai**.
  - Kỹ thuật: **bare repo + work-tree** — repo thứ hai theo dõi cùng thư mục, index riêng,
    không phải di chuyển file nào, không lồng `.git`.
    ```sh
    BARE="C:/Users/VVVZV/research-vault.git"
    git --git-dir=$BARE --work-tree=C:/Users/VVVZV/MatthewTrading <lệnh git bình thường>
    ```
    `status.showUntrackedFiles=no`; danh sách loại trừ ở `$BARE/info/exclude`
    (mp4/mp3/exe/dll/pak + phần ứng dụng Obsidian nằm chung thư mục vault).
  - Ảnh chụp đầu tiên `36f6e84`: **917 file, 93 MB**, gồm đủ 24 `*_MOC.md`, `Home.md`,
    `_portfolio_review_202608/data/*`, `_fund_panel_202608/data/fund_metrics.csv`.
  - [x] **Remote riêng tư đã nối và đẩy lên.** `origin` =
    `https://github.com/ngductien104-ai/MatthewResearch` — **917 file, nhánh `master`**.
    ⚠️ Repo này lúc đầu bị tạo nhầm thành PUBLIC; đã kiểm bằng API ẩn danh
    (`"private": false`) và **từ chối push**, chờ đổi sang private rồi kiểm lại
    (HTTP 404 + `ls-remote` ẩn danh không thấy ref) mới đẩy.
    **Quy tắc: trước mỗi lần push kho này, xác minh bằng
    `curl -s -o /dev/null -w "%{http_code}" https://api.github.com/repos/ngductien104-ai/MatthewResearch`
    — phải là 404. Không tin lời khai, chỉ tin mã HTTP.**
  - Lệnh hằng ngày:
    ```sh
    git --git-dir=C:/Users/VVVZV/research-vault.git         --work-tree=C:/Users/VVVZV/MatthewTrading <lệnh git>
    ```

- [x] **0.5 Lỗi provider không còn giết từng task một** — `src/swarm/runtime.py`
  - Nguyên nhân thật của 3/18: **402 hết số dư = 31 task**, `401 User not found` = 8,
    blocked 17, connection 4, **503 chỉ 4**. Mỗi task còn đốt hết ngân sách retry trước khi chết,
    rồi mọi layer sau đâm vào đúng bức tường đó.
  - Thêm `classify_fatal_provider_error()`: 402/401/403/insufficient balance/invalid key là
    **không đáng retry** → bỏ ngay phần retry còn lại **và** `cancel_event.set()` để dừng cả run.
  - 503/overload, 429, connection, timeout **vẫn retry** — huỷ run vì 503 còn tệ hơn lỗi đang sửa.
  - Pattern neo theo cách provider thật sự viết (`"error code: 402"`), không khớp số trần —
    dương tính giả ở đây là huỷ oan một run đang khoẻ.
  - `tests/test_swarm_fatal_provider_error.py` (9 test), dùng **chuỗi lỗi lấy nguyên văn**
    từ `agent/.swarm/runs`.
  - Anh chốt: giữ `openai-codex` cho swarm, **và** vẫn dùng subagent Claude trong phiên
    Claude Code như 3 tháng qua.
  - [ ] **Việc của anh:** `agent/.env` còn `OPENROUTER_API_KEY` dài 22 ký tự (placeholder chết).
    Em không tự sửa file secrets. Anh xoá dòng đó khi tiện — hiện vô hại vì provider là
    `openai-codex`, nhưng sẽ gây khó hiểu nếu sau này đổi provider.
- [x] **0.6 Đối chiếu full suite**
  - baseline `11 failed, 3131 passed, 1 skipped, 9 errors`
  - sau G0 `11 failed, **3142** passed, 1 skipped, 9 errors`
  - +11 pass = đúng 11 test mới (2 optimizer look-ahead + 9 swarm fatal-error).
    Fail và error **không đổi một cái nào**.

---

## ✅ GIAI ĐOẠN 0 HOÀN TẤT — 5 commit trên nhánh `upgrade/learning-loop`

Chưa push. Ba việc còn chờ anh:
1. Tạo repo GitHub **private** rồi `remote add origin` cho `research-vault.git` (lệnh ở mục 0.4)
2. Xoá `OPENROUTER_API_KEY` chết trong `agent/.env`
3. Xác nhận push nhánh `upgrade/learning-loop` lên repo public

## Giai đoạn 1 — Sổ cái quyết định *(chưa bắt đầu)*
## Giai đoạn 2 — PIT + backtest cứng *(chưa bắt đầu)*
## Giai đoạn 3 — Playbook + vòng lặp tự động *(chưa bắt đầu)*
