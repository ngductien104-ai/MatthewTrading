---
name: web-reader
description: Read web pages, articles, and document links by converting URLs into Markdown text. Use the `read_url` tool directly, without bash. Sends the full URL to the third-party Jina Reader (r.jina.ai).
category: tool
---
# Web Reading

## Purpose

Converts any URL into clean Markdown text, removing ads, navigation, styling, and other distractions. Suitable for:
- Reading API documentation (`tushare`, `OKX`, `yfinance`, and similar)
- Reading technical articles and blogs
- Retrieving research reports and announcements
- Reading GitHub README / Wiki pages

## Usage

**Call the `read_url` tool directly (do not use bash + requests, call the tool directly):**

```
read_url(url="https://tushare.pro/document/2?doc_id=27")
```

Returns JSON:
```json
{
  "status": "ok",
  "title": "Page title",
  "url": "Original URL",
  "content": "Page content in Markdown format",
  "length": 12345
}
```

## Notes

- Content longer than 8000 characters will be truncated, with the total length noted at the end
- Dynamically rendered SPA pages may return only skeleton HTML
- Chinese content is supported normally

## Privacy & freshness

- **Third-party dependency:** `read_url` forwards the full target URL
  (including any query string) to the external Jina Reader service
  (`r.jina.ai`). Do **not** pass URLs containing credentials, tokens, or
  private/internal addresses — they would leave this host.
- **Caching/staleness:** results may be a cached snapshot, not live data.
  When stale, the JSON includes `"cached": true`; pass `no_cache=true` to
  force a fresh fetch (slower — use only when freshness matters).
- **Bash fallback caveat:** if a site blocks the reader (e.g. HTTP 451) a
  manual `bash + requests` fetch is possible, but it **bypasses this
  tool's URL safety guard and the Jina layer** — use sparingly and never
  for internal/authenticated URLs.

## Common Usage

### Read API Documentation
```
read_url(url="https://tushare.pro/document/2?doc_id=27")
```

### Read Technical Articles
```
read_url(url="https://blog.example.com/quantitative-trading-guide")
```

### Retrieve GitHub Project Information
```
read_url(url="https://github.com/PaddlePaddle/PaddleOCR")
```


## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)

1. **Không bịa/cook số liệu.** Mọi số tài chính phải có nguồn thật. Luôn **audit nhanh, cross-check tối thiểu 2 nguồn uy tín** (vd `cafef.vn`, `vietstock.vn`) — dùng **crawl4ai** cào số rồi đối chiếu; nếu nguồn lệch nhau thì nêu rõ, không chọn bừa.
2. **Nếu DataPro VÀ vnstock đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
