# Sổ tay vận hành — vòng lặp tự học

Tài liệu này là thứ đọc **lúc thực chiến**. Lịch sử xây dựng nằm ở
`_upgrade/PROGRESS.md` (2.300 dòng) — đừng đọc file đó để biết phải gõ gì.

**Trình thông dịch:** `C:\Users\VVVZV\MatthewTrading\.venv\Scripts\python.exe`
**Thư mục chạy:** `agent/` · **Sổ cái:** `~/.vibe-trading/learning.db`

Mọi lệnh dưới đây viết tắt `learning X` cho `python -m src.learning.cli X`.

---

## Hệ thống này làm gì

Nó ghi lại **quyết định đã phát biểu** của bàn, rồi sau đó chấm chúng bằng
chuỗi giá thật — để câu "mình phân tích có đúng không" trở thành một con số
thay vì một cảm giác. Sổ cái là **append-only**: sửa thì ghi bản mới, không đè
bản cũ, và không có đường sửa tại chỗ.

Ba việc nó **không** làm: không sinh khuyến nghị, không chọn thước đo sau khi
biết kết quả, và không lấp chỗ trống bằng số ước lượng.

---

## Vòng lặp hằng tuần

### 0. Hỏi sổ xem còn thiếu gì

```bash
learning status                 # offline, không ghi gì, không cần DataPro
```

In ra ba thứ: tóm tắt sổ cái, **hàng đợi backfill theo episode**, và những call
chưa có outcome.

Đọc phần `covered` cho đúng: coverage được xét **theo thư mục**, trong khi một
episode thật là **(thư mục, mã)**. Một thư mục đã sinh call cho mã A vẫn có thể
chứa một quyết định thật về mã B — `_bankdata` có TPB và TCB, `_vre_committee`
có VRE + HPG + TCB. Offline thì không biết mã của một tài liệu nếu chưa gọi
model, nên lệnh **nói ra giới hạn đó** thay vì giả vờ không có. Đừng đọc
"không phải nguồn của call đã lưu" thành "đã có trong sổ".

### 1. Nạp quyết định mới vào sổ

```bash
learning extract --doc ../_<thư_mục_nghiên_cứu>/<tài_liệu_quyết_định>.md
```

Khoảng **70 giây và ~$0,35** mỗi tài liệu. Trả lời của model được ghi ra
`~/.vibe-trading/proposals/<stamp>-<digest>.json` **trước khi** vào sổ, nên
lần chạy nào cũng tái lập được bằng `--reply <file>`.

Đọc lại cùng một tài liệu **không** sinh bản ghi thứ hai — idempotency khoá
theo nội dung. Chạy lại an toàn.

**Chỉ nạp tài liệu QUYẾT ĐỊNH.** Ba loại file sau nằm cùng thư mục nhưng
không phải quyết định, và nạp chúng làm hỏng số liệu:

| Không nạp | Vì sao |
|---|---|
| `BULL.md` · `BEAR.md` · `RISK.md` | lập trường của một vai, không phải kết luận của bàn |
| `raw_*.md` · `_crawl_*.md` · `_data_brief.md` | dữ liệu đầu vào |
| `client_report.md` · `BAO_CAO_TONG_HOP*.md` · bản dựng để render PDF | **bản kể lại** một quyết định sổ đã giữ |

Loại thứ ba là cái bẫy đắt nhất. Ngày 06/09/2026 hàng đợi backfill được lập
theo **tài liệu**, và 3 trong 5 mục hoá ra là bản kể lại — chúng vào sổ rồi
**đè lặng lẽ** lên quyết định gốc với verdict khác (`hold` đè `reduce`,
`buy` đè `avoid`, ở đúng mức giá mà hội đồng viết là KHÔNG mua).

> **Luật:** hàng đợi backfill đi theo **episode** (một thư mục = một quyết
> định), không theo tài liệu. Episode đã có call trong sổ thì mọi tài liệu còn
> lại trong thư mục đó là ứng viên-kể-lại cho tới khi chứng minh ngược lại.

Từ 06/09 mỗi lần ghi đè đều **in ra**, không còn im lặng:

```
  ! VRE avoid -> buy: this overrides call_53bae6e9805d in episode ep_dbb48c11dffb
```

