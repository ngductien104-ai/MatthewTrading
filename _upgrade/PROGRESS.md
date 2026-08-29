# Nâng cấp hệ thống nghiên cứu tự học — Tiến độ

**Kế hoạch đầy đủ:** `~/.claude/plans/anh-c-n-em-xem-enumerated-finch.md`
**Cách nối lại khi hết quota:** `claude --continue` trong thư mục repo. Nếu mất phiên,
mở phiên mới và gõ: *"đọc `_upgrade/PROGRESS.md` + kế hoạch trong `~/.claude/plans/`, tiếp tục từ mục chưa tick"*.

**Quy ước:** mỗi mục = một commit riêng. Không để trạng thái nửa vời qua đêm.
**Trình thông dịch:** `C:\Users\VVVZV\MatthewTrading\.venv\Scripts\python.exe` (venv này có pytest;
`$HOME\.venv` thì **không** có pytest nhưng có trọn bộ gói tài trợ).

---

## 🔖 ĐIỂM DỪNG — 29/08/2026, tối

**Nhánh:** `upgrade/learning-loop`, **chưa push**, cây làm việc sạch.

**Đã xong:** 1.1 `records.py` · 1.2 `transcript.py` · 1.3 `store.py` · 1.4 `extract.py`
**158 test learning xanh** (49 + 25 + 32 + 52).

**Món nợ 1.3 đã trả.** Full suite chạy lại đầu phiên ra **đúng** con số dự kiến:

| Mốc | passed | failed | errors |
|---|---|---|---|
| baseline sau G0 | 3142 | 11 | 9 |
| + 1.1 `records.py` (49 test) | 3191 | 11 | 9 |
| + 1.2 `transcript.py` (25 test) | 3216 | 11 | 9 |
| + 1.3 `store.py` (32 test) — **đã đối chiếu 29/08** | **3248** | 11 | 9 |
| + 1.4 `extract.py` (52 test) | 3300 | 11 | 9 |

Fail/error không đổi một cái nào so với danh sách ở mục "Mốc test baseline".

**Mục kế tiếp: 1.5 — hook cuối phiên Claude Code.** Cần biết trước khi bắt đầu:
- `.claude/settings.json` hiện **chỉ** có `PreToolUse` matcher `Skill`, và `check-gstack.sh`
  trả `{}` — tức là **chưa bắt được gì**. Phải thêm hook cuối phiên thật.
- Đường ống đã đủ để hook gọi: `parse_transcript()` → `extract_document(doc, propose)` →
  `store_result(store, result)`. Thiếu đúng hai mảnh: **ai đóng vai `propose`** (xem quyết
  định 2 ở mục 1.4 — provider chưa ngã ngũ) và **một integration test chạy trên phiên thật**.
- `resolve.py` vẫn hoãn sang Giai đoạn 2, theo phản biện Codex.

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
    `<repo private, xem memory>` — **917 file, nhánh `master`**.
    ⚠️ Repo này lúc đầu bị tạo nhầm thành PUBLIC; đã kiểm bằng API ẩn danh
    (`"private": false`) và **từ chối push**, chờ đổi sang private rồi kiểm lại
    (HTTP 404 + `ls-remote` ẩn danh không thấy ref) mới đẩy.
    **Quy tắc: trước mỗi lần push kho này, xác minh bằng
    `curl -s -o /dev/null -w "%{http_code}" https://api.github.com/repos/<owner>/<repo-private>`
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

## Đính chính đã phát hiện trong quá trình làm (đọc trước khi tiếp)

1. **Provider thật là DeepSeek, không phải openai-codex.** Có **hai** file `.env` và
   `~/.vibe-trading/.env` **thắng** `agent/.env` (`src/providers/llm.py:247-251`, lấy file
   đầu tiên rồi `break`). File thắng đặt `LANGCHAIN_PROVIDER=deepseek`.
   API `/user/balance` trả **`is_available: false`, số dư $0.00** → đây mới là nguồn của
   31 lỗi `402 Insufficient Balance` (đúng định dạng lỗi DeepSeek).
   `_run_fpt.py` gọi `load_dotenv(agent/.env)` thẳng nên đường đó lại dùng openai-codex —
   **hai đường chạy, hai provider khác nhau.** Đã xoá `OPENROUTER_API_KEY/BASE_URL` khỏi
   `agent/.env` (sao lưu ra `~/.vibe-trading/env-backups/`, ngoài repo).
   → **Việc cần làm:** chốt MỘT provider ở `~/.vibe-trading/.env`, hoặc nạp tiền DeepSeek.

