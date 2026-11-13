# MatthewTrading — hướng dẫn cho AI agent

Fork của vibe-trading cho **thị trường chứng khoán Việt Nam** (HOSE/HNX/UPCOM):
skill phân tích, preset swarm, backtest, bản tin thị trường hằng ngày.
Ngôn ngữ làm việc: tiếng Việt.

---

## 🇻🇳 Nguồn dữ liệu: DataPro + VNDIRECT MCP (KHÔNG dùng vnstock)

> **Đọc trước khi viết bất kỳ dòng code lấy dữ liệu VN nào.**

Gói vnstock đã **huỷ ngày 13/11/2026** (xác thực ngừng từ 10/11/2026). Không
`import vnstock` / `vnstock_data` / `vnstock_ta` / `vnstock_news` ở bất kỳ đâu;
MCP `vnstock` và các tool `vn_*` đã gỡ. Còn hai nguồn sự thật:

| Loại dữ liệu | Nguồn | Gọi |
|---|---|---|
| Giá, KL, GTGD, giá tham chiếu, khối ngoại & tự doanh theo mã, thoả thuận, chỉ số, phái sinh, ETF, danh sách mã | **DataPro** | Python `vndata.price.*`, `vndata.reference.symbols()` · MCP `datapro` |
| Chỉ báo kỹ thuật | **tự tính trên giá DataPro** | `vndata.ta.indicator()` |
| Tin tức (tiêu đề + link) | **RSS nhà xuất bản** | `vndata.news.rss()` |
| Chỉ số tài chính & định giá, chỉ số ngân hàng, ICB, rổ chỉ số, sự kiện DN, lãnh đạo, khối ngoại tổng sàn, độ rộng sàn, quỹ mở, hàng hoá, lịch GD | **VNDIRECT MCP** | connector "VNDIRECT MCP", tool `FINFO_API__*` |
| **BCTC từng dòng + thuyết minh** | **PDF gốc** | `agent/scripts/evidence_pack.py` (Phase 0) |
| Vĩ mô VN | cơ quan công bố gốc (GSO, NHNN, BTC) | crawl4ai, ghi nguồn |
| Tỷ giá, DXY | Yahoo (`yfinance`, venv dự án) | `USDVND=X`, `DX-Y.NYB` |

**VNDIRECT MCP chỉ gọi được từ Claude / subagent** (OAuth, tool tên đầy đủ dạng
`mcp__<id-connector>__FINFO_API__get_ratios`; tìm bằng `ToolSearch("FINFO_API")`).
Python không có đường tới nó: `vndata.fundamental/macro/corporate` và
`vndata.reference.company/events/...` **cố ý raise `SourceUnavailable`** chỉ sang
VNDIRECT — không tự chế nguồn thay, không ước tính thay số. ICB cấp 2 và rổ VN30
mà Python cần hằng ngày (bản tin, backtest, learning loop) đọc từ **snapshot**
`agent/data/vn_reference/` lấy qua VNDIRECT.

**Swarm phân tích chạy bằng subagent Claude** (runtime OpenRouter đã chết) → agent
gọi thẳng tool VNDIRECT MCP cho số cơ bản, Python (`$HOME\.venv` hoặc `.venv`)
cho giá DataPro.

Bảng tool đầy đủ, cú pháp `get_ratios`, mã `ratioCode`, các bẫy đơn vị đã đo
(tỷ lệ là **phân số**; `EBITDA_TR` hỏng; `0` ở hàng hoá/quỹ = **thiếu số**):
skill **`data-routing`** và `VN_DATA_SOURCE.md`. Kiểm nguồn trước một phiên dài:

```bash
.venv/Scripts/python.exe agent/scripts/vn_preflight.py
```

---

## 🚦 BẮT BUỘC: Phase 0 trước mọi swarm phân tích doanh nghiệp

**Không chạy bất kỳ preset phân tích/đánh giá doanh nghiệp nào (fundamental_research_team,
equity_research_team, value_investing_committee, risk_committee…) trước khi có thư mục bằng chứng gốc.**
Agent chỉ được viết sau khi `FACTS.md` tồn tại.

```bash
# venv DỰ ÁN (có crawl4ai + fitz + pdfplumber). $HOME/.venv KHÔNG có fitz.
./.venv/Scripts/python.exe agent/scripts/evidence_pack.py <MÃ> --outdir _<mã>_research --auto
```

Script cào `finance.vietstock.vn/<MÃ>/tai-tai-lieu.htm`, tải PDF từ `static2.vietstock.vn` (không cần
login), đo lớp text từng trang, trích sẵn phần có text và ghi `EVIDENCE_MANIFEST.md`.
**Ưu tiên bản SOÁT XÉT bán niên** — thuyết minh đầy đủ nhất và có ý kiến kiểm toán.
Nếu doanh nghiệp có **công ty con đã niêm yết**, tải luôn BCTC của nó.

Sau khi có tài liệu, làm đủ 5 bước rồi mới sang Phase 1:
1. Đọc mục lục → ánh xạ trang PDF ↔ trang tài liệu (thường lệch +2).
2. Đọc ý kiến kiểm toán/soát xét — có ngoại trừ hoặc đoạn nhấn mạnh không.
3. Đọc bảng cân đối → lấy **số hiệu thuyết minh** cho từng khoản cần soi.
4. Render đúng dải trang đó (`--render 8-56`, 200 DPI) → đọc bằng vision →
   **kiểm đẳng thức tổng cộng từng bảng**, số không khớp thì không dùng.
5. Ghi `FACTS.md`: mỗi số kèm nguồn + số trang, gắn nhãn `[gốc]` / `[thứ cấp]` / `[giả định]` /
   `[khoảng chặn]`. **Cấm ghế nào dùng số ngoài sổ.**

**Cổng chặn:** vấn đề treo trọng yếu chưa giải → dừng, giao memo thiếu bằng chứng, KHÔNG viết
báo cáo đầu tư. Mục "bất khả giải" phải **chặn khoảng** (cận trên/cận dưới + cách dựng), cấm ghi
"không giải được" rồi đi tiếp.

**Vì sao bắt buộc:** swarm MWG 07/09/2026 ra báo cáo **tin cậy 58%** với 5 vấn đề treo — không mục nào
thực sự bất khả giải, chúng chưa được giải vì **không agent nào mở BCTC gốc**. Đọc thuyết minh xong
(~45 phút) đóng **23/44** vấn đề, gồm cả hai mục từng bị xếp "bất khả giải". Chi tiết quy trình 4 pha
2 cổng: memory `workflow-research-desk-v2`.

---

## 💻 Môi trường Python

| Env | Dùng cho |
|---|---|
| `.venv` (dự án) | backtest, `evidence_pack.py` (crawl4ai + fitz + pdfplumber), `yfinance`/`akshare` cho hàng hoá |
| `$HOME\.venv` | crawl4ai, stack NLP tiếng Việt, script bản tin |

Gói vnstock có thể vẫn còn cài trong venv nhưng **không được import**.

---

## ⚠️ Quy tắc dữ liệu (BẮT BUỘC)

1. **Không bịa số.** Mọi số tài chính có nguồn thật; cross-check ≥2 nguồn
   (cafef.vn, vietstock.vn) bằng crawl4ai, lệch thì nêu rõ.
2. **DataPro và VNDIRECT MCP đều thiếu → crawl4ai** từ cafef/vietstock/web công
   ty rồi mới phân tích.
3. Khoản mục bất thường → đọc **thuyết minh BCTC** gốc, trích số trang.
4. Giờ giao dịch VN: 9:00–15:00; dữ liệu trong phiên chỉ có trong khung này.