Thấy dòng `!` mà anh **không** chủ ý đổi ý thì dừng lại — gần như chắc chắn
đang nạp một bản kể lại.

### 2. Chấm những call đã tới hạn

```bash
learning resolve                # ghi vào sổ
learning resolve --dry-run      # chỉ xem, không ghi
```

**Cần DataPro desktop đang mở** (`localhost:6789`). Không mở thì lệnh chết
ngay với câu *"DataPro desktop is not answering"* — đó là **thiết kế**, không
phải lỗi: thà đứng còn hơn lùi về một nguồn giá yếu hơn rồi chấm bằng nó.

### 3. Đọc bảng điểm

```bash
learning report                 # hoàn toàn offline, không model, không mạng
learning report --checkpoint 63
learning cost                   # chi phí mỗi kết luận, theo tháng
```

---

## Đọc bảng điểm thế nào

**Đọc khoảng tin cậy trước khi đọc tỷ lệ.** Với n dưới ~30, hit rate là một
con số gần như không tách được khỏi ngẫu nhiên, và bảng điểm in KTC kèm mọi
lần chính vì thế. Câu *"the interval spans 59% of the range"* nghĩa là: chưa
biết gì cả.

**Hai thước đo in cạnh nhau, không được chọn một.** So với VN-Index và so với
cổ phiếu điển hình trong VN30 có thể cho hai câu trả lời khác nhau — VN-Index
là chỉ số **vốn hoá**, vài mã lớn kéo nó xuống dưới mã trung vị. Chọn cái có
lợi sau khi biết kết quả chính là thất bại mà sổ cái này sinh ra để chặn.

**Dòng `CONFIDENCE` là dòng đáng đọc nhất.** Nó là số duy nhất trên một call
nói về **người phân tích** chứ không nói về cổ phiếu. Hiện `confidence` khai
ra **không** tốt hơn khai base rate (Brier cao hơn) — n còn quá nhỏ để kết
luận, nhưng đó là thứ cần theo dõi.

**`DID THE ENTRY EVER PRINT?`** là câu hỏi sắc hơn alpha cho call đứng ngoài.
Một call `wait` hứa một mức giá tốt hơn; alpha không kiểm điều đó, dòng này có.

**`no_claim` không phải điểm kém.** `hold` / `neutral` không khẳng định chiều
nào nên được **đo mà không chấm** — chúng nằm ngoài cả tử số lẫn mẫu số.

---

## Bẫy đếm — đọc trước khi tự truy vấn SQL

`SELECT count(*) FROM outcomes` trả về số **dòng**, không phải số outcome. Sổ
append-only ghi bản sửa chứ không đè, nên ba lần chạy `resolve` là ba revision
của cùng một `outcome_id`. Đọc `count(*)` như số outcome sẽ **thổi mẫu số lên
gấp ba** và làm khoảng tin cậy hẹp giả.

Đường đọc đúng: `outcomes_for()` và `list_calls()` — cả hai đã gộp theo id và
trả bản đang có hiệu lực. `list_calls()` trả **một bản ghi mỗi episode**.

---

## Rút một dòng khỏi sổ

Khi một dòng vào sổ do đọc sai (bản kể lại, dẫn lại, đầu vào):

```bash
python -m src.learning.migrate --install --withdraw "call_xxxxxxxx=<lý do>"
```

**Lý do là bắt buộc** — một dòng rời sổ mà không có lý do thì không phân biệt
được với một dòng bị mất. Outcome đi theo call; **evidence ở lại**, vì trích
dẫn là sự thật về tài liệu, chỉ cách đọc nó là sai.

Sổ cũ được giữ nguyên vẹn ở `learning.db.bak-<stamp>` và **chính nó là đường
lùi**: đổi tên nó về `learning.db` là quay lại trạng thái trước.

Rút một call sổ không có thì lệnh **báo lỗi**, không im lặng.

---

## Chữ ký của các kiểu hỏng

