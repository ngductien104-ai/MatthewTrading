# Third Eyes — bàn giao để tiếp tục sau khi đổi tài khoản

Ngày rà soát: 14/09/2026, Asia/Bangkok. Workspace: `C:\Users\VVVZV\MatthewTrading`.

## Cảnh báo bảo toàn công việc

Toàn bộ `agent/src/third_eyes/`, hai preset Third Eyes, test, script chạy và client TypeScript hiện là file **untracked**. Một số wiring vào Swarm/VibeTrading là thay đổi tracked nhưng chưa commit. Không chạy `git clean`, `git reset --hard`, xóa workspace hoặc clone đè trước khi kiểm tra và bảo toàn các file này. `third-eyes.json` và `.third-eyes/` bị gitignore vì chứa cấu hình/trạng thái local.

Đổi tài khoản Codex không tự xóa workspace. Đổi tài khoản vnstock có thể thay `~/.vnstock/auth_state.json`; phải kiểm tra tier và xác thực lại trước khi query nguồn sponsored. Không sao chép API key hoặc token vào Git/tài liệu.

## Vị trí hiện tại trong plan

| Giai đoạn | Trạng thái | Bằng chứng / phần còn thiếu |
|---|---|---|
| P0 — chốt nền | Hoàn tất cho phạm vi cấu hình hiện tại | Có kiến trúc, 18 source, 23 rule, inventory, live verification và khoảng thiếu được ghi rõ |
| P1 — quan sát ổn định | Hoàn tất phần code, chưa nghiệm thu production | 13 source available, CPI stale, 4 placeholder disabled; đã có freshness theo phiên/lịch nghỉ, retry/backoff/jitter, circuit breaker, queue age và log rotation. Còn chọn danh mục thật, xử lý CPI/điểm mù và soak/restart/mất mạng trên tiến trình thật |
| P2 — Quant Lab | Hoàn tất hạ tầng, chưa có rule được chứng nhận | Có dataset builder/manifest/feature registry, walk-forward/embargo/bootstrap, certificate store, lifecycle và Bonferroni. `research_csv` vẫn trống, report thật = 0, toàn bộ 23 rule vẫn candidate |
| P3 — đội Swarm | Preset và executor đã có, chưa nghiệm thu AI live | Watch có 6 agent/task; Research có 7 agent/task; local-only evidence contract có test. Chưa chạy một DAG thật qua Ollama và đánh giá chất lượng/độ trễ; executor hiện chạy tuần tự |
| P4 — Fincept | Chỉ có contract tích hợp | REST/SSE/ack và TypeScript client đã có; chưa có checkout Fincept trong workspace, chưa có màn hình native hay kiểm thử E2E desktop |
| P5 — shadow/golive | Chưa bắt đầu | Monitor offline, chưa có token runtime, danh mục chưa cấu hình, chưa chạy 20 phiên |

Mức sẵn sàng: backend quan sát thử nghiệm có thể khởi chạy local; chưa đủ điều kiện gọi là monitor production trên Fincept.

## Trạng thái kỹ thuật đã xác minh

- Project venv: `vnstock 4.0.7`, `vnstock_data 3.2.8`, `vnai 2.5.9`.
- Auth state đã tái xác nhận: tài khoản `silver`; `show_api()` và `show_doc("Market.equity")` chạy thành công trong project venv. Không query source trong bước discovery.
- Đã thử `vnstock_data 3.2.9`, nhưng BCTC VCB lỗi ở route mặc định và KBS; đã rollback 3.2.8. Không tự nâng lại trước khi regression test BCTC thành công.
- Ollama đang chạy và có `qwen2.5:3b-16k`, đúng model trong config.
- Monitor báo `offline`, không có heartbeat. `.third-eyes/access-token` chưa tồn tại.
- Portfolio: `not_configured`, positions rỗng. `watchlist` rỗng và `excel_directory` chưa đặt.
- Store hiện có 1 signal Radar, 1 event, 18 feature registration, 23 rule candidate và 0 research certificate. Không coi signal này là tín hiệu đầu tư đã kiểm định.
- Inventory: 13 available, 1 stale (`vn_cpi` mới nhất 30/06/2026), 4 disabled.
- Test Python: 32 passed, 2 warning thư viện phụ thuộc. Test mới bao phủ lịch phiên, retry/jitter/circuit, queue age/job restart, log rotation, dataset PIT, multiple testing, certificate và lifecycle.
- Test TypeScript client: 2 passed bằng Node 26 với `--experimental-strip-types`. `node_modules` chưa cài nên `npm test` chưa chạy được.