2. **Transcript có lỗ hổng 47 ngày: 12/06 → 29/07.** Nghiên cứu PET 18/06, LPB 23/06,
   TPB→HDB 29/06, PHR 30/06, macro forum 20/07, sector rotation 21/07, **MWG 24/07** đều
   rơi vào đó. Backfill `ProcessRecord` chỉ làm được cho phần có transcript;
   `CallRecord` cho phần còn lại phải lấy từ markdown trong `_*` (mtime + nội dung).

3. **Transcript không chứa sidechain** (0 event) → phần suy luận của subagent không được lưu.

4. **Hook hiện có KHÔNG bắt được gì** — `.claude/settings.json` chỉ khớp `PreToolUse`
   matcher `Skill`, và `check-gstack.sh` chỉ trả `{}`. Cần hook cuối phiên thật sự.

## Giai đoạn 1 — Sổ cái quyết định *(đang làm)*

Thứ tự đã chốt sau phản biện Codex lượt hai:

### ✅ Hai quyết định anh đã chốt 28/08 — dùng luôn, KHÔNG hỏi lại

- **Giá tham chiếu (`ref_price`) = giá ĐÓNG CỬA của ngày ra nhận định.**
  Không dùng giá mở cửa phiên kế tiếp, không dùng giá lúc phát ngôn.
- **Horizon mặc định khi call không ghi rõ = 3 tháng ≈ 63 phiên giao dịch.**
  Đếm theo phiên giao dịch VN, không theo ngày lịch (lý do: `deadline` rơi vào
  cuối tuần/nghỉ lễ thì sai — xem mục 1.1). Call có ghi rõ deadline thì dùng của nó.

- [x] **1.1 `records.py` TRƯỚC TIÊN** — đóng băng hợp đồng dữ liệu:
  - `agent/src/learning/{__init__,records}.py` + `agent/tests/test_learning_records.py`
    (**49 test, xanh hết**). Năm dataclass: `Evidence`, `CallRecord`, `ProcessRecord`,
    `Outcome`, `Lesson` — thuần validate, chưa đụng lưu trữ.
  - **Bốn chỗ em đi lệch kế hoạch, có lý do:**
    1. `horizon_days` → **`horizon_sessions`** (mặc định 63). Giữ tên cũ là mời gọi
       đúng cái bẫy ngày lịch mà anh đã chốt bỏ.
    2. **`deadline` là trường DẪN XUẤT, để rỗng cho tới khi lịch giao dịch chạm tới.**
       Hệ quả trực tiếp của quyết định "đếm theo phiên": một call ra hôm nay, horizon 63
       phiên, thì ngày tới hạn **chưa tồn tại** — chưa ai biết phiên thứ 63 rơi vào ngày nào.
       `resolve_deadline()` trả `None` trong trường hợp đó thay vì bịa một ngày lịch.
       Câu hỏi "call này tới hạn chưa" trả lời bằng `sessions_between()`, không bằng ngày.
    3. Kế hoạch ghi hai trường song song `errors_caught[]` + `error_taxonomy[]`. Em gộp
       còn **một** trường `errors_caught[]` (mỗi mục bắt buộc có `code` + `evidence_id`),
       `error_taxonomy` thành property dẫn xuất. Hai trường song song thì sẽ lệch nhau.
    4. Thêm dataclass **`Evidence`** — kế hoạch không liệt kê, nhưng cổng chống hindsight
       "áp theo provenance từng bằng chứng" **không thể** thực hiện nếu bằng chứng chỉ là
       một chuỗi id. `assert_no_hindsight(wall, evidences)` so `observed_at` của TỪNG mục
       với `known_at` của record.
  - **Các cổng đã cắm vào chính dataclass** (không chờ tới store):
    - `confidence` là phân số `[0,1]`; ghi `61` thay vì `0.61` → **raise**, kèm thông báo
      chỉ đúng lỗi đơn vị.
    - `verdict != "open"` bắt buộc có `resolved_price` **và** `evidence_ids` — mô hình
      không được tự khai "hit". (Đây là tinh thần cổng bằng chứng của `goal/store.py`,
      viết lại cho đúng ngữ nghĩa Outcome, không bê nguyên.)
    - Bài học không có `evidence_ids` bị **ép** về `provisional` + tự đặt hạn 90 ngày;
      `confirmed` mà rỗng bằng chứng → raise.
    - `known_at < as_of` → raise.
    - Từ vựng action đóng, có bảng ánh xạ tiếng Việt thật đang dùng (`TÍCH LŨY`,
      `MUA THEO ĐỢT`, `TRUNG LẬP`, `không đuổi`…). Chữ lạ → **raise**, không đoán.
  - **`call_id` cố tình KHÔNG chứa `parser_version`**: đổi parser phải rơi trúng cùng
    `call_id` để store nhận ra là cùng một quan sát; nội dung đổi thì đó là bản mới
    `supersedes` bản cũ, không phải quan sát thứ hai.
  - Test neo vào dữ liệu thật: episode FPT 27/08 (93.000 → 69.500 → 59.000 → 58.800) =
    **1 episode, 4 revision**; `latest_revision(cutoff=...)` không bao giờ chấm một
    revision chưa tồn tại. Có test lỗ hổng Tết chứng minh cộng ngày lịch ra sai phiên.
  - Hợp đồng gốc, giữ nguyên để đối chiếu:
  - **Đơn vị quan sát: `episode` chứa nhiều `revision`.** Phiên FPT (93.000 → 69.500 →
    59.000 → 58.800) là **1 quan sát, không phải 4** — đếm thành 4 là pseudo-replication,
    thổi phồng n và làm sai khoảng tin cậy. Khoá `(session_id, ticker, thesis_episode)`.
    Điểm dự báo chính = **revision cuối còn hiệu lực trước cutoff**; các revision trước
    dùng riêng để đo trôi dạt hiệu chỉnh.
  - Provenance là `source_session_id` + `source_uuid` + hash sự kiện gốc — **KHÔNG phải
    `source_commit`**: transcript nằm ngoài repo nên commit không chứng minh được gì.
  - `deadline` tính theo **phiên giao dịch**, không phải `known_at + horizon_days`
    (rơi vào cuối tuần/nghỉ lễ). Chốt rõ giá tham chiếu: close / next open / giá lúc phát ngôn.
  - Cổng chống hindsight áp theo **provenance từng bằng chứng**, không chỉ timestamp record.
