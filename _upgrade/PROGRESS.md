# Nâng cấp hệ thống nghiên cứu tự học — Tiến độ

**Kế hoạch đầy đủ:** `~/.claude/plans/anh-c-n-em-xem-enumerated-finch.md`
**Cách nối lại khi hết quota:** `claude --continue` trong thư mục repo. Nếu mất phiên,
mở phiên mới và gõ: *"đọc `_upgrade/PROGRESS.md` + kế hoạch trong `~/.claude/plans/`, tiếp tục từ mục chưa tick"*.

**Quy ước:** mỗi mục = một commit riêng. Không để trạng thái nửa vời qua đêm.
**Trình thông dịch:** `C:\Users\VVVZV\MatthewTrading\.venv\Scripts\python.exe` (venv này có pytest;
`$HOME\.venv` thì **không** có pytest nhưng có trọn bộ gói tài trợ).

---

## 🔖 ĐIỂM DỪNG — 30/08/2026 (Claude điều phối, Codex thực thi — hết hàng đợi Q1–Q8)

**Nhánh:** `upgrade/learning-loop`. **9 commit mới, CHƯA PUSH** (`96409bc` → `f36345b`).
Cây làm việc sạch. **Full suite `11 failed, 3399 passed, 1 skipped, 9 errors`** — fail/error
khớp baseline từng cái; passed đi từ **3350 → 3399** (+49) qua 8 mục.

**Sổ cái `~/.vibe-trading/learning.db`: `calls=15`** (11 → 13 nhờ Q2 mở khoá memo TPB/HDB,
13 → 15 nhờ Q1 hỏi lại VRE + PET). `outcomes=0`, `lessons=0` — chưa có gì để chấm cho tới
khi làm `resolve.py`.

**Giai đoạn 2.2 xong phần làm được trong sandbox.** Còn **Q9** (chính sách điều chỉnh giá +
đối chiếu DataPro ↔ vnstock_data) **bị chặn bởi môi trường**, không phải bởi thiếu người làm.

### Việc kế tiếp
1. **Push 9 commit** — repo PUBLIC, liếc `_upgrade/PROGRESS.md` một lượt trước (đã cắt khuyến
   nghị sống ở `63bbfbd` theo tiền lệ `0c24536`).
2. **Q9** — cần máy có **DataPro desktop mở** và **mạng tới `vnstocks.com`**. Đây cũng là phép
   đo duy nhất trả lời được đơn vị thật của `vnstock_data` mà Q7 phải để ngỏ.
3. **MWG vào sổ** — Q3 mở đường vào HTML nhưng `_mwg_research` chưa có call nào. Cần một reply
   do Claude đóng vai model (không tốn token provider).
4. **Câu hỏi treo cần anh quyết** (chi tiết ở Q7): schema hỏng ở **một** mã nay giết **cả** lần
   chạy. Giữ nguyên, hay bỏ qua theo mã rồi ghi vào run card như Q6 làm với survivorship bias?
5. Rồi sang **2.1** (walk-forward, CPCV, DSR, PBO) — nay đã đứng trên nền dữ liệu sạch hơn,
   đúng thứ tự kế hoạch đã đảo.

### Ba việc môi trường, không phải việc code
- **5 thư mục pytest rỗng KẸT VĨNH VIỄN** trong `_upgrade/` (`q4_pytest_tmp`, `q5_pytest_tmp`,
  `q6_pytest_tmp{,_targeted,_targeted2}`). ACL chặn tới mức `icacls` **đọc** cũng bị từ chối;
  `takeown`, `robocopy /MIR` đều thất bại. Git không commit thư mục rỗng nên **không lọt lên
  repo public**, chỉ làm `git status` in warning. Cần shell quyền cao hơn. Luật 8 đã chặn việc đẻ thêm.
- **`/codex:transfer` HỎNG** ở codex-cli 0.150.1: báo "import completed" nhưng không ghi thread
  nào, cả khi truyền `--source` đúng đường dẫn. Bàn giao ngữ cảnh đi bằng chính file này.
- **Provider LLM vẫn chết** (DeepSeek $0 — xem Đính chính 1). Mọi việc trên đây làm được là vì
  không mục nào cần gọi model: reply backfill có sẵn trên đĩa, còn Claude tự đóng vai extractor.

### Điều đáng giá nhất rút ra từ vòng này

**Ba mục đầu (Q2, Q3, Q4) đều bị trả lại, và cả ba lần Codex đã nộp với test xanh cùng báo cáo
tự tin.** Không lần nào test của nó bắt được lỗi — vì test do chính nó viết, cho ca chính nó
nghĩ tới. Thứ bắt được là **chạy bản vá lên dữ liệu thật của repo rồi hỏi "code cũ có xử lý ca
này khác không"**:
- Q2: cổng action nhận `"Ban lãnh đạo"` thành lệnh `sell` — code cũ từ chối 5/6 ca đó.
- Q3: mở HTML cho cả 17 thư mục → ghi quyết định TPB/HDB **hai lần**, hai action mâu thuẫn.
- Q4: test chỉ phát biểu lại `5-4=1`, đỏ vì đổi chữ ký hàm chứ không vì đổi hành vi.

Sau khi câu hỏi đó vào brief, **Q5–Q8 chỉ còn một lượt trả lại duy nhất, và là vì chẩn đoán
chứ không vì logic**. Đây là luật 7 và 8 của luồng — giữ chúng.

---

## 🔖 ĐIỂM DỪNG trước đó — 29/08/2026, khuya (backfill vòng 2 xong)


**Nhánh:** `upgrade/learning-loop`, **đã push tới `0c24536`**; sau đó còn 3 commit chưa push.
**208 test learning xanh.** Cây làm việc sạch.
**Full suite đã đối chiếu: `11 failed, 3350 passed, 1 skipped, 9 errors`** — fail/error
không đổi một cái nào so với baseline. Hết nợ đối chiếu.

### Sổ cái thật `~/.vibe-trading/learning.db`

`process_records=21` · **`calls=11`** · `evidence=46` · outcomes=0 · lessons=0

| Mã | Ngày | Action | Giá tham chiếu | Mục tiêu | Upside | Conf |
|---|---|---|---|---:|---:|---|
| HAH | 15/06 | neutral | 54.500 | 57.400 | +5,3% | — |
| BSR | 17/06 | wait | 26.350 | 24.000 | −8,9% | 0,75 |
| PHP | 17/06 | wait | 38.700 | 37.000 | −4,4% | 0,78 |
| SBT | 18/06 | wait | 21.300 | 19.500 | −8,5% | 0,80 |
| PHR | 30/06 | accumulate | 62.000 | 72.000 | +16,1% | 0,61 |
| VCB ACB MBB HDB | 21/07 | hold | — | — | — | — |
| STB | 21/07 | avoid | — | — | — | — |
| FPT | 27/08 | reduce | 72.200 | 58.800 | −18,6% | — |