| Triệu chứng | Nghĩa là | Làm gì |
|---|---|---|
| `DataPro desktop is not answering` | app chưa mở | mở DataPro, chạy lại |
| `claude exited 1:` với **stderr rỗng** | phiên Claude hết token, **không** phải lỗi hạ tầng | đợi quota, hoặc `--proposer codex` |
| `refused: quote_not_found` | model trích dẫn không khớp nguyên văn tài liệu | đọc reply đã lưu; **đừng nới cổng** |
| `refused: scale_ambiguous` | không trích dẫn nào mang đơn vị giá, nên `12.80` không neo được là 12.800 hay 12,80 | thường là **từ chối đúng** với báo cáo kỹ thuật |
| `refused: unknown_action` | kết luận dùng từ ngoài từ vựng đóng | kiểm câu điều hành thật của tài liệu trước khi thêm alias |
| `refused: action_not_in_evidence` | action khai ra không có dòng nào trong tài liệu chứa nó | thường là bắt **đúng** |

**Từ chối là tính năng, không phải lỗi.** Mỗi lần nới một cổng để cho tài liệu
đi qua, một call sai đi vào sổ và bảng điểm mất nghĩa. Đã có tiền lệ: một lần
nới cổng khiến tài liệu viết *"KHÔNG ĐẶT MỘT LỆNH MUA NÀO"* chứng nhận được
một call `buy`.

---

## Cái hệ thống này KHÔNG đo — nói ra để không ai tưởng nó đo

1. **Survivorship bias chưa được chữa.** Rổ peer là VN30 **hiện tại**, không
   point-in-time; mã bị loại khỏi rổ vì giảm giá nên phân phối peer hơi cao,
   tức mọi phân vị hơi thấp. Run card mang cảnh báo — đó là bản vá cho *sự
   trung thực*, không phải cho *bias*.
2. **Call hoán đổi hai mã.** `switch` **không** có trong từ vựng action: một
   bản ghi là một mã, chấm bằng chuỗi giá của mã đó, nên `switch` không có gì
   để chấm. Memo hoán đổi vào sổ dưới dạng hai call (`reduce` mã này +
   `accumulate` mã kia) — đó là một **phân rã**, không phải nguyên văn.
3. **Call theo ngành.** Cùng lý do: một bản ghi là một **mã**. Báo cáo xoay
   vòng ngành kết luận `MARKET-WEIGHT` / `OVERWEIGHT` cho cả nhóm thì không có
   chuỗi giá nào để chấm, và `MARKET-WEIGHT` không nằm trong từ vựng action.
   Nạp nó vào sổ là ép một call ngành thành một call mã — đừng làm.
   *(Đã gặp: `_sector_rotation_banks/BaoCao_XoayVongNganh_NganHang_2026-06-18.md`,
   cố ý không nạp.)*
4. **Trigger dạng văn xuôi.** Chỉ `stop` được máy kiểm. Điều kiện kiểu *"nếu
   Q2 không xác nhận"* được đếm và ghi ra `n free-text trigger(s) not
   machine-checked`, không được kiểm.
5. **Cổng `reliability` của scheduler đang đóng** ở ~17% so với sàn 50%. Đó là
   **câu trả lời đúng** trên dữ liệu hiện có, không phải lỗi cần vá — và không
   được mở bằng cách hạ sàn hay loại lỗi provider khỏi mẫu số.

---

## Khi sửa code trong `src/learning/`

- Full suite baseline: **11 failed, 9 errors** — fail/error phải khớp **từng
  cái**, không chỉ khớp số đếm. Suite chạy ~6–7 phút.
- **Suite đang chạy thì không đụng file `.py`.** Đã mất một lần đo ~9 phút vì
  luật này bị vi phạm.
- **KHÔNG** `pytest --basetemp` trỏ vào trong repo. ACL máy này khiến thư mục
  pytest tạo ra không ai xoá được; `_upgrade/` đã có 5 thư mục kẹt vĩnh viễn.
- Đổi chữ ký một helper thì `grep` **toàn repo**, không grep trong một file.
- Với mọi thay đổi động vào một **cổng**: dựng ca đối kháng chạy trên chính
  hàm mới, rồi hỏi *"code cũ có từ chối ca này không"*. Nới cổng luôn lộ ra
  dưới dạng "cũ nói không, mới nói có". Test xanh **không** đủ để kết luận.
- **Một lần chạy không báo lỗi không có nghĩa là nó ghi đúng.** Mở sổ ra đọc
  sau mỗi đợt backfill.