- [x] **1.2 `transcript.py`** — parser + golden fixture. **25 test xanh**, gồm một test
  chạy thẳng trên 20 transcript thật (không skip).
  - **Đo lại toàn corpus trước khi viết một dòng code** (20 file, 39,5 MB):

    | Bẫy | Số thật |
    |---|---|
    | `tool_result` **không** nằm ở dòng kế tiếp | **648 / 1.946** — ghép theo dòng gán nhầm **1/3** bằng chứng |
    | `tool_use` không có kết quả (bị ngắt) | **4** (đúng ghi chú cũ) |
    | Sự kiện sidechain | **0** — suy luận subagent không hề được ghi |
    | Dòng JSON hỏng | 0 |
    | `parentUuid` trỏ hụt | 0 · mỗi file đúng 1 gốc, 1 `sessionId` |

  - **Phát hiện mới, kế hoạch chưa lường: timestamp CHẠY LÙI — 36 lần.** Phần lớn là
    jitter dưới giây, nhưng có **3 lần lùi hẳn ~120 giây** (file `73b3e10f`). Hệ quả:
    thứ tự dòng mới là sự thật, timestamp chỉ là tham khảo. Nên mỗi sự kiện mang **hai**
    mốc: `timestamp` (nguyên trạng) và **`observed_at` = max luỹ tiến** theo thứ tự dòng.
    **Tường chống hindsight phải dùng `observed_at`** — dùng `timestamp` thô thì riêng
    jitter đồng hồ đã đủ tố oan một bằng chứng vốn đứng trước.
  - Ghép tool **chỉ** bằng `tool_use.id ↔ tool_result.tool_use_id`. `misordered_tool_calls()`
    và `unresolved_tool_calls()` phơi ra đúng các ca mà parser theo vị trí sẽ làm hỏng.
  - Kiểu sự kiện lạ **không bị nuốt** — vào `Transcript.unknown_types` và test corpus thật
    sẽ đỏ khi harness đổi định dạng. 13 kiểu bookkeeping liệt kê tường minh, không lọc ngầm.
  - `thinking` bị loại khỏi `text` nhưng gắn cờ `has_thinking`: đó là nháp của model,
    không phải điều đã nói ra; cho backfill trích dẫn nó là bịa lại luận điểm.
  - ⚠️ **Fixture dựng tay, KHÔNG cắt từ transcript thật** — repo public, transcript có
    dữ liệu nghiên cứu khách hàng. `agent/tests/fixtures/transcript_golden.jsonl` tái tạo
    đủ 7 bẫy đã đo (song song, lệch thứ tự, lùi giờ, bị ngắt, thinking, kiểu lạ, đuôi cụt).
    Test corpus thật kiểm **bất biến**, không kiểm con số cứng, để không mục theo thời gian.
  - **Trần của backfill, phải nói thẳng:** 0 sidechain nghĩa là `ProcessRecord` dựng từ
    transcript chỉ thấy góc nhìn của người điều phối, không thấy lập luận subagent.