### Ba lỗi CỦA EM mà vòng backfill này moi ra (đã sửa hết)

1. **Từ vựng action thiếu chữ mà bàn giao dịch thật sự viết.** Grep corpus theo dấu
   "Khuyến nghị/Kết luận" lòi ra `KHẢ QUAN`, `TĂNG TỶ TRỌNG`, `KÉM KHẢ QUAN`, `NẮM`,
   `ĐỨNG NGOÀI`, `LOẠI`, `CHỐT LỜI` — đều là từ xếp hạng chuẩn, không phải diễn giải.
   Đồng thời siết prompt: đòi **cụm ngắn**, nói thẳng "một câu sẽ bị từ chối".
2. **Corpus trộn HAI quy ước thập phân trong cùng một file.** `Giá tham chiếu **54.8**`
   nằm cách `chỉ ≤ 53,5` bốn dòng. Parser coi mọi dấu chấm là phân nhóm nghìn nên đọc
   `54.8` thành **54**. Dạng chấm-thập-phân xuất hiện **5.909 lần / 32 thư mục** — là
   quy ước, không phải lỗi đánh máy. Nay: chấm trước đúng 3 chữ số = phân nhóm; chấm
   trước 1–2 chữ số = dấu thập phân.
3. **`action` là trường DUY NHẤT model được khai mà không cần bằng chứng.** Giao một
   memo hoán đổi viết bằng tiếng Anh, extractor khai action `MUA THEO ĐỢT` — và **tự
   khai luôn** rằng nó *ánh xạ* cơ chế sang cụm gần nhất trong danh sách. Ánh xạ có thể
   đúng, nhưng đó vẫn là một khẳng định về tài liệu không hề nói thế.
   Nay `action` phải **có mặt trong chính trích dẫn của nó**, y như mọi con số.
   → 24 fixture của em đỏ, tất cả vì cùng lý do đó; đã sửa fixture, **không nới cổng**.

Ngoài ra `_anchor_price` từng quá chặt (đòi token neo **đúng bằng** ref_price×1000) nên
PHR `62,0` bị loại dù cùng call có trích `~72k`. Nay đo theo **trung vị** các giá neo
trong trích dẫn, giới hạn trong dải giá cổ phiếu hợp lý để **số lượng CP lưu hành
1.714.326.422 không bao giờ được làm thước**.

### Còn từ chối, và vì sao đó là ĐÚNG

| Tài liệu | Mã | Mã lỗi | Việc cần làm |
|---|---|---|---|
| `_switch_tpb_hdb/04_pm_decision.md` | TPB, HDB | `action_not_in_evidence` | Memo tiếng Anh, không có cụm tiếng Việt nào. Phải quyết: bổ sung từ vựng tiếng Anh vào `ACTION_ALIASES`, hay chấp nhận mất call này. |
| `_vre_committee/PM_DECISION.md` | VRE | `action_not_in_evidence` | Trích dẫn thiếu chính dòng chứa action. **Hỏi lại là lấy được** — tài liệu có cụm hợp lệ. |
| `_pet_committee/PM_DECISION.md` | PET | `scale_ambiguous` | Trích dẫn không có giá nào ghi đơn vị (chỉ EPS `2.700`). Hỏi lại, đòi trích dòng có đơn vị. |
| `_social_alpha_lpb/04_alpha_synthesis.md` | LPB | 3×`unknown_action` + 1×`scale_ambiguous` | Tài liệu sentiment, action viết dạng câu. |
| `_hpg_research/BAO_CAO_HPG_forum_bao.md` | — | (0 call) | Model tự thấy không có call nào — chấp nhận được. |

**12 file reply ở `~/.vibe-trading/backfill_replies/`** (ngoài git). Chạy lại không tốn token:
`python -m src.learning.cli extract --doc ../<doc> --reply ~/.vibe-trading/backfill_replies/<x>.json`

### Việc kế tiếp

1. Hỏi lại VRE + PET với prompt đã siết (2 call, rẻ) → sổ cái lên 13.
2. Quyết TPB/HDB: thêm alias tiếng Anh hay bỏ.
3. MWG 24/07 **không có `.md`** — chỉ HTML/PDF. Tiêu chí nghiệm thu G1 nhắc mã này nên
   cần đường khác (parse HTML) hoặc chấp nhận thiếu.
4. Rồi sang **Giai đoạn 2, làm 2.2 TRƯỚC 2.1**.

---

## 🤝 Luồng Claude ↔ Codex — mở 30/08/2026

**Vai:** Claude điều phối (đọc/ghi file này, review diff, chạy test, commit).
**Codex thực thi** (`codex exec` qua `codex-companion.mjs task --write`, sandbox workspace-write).

**Luật của luồng — Codex đọc trước khi gõ dòng nào:**
1. Mỗi mục hàng đợi có **chủ**: `[C]` = Codex viết code · `[K]` = Claude (cần phán đoán trên
   tài liệu, không giao được).
2. **Làm xong MỘT mục thì dừng.** Không tự nhảy sang mục kế, không gộp hai mục vào một diff.
3. **Codex KHÔNG commit, KHÔNG `git add`, KHÔNG push.** Để cây làm việc bẩn cho Claude review.
4. Chỉ đụng file thuộc phạm vi mục đang làm. Thấy lỗi ngoài phạm vi thì **ghi ra**, đừng sửa.
5. Test bằng `C:\Users\VVVZV\MatthewTrading\.venv\Scripts\python.exe -m pytest` (venv này
   có pytest). Mỗi mục phải kèm test **fail được trên code cũ** — không thì chưa xong.
6. Không bịa số, không nới cổng để test xanh (bài học vòng backfill 2: 24 fixture đỏ thì
   sửa fixture, không hạ chuẩn).

7. **Test xanh + báo cáo của Codex KHÔNG đủ để tick.** Với mọi thay đổi động vào một **cổng**
   hay một **đường vào dữ liệu**, Claude phải tự dựng ca đối kháng chạy trên chính hàm Codex
   viết, rồi hỏi *"code cũ có từ chối / có trả khác ca này không"*. Nới cổng luôn lộ ra dưới
   dạng "cũ nói không, mới nói có". Ba mục đầu (Q2, Q3, Q4) đều bị trả lại nhờ bước này.
