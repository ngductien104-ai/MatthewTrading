---
name: doc-reader
description: Read any common document/data file — PDF, Word (.docx), Excel (.xlsx/.xls), PowerPoint (.pptx), images (OCR), CSV/TSV, plain text, JSON/YAML/TOML, HTML/XML, and most source-code files. Use the `read_document` tool.
category: tool
---
# Universal Document Reader

## Purpose

Return extracted text from any supported file in a single unified JSON
envelope. The tool dispatches by file extension — you always call the same
tool regardless of format.

### Supported formats

| Category | Extensions | Notes |
|---|---|---|
| PDF | `.pdf` | Text pages extracted in ms; scanned/image pages fall back to OCR |
| Word | `.docx` | Paragraphs + table cells |
| Excel | `.xlsx`, `.xls` | All sheets, first 100 rows per sheet as preview |
| PowerPoint | `.pptx` | Slide text content |
| Images | `.png/.jpg/.jpeg/.gif/.bmp/.webp/.tiff` | OCR only |
| CSV / TSV | `.csv`, `.tsv` | Raw text with encoding fallback |
| Plain text | `.txt/.md/.log/.rst` | Encoding fallback |
| Config | `.json/.yaml/.yml/.toml/.ini/.cfg/.env` | Raw text |
| Markup | `.html/.htm/.xml` | Raw text (no HTML stripping) |
| Source code | `.py/.js/.ts/.tsx/.go/.rs/.java/.cpp/.c/.sql/.sh/...` | Raw text |
| Unknown extension | anything else | Best-effort read as UTF-8/GBK text |

**Blocked** (rejected at `/upload`): executables (`.exe/.dll/.so/...`) and
archives (`.zip/.tar/...`). Ask the user to unpack archives locally first.

## Usage

**Always call the tool directly — do not run Python from bash.**

```
read_document(file_path="uploads/paper.pdf")
read_document(file_path="uploads/annual_report.pdf", pages="1-10")
read_document(file_path="uploads/contract.docx")
read_document(file_path="uploads/sales.xlsx")
read_document(file_path="uploads/deck.pptx")
read_document(file_path="uploads/chart.png")     # image → OCR
read_document(file_path="uploads/config.yaml")
read_document(file_path="uploads/notes.md")
```

The `pages` parameter only applies to PDF; other formats ignore it.

## Return envelope

All formats share this shape:

```json
{
  "status": "ok",
  "file": "paper.pdf",
  "format": "pdf",
  "char_count": 52000,
  "truncated": true,
  "text": "..."
}
```

Format-specific extra fields:

| Format | Extra keys |
|---|---|
| `pdf` | `total_pages`, `pages_read`, `ocr_pages` |
| `docx` | `paragraphs`, `tables` |
| `excel` | `sheets` (array of `{name, rows, cols}`) |
| `pptx` | `slides` |
| `text` | `encoding`, `size` |

Content longer than 15000 chars is truncated; for PDFs use the `pages`
parameter to read slices.

## Workflows

### Paper / report summary
```
1. read_document(file_path="paper.pdf")  → full text
2. Extract abstract, methodology, conclusion → summarize
```

### Contract review
```
1. read_document(file_path="contract.docx")  → paragraphs + tables
2. Flag key clauses (termination, liability, payment, IP)
```

### Spreadsheet quick-look
```
1. read_document(file_path="sales.xlsx")  → all sheet previews
2. If user wants trade journal analysis specifically, pivot to
   `analyze_trade_journal` tool instead (see trade-journal skill).
```

### Chart / screenshot / scanned PDF
```
1. read_document(file_path="scan.png")  → OCR text
2. If OCR returns empty, tell the user; don't fabricate.
```

## Notes

- **Encoding fallback** order for text: utf-8 → utf-8-sig → gbk → gb2312 → big5 → latin-1.
- **OCR** uses RapidOCR; if the package is missing, image/scanned files
  return empty `text` with a `note` field — tell the user to install
  `rapidocr-onnxruntime`.
- **Excel previews** are limited to 100 rows per sheet to stay in budget.
  If the user needs full data (e.g. trade journals), call
  `analyze_trade_journal` instead.
- **Source-code files** are returned raw; do not re-format or re-indent.


## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)

1. **Không bịa/cook số liệu.** Mọi số tài chính phải có nguồn thật. Luôn **audit nhanh, cross-check tối thiểu 2 nguồn uy tín** (vd `cafef.vn`, `vietstock.vn`) — dùng **crawl4ai** cào số rồi đối chiếu; nếu nguồn lệch nhau thì nêu rõ, không chọn bừa.
2. **Nếu DataPro VÀ vnstock đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