- [x] **1.3 `store.py`** — sổ cái SQLite append-only. **32 test xanh.**
  - **Append-only cưỡng chế bằng TRIGGER SQL, không bằng quy ước.** Mỗi bảng có
    `seq` tự tăng làm khoá; id của record chỉ là cột thường. Ghi lại = **thêm dòng**,
    `seq` cao nhất thắng, bản cũ đọc được vĩnh viễn. `BEFORE UPDATE` / `BEFORE DELETE`
    trên cả 5 bảng đều `RAISE(ABORT)`. Đây là thuốc chữa trực tiếp cho bệnh `Home.md`:
    một caller sau này **không thể** vô tình tái lập lỗi ghi đè.
    (Test seed đủ 5 bảng rồi mới thử UPDATE/DELETE — trigger cấp dòng không bắn trên
    bảng rỗng, test bỏ qua chỗ này thì chứng minh được số không.)
  - **Idempotency theo NỘI DUNG**: unique index `(record_id, content_hash)`.
    Chạy lại backfill trên transcript không đổi → chèn 0 dòng, audit ghi
    `duplicate_ignored`. Parser tốt lên làm đổi nội dung → thêm **phiên bản mới của cùng
    một quan sát**, không đẻ quan sát thứ hai. Đây chính là lý do `call_id` không chứa
    `parser_version`.
  - **Cổng bằng chứng cưỡng chế lúc GHI**: call/outcome trích `evidence_id` mà sổ cái
    chưa từng thấy → `LedgerError`; bằng chứng đã có thì kiểm tường hindsight ngay.
    Ghi call trước rồi bằng chứng sau sẽ để tường không được kiểm, nên **ép thứ tự**
    thay vì tin. Có `append_call_with_evidence()` làm đúng thứ tự đó.
  - ⚠️ Đúng như cảnh báo: **không** bê `_validate_completion_audit` của `goal/store.py:894`.
    Nó gác việc *hoàn tất goal*, ngữ nghĩa khác, và không chứng minh gì về append-only.
    Chỉ mượn lại WAL + `RLock`/`_synchronized` + `PRAGMA user_version`.
  - Migration: `PRAGMA user_version`, `SCHEMA_VERSION = 1`. DB cũ chưa đóng dấu → nâng
    tại chỗ, **không đụng bảng lạ có sẵn**. DB đóng dấu **cao hơn** build hiện tại →
    `LedgerError`, từ chối mở, thà không ghi còn hơn ghi ra dòng mà bản mới đọc sai.