## File cần bảo toàn

- `agent/src/third_eyes/`
  - P2 thêm `datasets.py`; không tách file này khỏi package khi bảo toàn.
- `agent/src/swarm/presets/third_eyes_watch.yaml`
- `agent/src/swarm/presets/third_eyes_research.yaml`
- `agent/tests/test_third_eyes.py`
- `agent/tests/test_third_eyes_inventory.py`
- `agent/scripts/verify_third_eyes_sources.py`
- `agent/scripts/update_third_eyes_vnstock.py`
- `agent/scripts/restore_third_eyes_vnstock.py`
- `frontend/src/lib/thirdEyes.ts`
- `frontend/src/lib/thirdEyes.test.mjs`
- `scripts/start-third-eyes.ps1`
- `docs/third-eyes*.md`
- Tracked wiring liên quan: `agent/api_server.py`, `agent/src/swarm/subprocess_worker.py`, `agent/src/tools/swarm_tool.py`, các test/preset packaging liên quan và `pyproject.toml`.
- Local/private: `third-eyes.json`, `.third-eyes/`. Không commit credential, token, portfolio hoặc snapshot riêng tư.

## Đường đi ngắn nhất đến go-live Fincept

### Gate 1 — bảo toàn và tái xác thực

1. Kiểm tra lại `git status`; tạo commit riêng chỉ chứa mã/tài liệu/test Third Eyes sau khi review phần wiring tracked. Không gom dữ liệu nghiên cứu riêng vào commit.
2. Đăng nhập tài khoản vnstock mới, đọc tier từ auth state và chạy `show_api()`/`show_doc()` trong project venv. Yêu cầu tối thiểu hiện tại là quyền dùng `vnstock_data`; news cần tier phù hợp.
3. Giữ project venv ở 3.2.8 cho đến khi 3.2.9 hoặc bản sau vượt qua test live BCTC VCB. Chạy `pip check` và 25 test sau mọi thay đổi package.

### Gate 2 — biến prototype thành monitor của danh mục thật

1. Chọn một trong hai nguồn danh mục: cấu hình `excel_directory` cùng token lookup nội bộ, hoặc đặt `watchlist` rõ ràng. Xóa/disable hai source `sample_vcb_*` nếu VCB không nằm trong phạm vi thật.
2. Điền lịch nghỉ giao dịch; bổ sung freshness theo phiên để phát hiện thiếu bar EOD mới nhất dù chưa vượt `max_age_seconds`.
3. Thêm retry/backoff/jitter, giới hạn lỗi liên tiếp, queue-age metric và log rotation. Chạy restart/gián đoạn mạng thật để xác minh job store, lease và SSE cursor.
4. Xử lý CPI stale bằng nguồn được xác minh hoặc giữ disabled/stale; không nới tuổi dữ liệu để che khoảng thiếu. Quyết định có bật các placeholder USD/policy rate/disclosure hay hiển thị rõ điểm mù.

Trạng thái 14/09/2026: mục 2–3 đã hoàn tất ở mức code/test. `third-eyes.json` đã có lịch nghỉ 2026 theo thông báo HNX, gồm 02/01 điều chỉnh; Saturday làm bù vẫn không phải phiên. Mục 1 và 4 cần quyết định phạm vi danh mục/nguồn của người dùng. Chưa chạy monitor production; test mất mạng/restart hiện là mô phỏng cô lập.

### Gate 3 — kiểm định signal