8. **KHÔNG chạy pytest với `--basetemp` trỏ vào trong repo**, đặc biệt là `_upgrade/`.
   Máy này chặn ACL nên thư mục pytest tạo ra **không ai xoá được** — cả Codex, cả Claude, cả
   `takeown`/`icacls`/`robocopy`. Đã có **5 thư mục rỗng kẹt vĩnh viễn** trong `_upgrade/`
   (`q4_pytest_tmp`, `q5_pytest_tmp`, `q6_pytest_tmp{,_targeted,_targeted2}`). Chúng rỗng nên
   git không commit được, chỉ làm bẩn `git status` — nhưng đừng đẻ thêm. Dùng `--basetemp` trỏ
   ra **ngoài repo**.

**Claude sau mỗi mục:** đối chiếu full suite với baseline (`11 failed / 9 errors` cho sẵn),
tick `[x]` kèm **số đo thật**, rồi commit riêng một mục.

> ⚠️ `/codex:transfer` (bản codex-cli 0.150.1) **hỏng** trên máy này: báo "import completed"
> nhưng không ghi thread nào, cả khi truyền `--source` đúng đường dẫn. Bàn giao ngữ cảnh vì
> vậy đi bằng **chính file này** — Codex được lệnh đọc `_upgrade/PROGRESS.md` mở đầu mỗi lượt.

### Hàng đợi

- [x] **Q1 [K]** Hỏi lại VRE + PET — **sổ cái 13 → 15 call.** Claude đóng vai extractor,
      sửa **tối thiểu**: chỉ bổ sung trích dẫn còn thiếu, **không viết lại call**.
      - **VRE** `action_not_in_evidence` là bắt **đúng**, không phải cổng quá chặt: bản cũ khai
        action `KHÔNG MUA` mà 12 trích dẫn không có dòng nào chứa cụm đó. Thêm `PM_DECISION.md:437` (dòng
        "Hành động hôm nay") và `:330`. Vào sổ: `avoid`, ref 24.300, target 26.200, 14 evidence.
      - **PET** `scale_ambiguous`: bản cũ toàn số trần (`54.8`, `44–48`, `48,5`) nên
        `resolve_scale` không chứng minh nổi `54.8` là 54.800 hay 54,8. Thêm `:33` và `:22` — hai dòng
        có giá **ghi đơn vị** (`…k`), thứ mà bản cũ không có.
        Vào sổ: `wait`, ref **54.800**, và `notes` ghi lại chính suy luận đó:
        `"ref_price 54.8 read as 54800 against quoted 53000"`. Target 44.000 / bull 64.000 /
        bear 39.000 / stop 48.500, 12 evidence.
      - ⚠️ **Một chỗ Claude tự quyết, anh phủ quyết được:** VRE ghi `avoid` theo đúng tiêu đề
        *"Hành động hôm nay: KHÔNG MUA"*, giữ `target` 26.200 của kịch bản cơ sở. Kế hoạch thật (giá vào tối đa + hạn hiệu lực) nằm ở `notes`. Claude **không** đổi sang `wait` + mốc
        22.300 cho giống ba call `wait` cũ, dù dạng đó dễ chấm điểm hơn — vì đổi thế là **viết
        lại call**, không phải sửa bằng chứng. → `resolve.py` ở Giai đoạn 2 sẽ phải trả lời:
        một call `avoid` thì chấm bằng gì.