- [x] **1.4 `extract.py`** — LLM trích, **code chốt**. **52 test xanh** (gồm 1 test chạy
  thẳng trên corpus thật 229 file / 4,3 MB, không skip).
  - **Đo corpus trước khi viết code** (229 file markdown trong `_*`, 4,3 MB):

    | Cách viết số | Số hit |
    |---|---|
    | `%` | 18.040 |
    | nghìn chấm (`72.200`) | 12.130 |
    | dải giá `A–B` | 5.510 |
    | `tỷ` | 3.167 |
    | ngày `dd/mm/yy` | 2.126 |
    | hậu tố `đ / đồng / VND` | 1.510 |
    | hậu tố `k` (`94k`) | 441 |

    Và: **chỉ 3/18 `run.json` có `final_report` khác rỗng** (9.351 / 10.404 / 14.739 ký tự);
    15 file còn lại rỗng → bỏ qua, không đưa vào extractor như tài liệu trắng.
  - **Ranh giới người/máy đặt ở đâu:** model được nói *call nằm ở đâu* (mã, ngày, hành động,
    và **trích dẫn nguyên văn** cho MỌI con số nó khai). Model **không** được nói *con số là bao
    nhiêu* — mọi giá được đọc lại từ chính đoạn trích bằng `parse_prices()`, khai mà không tìm
    thấy trong trích dẫn của chính mình → **từ chối**, không sửa hộ.
  - **Bẫy nghìn — chỗ khó nhất, và là lý do module này tồn tại.** Cùng một tài liệu viết
    `72.200 đ`, `58,8k`, `25.000` **và** `vùng 64–65` / `stop dưới 60`. Đọc `64` thành 64 đồng
    hay lặng lẽ nhân 1.000 đều làm hỏng sổ cái (target lệch 1.000 lần chấm ra "miss thảm hoạ"
    trông y như miss thật). `resolve_scale()` **chỉ nhân khi phép chia chứng minh được**: so cả
    hai cách đọc với `ref_price`; đúng một cách lọt dải `[0,2 ; 5,0]` thì lấy cách đó, cả hai
    hoặc không cách nào lọt → **raise**. Không có `ref_price` để làm thước → cũng raise, chứ
    không lưu 60 đồng.
  - `ref_price` là thước đo của mọi giá khác nên là số **duy nhất không được suy ra**: viết trần
    (`61,5`) thì chỉ được chấp nhận khi trong trích dẫn có một token neo đúng bằng 1.000 lần.
  - **Dải giá vouch cho trung điểm của chính nó** — `22.000–27.500` đủ chứng cho target 24.750,
    và dải gốc được ghi nguyên văn vào `notes` để còn kiểm lại được.
  - `locator` (`L3-L3`) **do code tính bằng `str.find`**, không lấy offset model khai:
    offset model đưa là một lời quả quyết, offset tìm được là một sự thật.
  - Cổng đã cắm: thiếu `ticker`/`as_of`/`action` → từ chối; thiếu `target`/`confidence` → nhận,
    `incomplete`; hành động ngoài từ vựng → raise (`BÁN / TRÁNH MUA ĐUỔI` buộc phải chọn một);
    `as_of` sau mtime tài liệu → `future_dated`; target > 5× hoặc < 0,2× `ref_price` → lỗi đơn vị;
    `confidence: 61%` khai thành `61` → chết ở cổng phân số của `records.py`.
  - Số trong ngày tháng bị gắn nhãn `date`, `tỷ` → `billion`, `%` → `percent`: `2026` trong
    `27/08/2026` **không được phép** làm chứng cho một mức chỉ số bịa.
  - **Ba quyết định em tự chốt, có lý do:**
    1. **Khoá episode cho nguồn ngoài transcript = thư mục chứa** (`_fpt_research`, hoặc run id
       của swarm), còn `source_session_id` **để rỗng**. Nhét khoá thư mục vào trường session là
       nói dối về ngữ nghĩa trường đó; mà để rỗng thì `episode_id_for()` gộp mọi call FPT mọi
       thời điểm vào **một** episode — nên khoá phải đi đường riêng.
    2. **`propose` là tham số tiêm vào, không nối provider.** Provider của repo còn chưa ngã ngũ
       (hai file `.env` đá nhau, DeepSeek số dư $0 — xem mục Đính chính 1), và backfill phải
       dựng lại được từ câu trả lời đã lưu. Ai gọi cũng được: subagent Claude, hay một reply
       chép tay.
    3. **`assign_revisions()`** đánh lại số revision trong từng episode + nối `supersedes`.
       Vệt FPT 93.000 → 69.500 → 59.000 → 58.800 nằm rải nhiều file; không đánh số thì
       `latest_revision()` không biết đâu là điểm chấm. Bản gốc **không bị sửa** (sổ cái
       append-only) — hàm trả về record mới.
  - Một tài liệu hỏng **không** làm gãy backfill: reply không phải JSON → một `Rejection`
    mã `bad_json`, không raise. 10 mã từ chối là từ vựng đóng, đếm được như `ERROR_TAXONOMY`.
- [ ] ~~`resolve.py`~~ — **hoãn sang Giai đoạn 2** (Codex đúng): resolver kéo theo lịch giao dịch,
  sự kiện doanh nghiệp, phiên bản dữ liệu, và dễ che lỗi dataset bằng một outcome đẹp mắt.
  Làm xong capture/backfill/dedupe/audit rồi mới chấm điểm.
- [ ] **1.5 Hook cuối phiên Claude Code** + integration test chạy một phiên thật.
## Giai đoạn 2 — PIT + backtest cứng *(chưa bắt đầu)*
## Giai đoạn 3 — Playbook + vòng lặp tự động *(chưa bắt đầu)*