1. Xây research CSV point-in-time cho các rule ưu tiên: VNINDEX breadth/liquidity, interbank ON, sector strength và indicator doanh nghiệp danh mục.
2. Chạy backtest 1/5/20 phiên, lưu certificate; bổ sung registry `candidate → shadow → validated → retired` và kiểm soát multiple testing.
3. Giữ mọi rule chưa đạt ở Radar. Chỉ Priority khi certificate hợp lệ và có xác nhận độc lập theo contract hiện tại.

Trạng thái 14/09/2026: hạ tầng của mục 1–3 đã triển khai. Dataset builder giữ cadence phiên và chỉ đánh dấu ngày vintage mới là `event_eligible`; synthetic không được chứng nhận. Registry bắt buộc chuyển có lý do và không cho nhảy `candidate → validated`. Chưa có dữ liệu PIT thật nên không tạo certificate giả và không nâng rule.

### Gate 4 — nghiệm thu Swarm thật

1. Tạo một signal kiểm thử có evidence hợp lệ rồi chạy `third_eyes_watch` qua Ollama thật.
2. Xác minh output tiếng Việt, evidence ID, mâu thuẫn, giới hạn và thời gian toàn DAG; lỗi AI không được chặn signal định lượng.
3. Bổ sung routing chỉ gọi agent đúng domain để giảm độ trễ trước khi mở rộng universe.

### Gate 5 — tích hợp Fincept

1. Đưa checkout/version Fincept Terminal vào workspace hoặc cung cấp đường dẫn repo. Xác định framework desktop, backend ownership và cách lưu secret.
2. Tích hợp `ThirdEyesClient`: health, inventory/coverage, signals, detail/evidence, ack và SSE reconnect bằng cursor bền vững.
3. Đồng bộ schema còn thiếu trong TypeScript như `feature_value`, `threshold_unit` và inventory. Hiện bốn domain, stale/gap, Radar/Priority và portfolio exposure.
4. Dùng Bearer header; không đặt token trong URL/localStorage hoặc bật CORS wildcard. Test mất mạng, restart backend, replay trùng và token sai.

### Gate 6 — vận hành Windows và shadow

1. Tạo token runtime và chạy monitor bằng `scripts/start-third-eyes.ps1`; xác minh heartbeat, source schedules, Ollama và dashboard local.
2. Sau smoke test thủ công, đóng gói thành Windows Task Scheduler/service tự khởi động, auto-restart, working directory cố định và tài khoản có quyền đọc DataPro/danh mục.
3. Chạy shadow ít nhất 20 phiên. Ghi coverage, freshness, downtime, detection latency, AI latency/failure, duplicate/missed signal, Radar/Priority và phản hồi người dùng.
4. Chỉ công bố go-live khi Fincept E2E đạt, không mất sự kiện qua restart, nguồn danh mục thật hoạt động, các điểm mù hiển thị và có runbook rollback.

## Lệnh kiểm tra lại cho tài khoản mới

Từ repo root:

```powershell
& .\.venv\Scripts\python.exe -c "from importlib.metadata import version; print({p:version(p) for p in ['vnstock','vnstock_data','vnai']})"
Push-Location agent
& ..\.venv\Scripts\python.exe -m src.third_eyes --config ..\third-eyes.json inventory
& ..\.venv\Scripts\python.exe -m pytest tests/test_third_eyes.py tests/test_third_eyes_inventory.py -q --basetemp=..\.third-eyes-handoff-tests -p no:cacheprovider
Pop-Location
node --experimental-strip-types --test frontend/src/lib/thirdEyes.test.mjs
```

Không chạy source verification toàn bộ hoặc bật monitor trước khi tài khoản vnstock mới xác thực thành công. Khi cần kiểm tra một nguồn, dùng `scan --source ID` hoặc `verify_third_eyes_sources.py --source ID` để giới hạn tác động.

## Prompt tiếp tục gợi ý

> Đọc `THIRD_EYES_HANDOFF.md` và `docs/third-eyes-architecture.md`. Bảo toàn mọi file Third Eyes untracked, không chạy git clean/reset. Kiểm tra tier vnstock của tài khoản mới và project venv, sau đó tiếp tục Gate 1 rồi Gate 2. Mục tiêu là go-live Third Eyes trên checkout Fincept thật; không bật monitor production trước khi hoàn thành các gate được ghi trong handoff.