- [x] **Q2 [C]** Từ vựng action tiếng Anh trong `ACTION_ALIASES` — **xong, nhưng phải trả lại Codex một lượt.**
      - Alias thêm: `outperform`/`overweight`→buy · `accumulation`→accumulate ·
        `trim`/`underperform`/`underweight`→reduce.
      - **Lượt 1 của Codex làm CỔNG THỦNG, và nó tự báo cáo là "giữ nguyên".** Hàm
        `_action_is_quoted` tra ngược alias rồi tìm bản **đã bỏ dấu** trong trích dẫn.
        Bỏ dấu làm `bán`→`ban` đụng *"Ban lãnh đạo"*, `nắm`→`nam` đụng *"trong năm 2026"*,
        `gồm`→`gom` đụng *"bao gồm"*, `chờ`→`cho` đụng *"cho thấy"*. Claude dựng 6 ca đối
        kháng chạy thẳng trên hàm đó: **6/6 nhận sai**, trong khi code CŨ từ chối đúng 5/6.
        Một tài liệu viết *"KHÔNG ĐẶT MỘT LỆNH MUA NÀO"* chứng nhận được call `buy`.
      - Lượt 2 sửa đúng hai vế: **alias giữ nguyên dấu** (fold chỉ còn dùng để TRA action
        model viết ra, không dùng để soi trích dẫn), và **kiểm phủ định theo mệnh đề** —
        cụm khớp mà mệnh đề trước nó có `không`/`chưa`/`đừng`/`no`/`not` thì không tính là
        bằng chứng. `không mua` vẫn chứng nhận `avoid`; chữ `mua` bên trong thì không
        chứng nhận `buy`.
      - **Số đo:** 25 ca đối kháng Claude tự dựng (11 ca Codex chưa từng thấy) — **24 đúng**.
        Learning suite **208 → 228 xanh**. Full suite `11 failed, 3370 passed, 1 skipped,
        9 errors` — fail/error khớp baseline từng cái, passed +20.
      - Memo `_switch_tpb_hdb/04_pm_decision.md`: **2 rejection → 2 call** (TPB `reduce`,
        HDB `accumulate`, 18 evidence). **Sổ cái: 11 → 13 call.** Chạy `extract` ba lần
        không đẻ bản trùng — idempotency theo nội dung đứng vững.
      - ⚠️ **Hai điều còn nợ, ghi để không quên:**
        1. `trim` vẫn khớp được trong câu tiếng Việt chêm tiếng Anh (*"Nhà máy đã trim lại
           công suất"* → `reduce`). Giữ vì memo thật dùng `trim` 4 lần, nhưng đây là alias
           yếu nhất trong bảng — nó là động từ thường, không phải từ xếp hạng như `OUTPERFORM`.
        2. Memo đó thực chất viết `switch` **16 lần** — và `switch` KHÔNG có trong `ACTIONS`.
           Ghi thành TPB `reduce` + HDB `accumulate` là một **phân rã**, không phải nguyên
           văn. Nếu sau này muốn đo "call hoán đổi" như một loại riêng thì phải quay lại đây.
      - **Luật mới cho luồng, rút từ chính vụ này:** test xanh + báo cáo của Codex KHÔNG đủ
        để tick. Với mọi thay đổi động vào một **cổng**, Claude phải tự dựng ca đối kháng
        chạy trên chính hàm Codex viết, và hỏi *code cũ có từ chối ca này không*. Nới cổng
        luôn lộ ra dưới dạng "cũ nói không, mới nói có".
- [x] **Q3 [C]** Đường vào cho tài liệu **không** phải `.md` — **xong, và cũng phải trả lại một lượt.**
      - `html_to_text` viết trên `html.parser` của thư viện chuẩn, **không phụ thuộc gói ngoài**
        nên tính tất định do chính repo giữ. Giữ heading, `- ` cho list, ` | ` cho ô bảng;
        bỏ CSS/script/SVG/ảnh base64. PDF **cố ý loại** (bản dẫn xuất từ HTML, kém ổn định hơn).
      - Converter tốt ngay từ lượt 1: HTML MWG 256.571 ký tự → **5.069 ký tự / 37 dòng**.
        Claude tự strip tag thô ra 5.067 để đối chứng — nó **không nuốt nội dung**, 256KB kia
        là CSS + SVG + ảnh nhúng. Bản chuyển đọc được nguyên vẹn dòng
        khuyến nghị, dòng giá tham chiếu, bảng kịch bản định giá và bảng ba đợt giải ngân
        *(nội dung khuyến nghị cắt ở đây vì repo public — xem tiền lệ `0c24536`)*.
      - ⚠️ **Lượt 1 mở `*.html` cho TOÀN BỘ thư mục `_*` → sinh call TRÙNG.** Claude đếm thật:
        **17 thư mục có HTML, 15 trong đó CŨNG có `.md`**; chỉ `_mwg_research` và
        `_sentiment_report` là md=0. Chạy converter lên `_switch_tpb_hdb/TPB_HDB_Switch_report.html`
        ra đúng dòng khuyến nghị + hai giá tham chiếu của **chính quyết định đã có trong
        `04_pm_decision.md`** *(nội dung cắt, repo public)* — đó là bản trình bày cho khách. Backfill sẽ rút TPB + HDB ngày 29/06 **hai lần**, hai action khác nhau, hai giá
        tham chiếu khác nhau. Trên sổ cái 13 call thì hai call ma là 15% nhiễu.
      - Lượt 2: **markdown là nguồn có thẩm quyền; HTML chỉ là dự phòng cấp thư mục khi
        thư mục không có `.md` nào.** Claude chạy `iter_research_documents(".")` để kiểm:
        **206 tài liệu, đúng 2 HTML** — `_mwg_research` và `_sentiment_report`. Bản khách
        TPB/HDB bị loại.
      - Ba điểm nhỏ sửa cùng lượt: bỏ hằng `HTML_TEXT_CONVERTER` (khai ra mà không ghi vào
        đâu — grep cả repo chỉ thấy dòng khai báo; một phiên bản không được lưu là chú thích
        chứ không phải cơ chế); nhãn `external` → **`research_report`** mới (báo cáo do chính
        bàn mình sinh ra, không phải nguồn ngoài); và `handle_data` từng chèn dấu cách giữa
        hai khối data liền nhau nên `<span>69</span><span>.000</span>` ra `69 .000` — nay
        `69.000đ` nguyên vẹn, `TÍCH LŨY` vẫn giữ dấu cách thật, ô bảng vẫn ` | `.
      - **Số đo:** learning suite **228 → 233 xanh**; full suite `11 failed, 3375 passed,
        1 skipped, 9 errors` — fail/error khớp baseline từng cái. Chuyển hai lần ra chuỗi
        y hệt. Prompt sinh được, exit 0, **không gọi model, không tốn token**.
      - Còn lại cho lượt sau: MWG mới **có đường vào**, chưa có call. Cần một reply (Claude
        đóng vai model) để `_mwg_research` vào sổ.
- [x] **Q4 [C]** G2.2-c lịch nghỉ lễ VN cho T+2 — **xong, một lượt trả lại (chỉ để dọn, không phải sửa lỗi logic).**
      - Bỏ `np.busday_count`. `_sessions_held` nay nhận `pos.entry_bar_idx` và `self._bar_idx`,
        tức **đếm bar trong chuỗi phiên đã căn chỉnh**. Không bảng ngày lễ, không hard-code,
        tự đúng cho mọi năm kể cả năm chưa xảy ra. Thêm một điểm: `base.py:648` vốn đã tính
        `holding_bars` đúng bằng công thức đó — nay T+2 khớp với chính thước engine dùng chỗ khác.
      - **Sai lệch thật, Claude tự đọc `VNINDEX_daily.csv` của DataPro để kiểm** (file dùng
        epoch timestamp nên phải parse, không grep được):
        ```
        ... 2024-02-05, 02-06, 02-07 | 2024-02-15, 02-16, 02-19 ...
        np.busday_count(07/02 → 15/02) = 6 phiên
        số bar THẬT giữa hai ngày đó   = 1
        ```
        Sàn nghỉ Tết 7 ngày. Mua phiên 07/02 thì **ngay hôm sàn mở lại**, code cũ đã coi là
        qua T+2 và cho bán. Đây là look-ahead: backtest thoát sớm hơn đời thực đúng vào chỗ
        rủi ro nhất.
      - **Chứng minh hành vi, không phải chứng minh chữ ký hàm.** Lượt 1 Codex nộp test kiểu
        `assert _sessions_held(4, 5) == 1` — nó chỉ phát biểu lại `5-4=1`; ai quay về đếm ngày
        trong tuần thì test đỏ vì **đổi chữ ký**, không phải vì đổi hành vi. Lượt 2 viết lại cho
        chạy qua `_execute_bars` trên đúng sáu phiên Tết thật. Claude `git stash` bản vá rồi chạy
        test mới trên code cũ:
        ```
        code CŨ: exit_time = 2024-02-15, holding_bars = 1   ← đỏ
        code MỚI: exit_time = 2024-02-16, holding_bars = 2   ← xanh
        ```
        Test ca thường (19/02 → 21/02) xanh trên **cả hai** — hành vi không đổi ngoài chỗ cần đổi.
      - Xoá `_bar_date` trong `vn_equity.py`: chính thay đổi này làm nó mất caller cuối cùng.
        `china_a.py` có bản sao riêng nên không ai bị ảnh hưởng.
      - **Số đo:** backtest + learning + vn_equity: **261 xanh**. Full suite `11 failed,
        3377 passed, 1 skipped, 9 errors` — khớp baseline, passed +2.
      - ⚠️ **Codex báo `20 failed` rồi TỰ PHÂN LOẠI 9 fail thừa là "lỗi môi trường".** Chạy lại
        ngoài sandbox: đúng baseline. Nó **đoán trúng nhưng không có cách nào biết**. Đã yêu cầu:
        gặp fail vượt baseline mà không giải thích được thì nói "không xác minh được trong
        sandbox", đừng tự dán nhãn. Lượt sau nó làm đúng như vậy.
      - ⚠️ **`_upgrade/q4_pytest_tmp/` không xoá được** — thư mục RỖNG do pytest tạo, nhưng cả
        Codex lẫn Claude đều bị `Access is denied`, tới mức `icacls` **đọc ACL cũng bị chặn**
        (cùng họ với việc `%TEMP%\pytest-of-VVVZV` và `C:\tmp` bị chặn trong sandbox). Git không
        commit thư mục rỗng nên nó **không thể lọt lên repo public**; chỉ làm bẩn `git status`.
        Cần một shell có quyền cao hơn để dọn.
- [x] **Q5 [C]** G2.2-a hợp nhất hai client DataPro — **lượt đầu tiên Codex nộp mà không phải trả lại.**
      - `DataLoader.fetch()` nay chạy trên `vndata.price.ohlcv`. Xoá client HTTP riêng cùng
        `_normalize_symbol` / `_to_epoch` / `_fetch_frame` / `_EXTRA_FIELD_MAP`
        (**−151 dòng, +50**). Chữ ký loader không đổi; mọi caller trong `backtest/` đều truyền
        `fields`/`interval` bằng **keyword** nên không ai gãy vì `*` mới thêm.
        `DATAPRO_URL` / `DATAPRO_API_KEY` giữ nguyên — `price.py` đọc đúng hai biến đó.
      - **Đối chiếu trước/sau, Claude tự dựng harness riêng** (phục vụ `VRE_daily.csv` và
        `VNINDEX_daily.csv` qua `requests.get` giả, `git stash` để chạy code cũ, cache loader
        off mặc định nên không nhiễm):
        ```
                     rows   first_close   last_close   cols
        VRE.VN  cũ   1388      30.566        24.3      open high low close volume pre_close
        VRE.VN  mới  1388      30.566        24.3      (y hệt)
        VNINDEX cũ   1388     1120.47      1744.66     (y hệt)
        VNINDEX mới  1388     1120.47      1744.66     (y hệt)
        ```
        Giống từng con số, cả cổ phiếu lẫn chỉ số. `24.3` nghìn đồng khớp đúng giá tham chiếu
        VRE trong sổ cái — **không lệch thang 1000×**.
      - **Đơn vị nay ĐI KÈM dữ liệu thay vì phải đoán** (`DataFrame.attrs` sống qua cả bước
        chọn cột, Claude đã kiểm):
        ```
        VRE.VN     instrument=equity  price_unit=thousand VND  value_unit=thousand VND
        VNINDEX.VN instrument=index   price_unit=index level   value_unit=million VND
        ```
      - `fields` mở được **cả 24 cột** của `price.COLUMN_MAP` (`prop_*` tự doanh,
        `put_through_*` thoả thuận, `active_buy/sell_*` chủ động, `foreign_*`, `adj_rate`…),
        bốn alias cũ vẫn chạy, **tập cột mặc định không đổi**.
      - Fallback nay **ồn ào**: frame `degraded=True` → loader `raise SourceUnavailable` kèm
        lý do. Lỗi request sau `/ping` cũng không còn bị nuốt thành kết quả rỗng — đúng hướng
        đã chọn ở G0.1 (benchmark hỏng thì raise).
      - **Số đo:** 7 test mới; targeted `loader|backtest|vndata|datapro` **206 passed**
        (5 fail là nhóm duckdb cache có sẵn trong baseline); full suite `11 failed,
        **3384 passed**, 1 skipped, 9 errors` — khớp baseline, passed +7.
      - ⚠️ **Quyết định có chủ ý, cần biết:** loader **không** gọi `to_vnd()` tự động — giá cổ
        phiếu vẫn là **nghìn đồng** như loader cũ. Bật lên là mọi backtest cũ đổi 1000× lặng lẽ.
        Hệ quả: backtest nói `24.3` trong khi sổ cái nói `24300`. Hợp nhất về **một** đơn vị là
        việc riêng, phải chạy lại và đối chiếu toàn bộ kết quả cũ.
      - ⚠️ Nhỏ, có sẵn từ trước chứ không phải mới: `fields` chứa tên cột **sai chính tả thì bị
        bỏ im lặng**. Backtest có thể chạy thiếu đúng tín hiệu nó tưởng đã yêu cầu.
- [x] **Q6 [C]** G2.2-b PIT VN30 — **xong, không phải trả lại; Codex nói thật về giới hạn.**
      - `_materialize_named_universe` trong `runner.py`: config ghi `"universe": "VN30"` mà
        **không** có `codes` thì sinh `codes` từ `vndata.reference.symbols_by_group("VN30")`.
        Config đã liệt kê `codes` tay thì **giữ nguyên tuyệt đối**, không cảnh báo thừa.
        Cảnh báo đi qua tham số `warnings` sẵn có của `run_card.py` — không đẻ cơ chế mới.
      - **Nửa quan trọng hơn: nói thật.** Gọi `symbols_by_group` **không** chữa survivorship
        bias — hàm đó trả membership **hiện tại**, không phải membership tại từng ngày tái cơ
        cấu. Codex đã tìm và **không thấy** nguồn PIT nào trong `vndata` hay trong repo, và nói
        thẳng thay vì bịa. Nên run card mang nguyên văn:
        > `SURVIVORSHIP BIAS WARNING: VN30 codes use current membership as of 2026-08-30, not`
        > `point-in-time membership for the backtest period; constituents removed before this`
        > `date are absent.`
      - **Claude kiểm độc lập** (mock nguồn membership, không chạm mạng):
        ```
        codes sinh ra   : ['VCB.VN','FPT.VN','HPG.VN']  ← dedupe + lọc chuỗi rỗng
        codes tường minh: giữ nguyên, KHÔNG cảnh báo
        nguồn rỗng      → raise "returned no symbols"
        sai tên cột     → raise "returned no 'symbol' column"
        offline         → raise "Could not resolve VN30 membership..."
        universe lạ     → raise "Unsupported named backtest universe 'VN100'"
        cảnh báo tới run_card.json: True   |  tới run_card.md: True
        ```
        Bốn kiểu hỏng đều **ồn ào**, không lùi im lặng về danh sách cứng — cùng nguyên tắc G0.1 và Q5.
      - Schema cho phép (`extra="allow"`) nên `universe` và `_run_card_warnings` không làm
        gãy validate.
      - **Số đo:** `test_run_card.py` **12 passed**; targeted `backtest|run_card|vndata`
        **75 passed**; full suite `11 failed, **3389 passed**, 1 skipped, 9 errors` — khớp
        baseline, passed +5.
      - ⚠️ **Chưa có config nào trong repo dùng `universe: VN30`** — mục này mở đường, chưa đổi
        kết quả của bất kỳ backtest đang chạy nào. Muốn hưởng thì phải sửa config.
      - ⚠️ **Membership vẫn KHÔNG phải point-in-time.** Cảnh báo là bản vá cho sự trung thực,
        không phải bản vá cho bias. Muốn chữa thật thì cần lịch sử tái cơ cấu VN30 — chưa có nguồn.
- [x] **Q7 [C]** G2.2-d siết hợp đồng dữ liệu `vndata` — **xong 4/5 mục; mục 5 tách ra, xem Q9.**
      - **Hai lỗi Claude đọc ra trong `price.py` trước khi giao việc, nay đã sửa:**
        1. `_fallback_ohlcv` **gán cứng** `price_unit = "thousand VND"` mà không gọi
           `classify_instrument`. Đường DataPro chính thì phân biệt đủ ba loại. Hệ quả: DataPro
           chết, ai xin VNINDEX qua fallback, frame **dán nhãn "nghìn VND" cho một chuỗi điểm
           chỉ số**. Đúng câu `CLAUDE.md` gọi là *"suy đoán đơn vị giá theo giả định khi fallback"*.
        2. `_empty_frame()` luôn khai `source="datapro"`, `degraded=False` — **nhưng nó được gọi
           từ trong `_fallback_ohlcv`** khi vnstock_data trả rỗng. Một frame do nguồn dự phòng
           phục vụ lại tự khai đến từ DataPro và không suy giảm. Lỗi này **mới có hậu quả thật
           từ Q5**: loader nay tin `attrs["degraded"]` để quyết định raise.
        Nay đơn vị và xuất xứ được **suy ra ở mọi đường trả về, kể cả đường rỗng**.
      - **Đơn vị của `vnstock_data` KHÔNG khẳng định nữa.** Sandbox chặn socket tới
        `vnstocks.com` (`WinError 10013`) nên không đo được → ghi
        `price_unit = "unverified — vnstock_data native unit not verified"` thay vì đoán theo
        độ lớn con số. Giả định `"thousand VND"` cũ là một khẳng định chưa ai kiểm; nay nó tự
        tố cáo mình. (License local `silver`, `vnstock_data` 3.2.8.)
      - **Schema validation**: đủ `open/high/low/close/volume`, số hữu hạn, index là
        `DatetimeIndex` tên `trade_date`, tăng dần, không trùng. Hỏng thì raise.
      - **`attrs["session_audit"]`**: khoảng ngày yêu cầu, số bar, độ phủ, và danh sách ngày
        làm việc vắng mặt — gọi là **candidate**, không tự nhận là phiên thiếu, vì chỉ lịch sàn
        mới phân biệt được nghỉ lễ với mất dữ liệu. Claude đo trên VRE 5,5 năm: **1.388 bar,
        66 ngày vắng, toàn bộ nằm giữa chuỗi** — đúng bằng số ngày lễ VN giai đoạn đó, tức
        chính cái lịch Q4 vừa dạy engine phải tôn trọng.
      - **Một lượt trả lại, vì chẩn đoán chứ không vì logic.** Thông điệp lỗi ban đầu là
        `... must contain only finite numeric values: ['close']` — không nói mã nào, ngày nào.
        Sau Q5 loader **không còn bắt exception theo từng mã**, nên một `NaN` trong một mã dừng
        nguyên backtest 30 mã, và người vận hành chỉ nhận đúng dòng đó. **Một cổng chặn đúng mà
        không chỉ được chỗ hỏng thì người ta sẽ tắt cổng.** Claude tiêm 3 `NaN` vào CSV thật để kiểm:
        ```
        OHLCV frame for VRE.VN required columns must contain only finite numeric values;
        close: 3 rows non-finite, first dates=['2023-01-03', '2023-01-04', '2024-02-16']
        ```
        Có mã, có cột, có tổng số dòng, có ngày. **Hành vi raise giữ nguyên — không nới cổng.**
      - **Số đo:** Q7 trực tiếp **53 passed**; targeted **214 passed** (5 fail nhóm DuckDB
        loader-cache có sẵn); full suite `11 failed, **3397 passed**, 1 skipped, 9 errors` —
        khớp baseline, passed +8. **Đối chiếu Q5 không đổi một số nào**: VRE.VN 1388 dòng
        `30.566 → 24.3`; VNINDEX.VN 1388 dòng `1120.47 → 1744.66`.
      - ⚠️ **Câu hỏi thiết kế còn treo, cần anh quyết:** schema hỏng ở **một** mã nay giết **cả**
        lần chạy. Đúng hướng "hỏng thì ồn ào" của G0.1/Q5/Q6, nhưng khác về mức độ: một `NaN`
        giữa 1.388 bar là lỗi **chất lượng dữ liệu**, không phải lỗi **xuất xứ**. Giữ nguyên,
        hay cho phép bỏ qua theo mã và ghi vào run card? Đã ghi thẳng hậu quả vào docstring
        `ohlcv` để người dùng biết trước khi dựa vào nó.
      - ⚠️ **`session_audit` hiện là metadata THỤ ĐỘNG** — đính vào `attrs` nhưng chưa ai đọc.
        Cố ý không xây heuristic cảnh báo tự động ở lượt này.
- [x] **Q8 [C]** G2.2-e nâng `_DISCLOSURE_LAG_DAYS` lên `vndata` — **xong, không phải trả lại.**
      - Vấn đề đã **hiện hình chứ không còn là nguy cơ**: hai định nghĩa song song **đã lệch nhau**.
        `vnstock_data_fundamentals.py:79` có `{"year": 90, "quarter": 45}`; `vnstock_fundamentals.py:46`
        chỉ có số phẳng `90`, không có kỳ quý. Cả hai trả lời cùng một câu hỏi — *số liệu của một
        kỳ trở nên nhìn thấy được vào lúc nào* — và trả lời sai câu đó là **look-ahead**.
        `resolve.py` sắp tới sẽ cần đúng định nghĩa này, tức sắp có **bản sao thứ ba**.
      - Nay một nguồn duy nhất ở `agent/vndata/fundamental.py:43`, bọc `MappingProxyType` nên
        **không ghi đè được** (Claude thử gán → `TypeError`). Hai loader import về dùng.
      - **Docstring nói đúng thứ cần nói**, kể cả phần tự hạn chế: đây là *"conservative synthetic
        dates for feeds without an actual filing timestamp, not claims that every issuer filed on
        exactly that date"*. `90` là cửa sổ công bố BCTC năm kiểm toán; `45` là deadline BCTC quý
        hợp nhất 30 ngày cộng đệm an toàn 15 ngày.
      - **Giá trị GIỮ NGUYÊN** — đây là refactor về *nơi định nghĩa*, không phải dịp đổi số.
        Codex nói rõ nó chưa có căn cứ kết luận hai con số sai, và đề nghị tách việc đối chiếu
        với quy định công bố thông tin hiện hành thành mục riêng. Đồng ý.
      - **Claude kiểm trước/sau bằng `git stash`**, suy ngày công bố cho ba kỳ cụ thể:
        ```
                                   TRƯỚC        SAU
        sponsor quarter 2024-Q1    2024-05-15   2024-05-15
        sponsor year    2024       2025-03-31   2025-03-31
        free    year    2024       2025-03-31   2025-03-31
        ```
        Giống hệt. `vnstock_fundamentals.py` **không** mọc thêm nhánh quý dù nguồn chung có sẵn.
      - **Số đo:** `test_disclosure_lag.py` **2 passed**; targeted **224 passed** (5 fail nhóm
        DuckDB loader-cache có sẵn); full suite `11 failed, **3399 passed**, 1 skipped, 9 errors`
        — khớp baseline, passed +2. Grep toàn repo: **không còn hằng số song song nào.**
- [x] **Q9 [C]** *(tách ra từ Q7 mục 5)* Chính sách điều chỉnh giá + đối chiếu hai nguồn —
      **xong, vì điều kiện tiên quyết đã tự đến.** Đầu phiên 01/09 `datapro_available()` còn
      `False`, vài phút sau lên `True` (app đang khởi động), và mạng tới `vnstocks.com:443`
      đã thông. **Hai nguồn sống cùng lúc — đúng phép đo hôm 30/08 phải hoãn.**

      - **Đơn vị `vnstock_data`: HẾT "unverified".** Đối chiếu 15 mã × 65 phiên, cả hai nguồn
        gọi cùng lúc: `close` DataPro / `close` vnstock_data = **1,000000 ở CẢ 15 mã**. Không có
        bẫy 1000×, fallback **không cần rescale**. Chỉ số (VNINDEX) và phái sinh (VN30F1M) cũng
        về 1,000000. Phần lệch còn lại là **làm tròn của vendor**: DataPro giữ 3 chữ số thập phân
        của nghìn VND (`61.744`), vnstock_data làm tròn 2 (`61.74`) → **tối đa 5 VND**.
      - **Chính sách điều chỉnh giá: đo được, không suy diễn.** `*_PX` của DataPro là **giá đã
        điều chỉnh lùi**, và `ADJ_RATE` là hệ số luỹ kế từ phiên đó tới hiện tại — giảm bậc tại
        mỗi ngày GDKHQ, về đúng `1.000000` sau sự kiện gần nhất (VCB: 1,516970 → 1,013924 →
        1,007393 → 1,000000; SSI 6 bậc; MSN 1 bậc vì không có sự kiện quyền).
        **Chiều là NHÂN:** `giá thô = close × adj_rate`.
      - **Cách chứng minh — lưới bước giá HOSE làm phép phản chứng.** Bước giá do luật định
        (10 VND dưới 10.000; 50 VND tới 49.950; 100 VND từ 50.000), nên giả thuyết sai sẽ **rải
        đều** trên bước giá còn giả thuyết đúng thì không. Trên **9.908 phiên × 15 mã**:

        | Giả thuyết | khoảng cách tới bước giá (median) | p95 | max | ≤3 VND |
        |---|---:|---:|---:|---:|
        | `close × adj_rate` | **0,233 VND** | 0,63 | 1,01 | **100,00%** |
        | `close / adj_rate` | 8,615 | 38,90 | 49,93 | 32,05% |
        | `close` nguyên trạng | 12,000 | 42,00 | 50,00 | 27,57% |

        Hai giả thuyết sai cho median 8,6 và 12,0 — đúng bằng ~tick/4, tức nhiễu đều. Phần dư
        0,233 VND của giả thuyết thắng là **sai số làm tròn**, không phải sai thang: DataPro lưu
        1 VND còn bước giá là 50–100 VND. Kiểm ngược qua `traded_price()`: 9.908/9.908 phiên về
        đúng lưới, max 1,01 VND; **MSN về đúng 0,000** — mã duy nhất không có sự kiện quyền.
      - **`price.traded_price(df)` mới.** Chỉ dùng nơi lưới giao dịch thật sự có ý nghĩa: lệnh
        giới hạn, bước giá, biên độ. Suất sinh lời và chỉ báo **vẫn đúng trên chuỗi đã điều chỉnh
        và nên ở lại đó**. Không có `adj_rate` thì **raise**, không đoán — cả khi frame đến từ
        fallback lẫn khi `columns=` đã lọc mất cột.
      - **Ba khiếm khuyết của đường suy giảm do chính phép đối chiếu lôi ra, đã sửa:**
        1. **DataPro chết là MỌI yêu cầu chỉ số đều raise.** vnstock_data gắn thêm một dòng ảnh
           chụp trong phiên cho **phiên mới nhất** — cùng `close`, khác `open`/`volume` — nên
           cổng "index không trùng" của Q7 giết cả yêu cầu. Kiểm: VNINDEX và VN30 đều trùng ở
           `2026-08-28`, còn mọi khoảng lịch sử đã đóng thì **sạch 0 dòng trùng**. Nay gộp lại,
           **giữ dòng có volume lớn hơn** (ảnh chụp đầy đủ hơn), ghi vào
           `attrs["vendor_duplicate_sessions"]`. Trùng mà **lệch `close`** thì **không** phải
           hiện tượng này → rơi xuống cổng cũ và raise như trước.
        2. **`to_vnd` dán nhãn sai âm thầm.** `classify_instrument` trên frame vnstock_data trả
           **`"index"`** (không có `listed_shares`/`open_interest` → cả hai = 0), còn với
           `instrument="unverified"` thì `to_vnd` rơi vào nhánh **futures**, tức một cổ phiếu
           qua fallback ra nhãn *"index points"*. Nay `to_vnd` **raise** khi chưa phân loại được.
        3. **Nhãn đơn vị nói sai chỗ.** Cái chưa biết **không phải thang đo** (đã đo, bằng
           DataPro) mà là **loại công cụ** — vnstock_data không trả `listed_shares` lẫn
           `open_interest`, đúng hai tín hiệu `classify_instrument` đọc. Nhãn mới nói đúng điều đó.
      - **Số đo:** `test_vndata.py` **59 passed** (+13); targeted **82 passed**; full suite
        `11 failed, **3412 passed**, 1 skipped, 9 errors` — khớp baseline, passed +13.

- [x] **Q10 [C]** *(anh chốt câu hỏi treo của Q7)* Schema hỏng ở một mã **bỏ qua theo mã +
      ghi run card**, thay vì giết cả lần chạy.
      - **Ranh giới giữ nguyên chỗ Q7 đã vạch:** bỏ qua chỉ dành cho **lỗi chất lượng dữ liệu**
        (`ValueError` từ cổng schema). **Lỗi xuất xứ** — `SourceUnavailable`, frame không đến từ
        nguồn nó tự khai — **vẫn dừng cả lần chạy như cũ**. Có test riêng cho vế này để lần sau
        không ai nới nhầm.
      - Mã bị loại đi vào `DataLoader.skipped_symbols`, engine đổ sang `_run_card_warnings` —
        **đúng kênh Q6 dùng cho cảnh báo survivorship**, không đẻ cơ chế mới. Chống ghi trùng vì
        `runner.py` và `base.py` **đều** gọi `fetch()`.
      - **Kiểm trên dữ liệu DataPro SỐNG, không phải trên mock**: 5 mã 162 phiên, tiêm 3 `NaN`
        vào `close` của VCB.
        ```
        MỚI: trả về 4/5 mã (FPT, HPG, MWG, VRE), và run card ghi
             "SYMBOL DROPPED: VCB.VN failed the data schema gate and was not traded —
              close: 3 rows non-finite, first dates=['2026-01-08','2026-01-14','2026-03-09']"
        CŨ (git stash): raise ValueError, trả về 0 mã.
        ```
        Đây là **đổi hành vi thật**, không phải đổi chữ ký hàm — đúng câu hỏi luật 7 bắt phải hỏi.
      - **Số đo:** `test_datapro_loader.py` **15 passed** (+9); targeted **88 passed**; full suite
        `11 failed, **3420 passed**, 1 skipped, 9 errors` — khớp baseline, passed +8.

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
- [x] **1.5 Hook cuối phiên Claude Code** — `session.py` + `cli.py` +
  `.claude/hooks/learning-capture.sh`. **25 test xanh**, gồm một test chạy **thẳng script
  hook thật** qua `bash` (không mô phỏng), và một test đọc `.claude/settings.json` để chắc
  hook đã đăng ký.
  - **Hook KHÔNG đáng tin, và thiết kế phải giả định vậy.** `SessionEnd` chỉ bắn với
    `clear` / `resume` / `logout` / `prompt_input_exit` — **không** bắn khi tắt terminal,
    máy sleep, hay tiến trình chết. Nên hook làm hai việc: `capture` phiên hiện tại, rồi
    `scan` toàn bộ transcript trên đĩa để vá những phiên hook chưa từng bắn. Phiên bị mất
    không mất dữ liệu, chỉ trễ tới lần kết phiên bình thường kế tiếp.
  - **Không cần LLM, không cần provider.** Mọi trường đều **suy ra** từ transcript:
    `tokens` (cộng đủ 4 bộ đếm), `wall_time_sec` (đo trên `observed_at`, không phải
    timestamp thô — thứ chạy lùi 36 lần), `rework_count`, `research_paths`.
    `errors_caught` / `rounds` / `data_violations` **cố tình để trống**: chúng cần người
    đọc phân biệt "lỗi bị bắt" với "sửa văn", và mỗi mục phải có `evidence_id` mới qua
    được cổng của `ProcessRecord`. Bịa chúng từ số lần gọi tool chính là thứ sổ cái này
    sinh ra để chặn.
  - **Idempotent theo nội dung**: `process_id` gieo từ sự kiện **ĐẦU** phiên (không phải
    sự kiện cuối) nên chạy lại rơi trúng cùng record; `known_at` = `last_observed_at` của
    phiên, **không phải `utc_now()`** — lấy "bây giờ" thì payload đổi mỗi lần chạy và
    idempotency chết ngay. Đã kiểm: chạy hook 2 lần → lần 2 append **0**.
  - ⚠️ **Bẫy đã dính và đã sửa, giữ lại làm test hồi quy** (`test_the_scan_never_un_knows_a_completed_session`):
    `scan` không biết phiên kết thúc thế nào, nên nó ghi đè `completed=True` của hook thành
    `False` → payload khác → **mỗi lần chạy lại đẻ thêm một version của cùng một quan sát**.
    Quy tắc rút ra: **scan chỉ được cộng thêm hiểu biết, không được xoá hiểu biết.**
  - Cùng bệnh đó làm em **bỏ hẳn `git_commit`** khỏi capture: một phiên Claude Code kéo
    dài nhiều commit nên "commit mà phiên chạy trên" không có nghĩa xác định; giữ lại chỉ
    tạo một trường lúc có lúc không. Trường này thuộc về **swarm run** (một lần chạy bó gọn
    trên một checkout), không thuộc về phiên tương tác.
  - **`timeout: 30` là bắt buộc, không phải cho sang.** Hook `SessionEnd` dùng chung ngân
    sách **1,5 giây**; đặt timeout dài hơn thì Claude Code mới nâng ngân sách (tối đa 60s).
    Đo thật: capture + scan 21 transcript = **~4 giây**. Không đặt timeout thì hook bị giết
    giữa chừng. Có test khoá điều này.
  - ⚠️ **`.gitignore` đang chặn `.claude/*`** — hook chỉ tồn tại trên máy này thì đúng bằng
    cái bệnh cũ (xem Đính chính 4). Đã mở đúng hai lối: `!.claude/settings.json` và
    `!.claude/hooks/`. `settings.local.json` **vẫn bị chặn** (chỗ để quyền hạn theo máy).
  - Log: `~/.vibe-trading/hook.log` (cạnh `learning.db`). Mọi lỗi được ghi kèm giờ + exit 1
    — `SessionEnd` coi đó là cảnh báo không chặn, nên hook không bao giờ giết phiên.
  - **Số đo thật lần chạy đầu, 21 phiên:** tổng **1.011.623.992 token**; phiên lớn nhất
    317,8 triệu token / 9,5 giờ; `rework_count` cao nhất 10.
  - Còn thiếu để khép Giai đoạn 1: **ai đóng vai `propose`** cho `extract.py` (provider chưa
    ngã ngũ) — `research_paths` đã sẵn trong `CaptureResult` để nạp cho vòng trích xuất đó.
## Giai đoạn 2 — PIT + backtest cứng *(chưa bắt đầu)*
## Giai đoạn 3 — Playbook + vòng lặp tự động *(chưa bắt đầu)*
