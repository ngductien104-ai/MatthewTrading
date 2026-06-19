---
name: social-media-intelligence
description: "Tình báo mạng xã hội TTCK Việt Nam — thu thập & định lượng tín hiệu từ forum (F247/Fireant/Vietstock/Bovagau), báo (CafeF/24hMoney/VnEconomy/TNCK), Telegram/Zalo/Facebook room phím hàng, KOL YouTube/TikTok. Trọng tâm: PHÁT HIỆN ĐỘI LÁI/PHÍM HÀNG, NLP lóng tiếng Việt, buzz-factor theo mã. Xương sống thu thập: crawl4ai. Bổ trợ: /last30days cho lớp KOL video."
category: tool
---

# Tình báo mạng xã hội — TTCK Việt Nam

> **Ranh giới skill (đọc trước):**
> - Skill này = **đào sâu LỚP MẠNG XÃ HỘI**: thu thập → làm sạch → định lượng (NLP tiếng Việt) → **phát hiện đội lái** → dựng buzz-factor theo mã.
> - Khung **tâm lý toàn thị trường** (khối ngoại, dư nợ margin, tài khoản mở mới, thanh khoản/độ rộng, basis VN30F) → xem [[sentiment-analysis]]. Đừng làm lại ở đây.
> - Vòng xoáy giải chấp / call margin / quy định → [[regulatory-knowledge]]. Dòng ETF → [[etf-analysis]].
> - Phạm vi: **CỔ PHIẾU VN**. Crypto/Telegram crypto có skill riêng (onchain/defi/ccxt) — không bàn ở đây.

---

## 0. Vì sao KHÔNG bê nguyên khung Mỹ/crypto

Bản gốc (FinTwit, WSB short-squeeze, options flow, VADER/FinBERT) **lệch hẳn thực tế VN**. Phải bỏ/thay, không dịch:

| Bản gốc (Mỹ/crypto) | Thực tế VN → xử lý |
|---|---|
| Twitter/X cashtag `$AAPL`, Reddit r/wallstreetbets | Người VN bàn cổ phiếu trên **forum nội + Facebook/Zalo/Telegram + KOL video**, KHÔNG dùng X/Reddit → **bỏ**, thay bằng nguồn VN |
| WSB short-squeeze (SI>20%, borrow tightness) | **VN cấm bán khống cổ phiếu** → không có squeeze cổ phiếu cơ sở → **bỏ** |
| Options open-interest / IV bất thường | **Không có quyền chọn cổ phiếu** ở VN (chỉ CW + VN30F) → **bỏ**, dùng CW/phái sinh ở [[sentiment-analysis]] |
| VADER / FinBERT (tiếng Anh) | Văn bản VN đầy **lóng + teencode + bỏ dấu** → **LLM-based + lexicon lóng VN** (mục 4) |
| Manipulation = "rủi ro phụ" | Ở VN **đội lái/"phím hàng"/"úp bô" là rủi ro TRUNG TÂM** (lẻ ~85–90%, nhiều penny/midcap bị làm giá) → nâng thành **mục lõi (mục 5)** |

**Tư duy nền:** thị trường lẻ chi phối → MXH vừa là *nguồn tâm lý đám đông* vừa là *kênh thao túng*. Cùng một tín hiệu buzz có thể là tiền thật vào HOẶC bẫy úp bô. Phân biệt hai cái này là giá trị chính của skill.

---

## 1. Bản đồ kênh MXH chứng khoán VN (phân tầng tín hiệu)

| Kênh | Loại | Nội dung điển hình | Độ nhiễu | Giá trị tín hiệu | Truy cập |
|---|---|---|---|---|---|
| **Fireant** | feed/forum theo mã | Tin + bình luận gắn mã, room phân tích | Trung bình | Cao (theo mã, tập trung) | crawl4ai (SPA, cần JS render) |
| **F247** (kế F319), **Vietstock forum** | forum | Topic theo mã/ngành, "hô hàng", phân tích lẻ | Cao | Trung bình (buzz lẻ, lọc kỹ) | crawl4ai (HTML + phân trang) |
| **Bovagau** | forum/cộng đồng | Phím hàng, kèo lướt | Rất cao | Thấp–TB (chủ yếu đo buzz/đội lái) | crawl4ai |
| **CafeF, 24hMoney, VnEconomy, TNCK** (Tinnhanh CK) | báo tài chính | Tin chính thống, sự kiện DN, vĩ mô | Thấp | Cao (sự kiện), thấp (sentiment) | crawl4ai (list → bài) |
| **Telegram "room phím hàng"** | room | Hô mua/bán, call kèo, target | Rất cao | TB (nhiệt kế + dấu hiệu lái) | `t.me/s/<kênh>` qua crawl4ai (public, **không cần telethon**); telethon nếu cần lịch sử sâu |
| **Group Facebook đầu tư** | group kín/mở | Thảo luận, hô hàng, "phòng hô" | Rất cao | TB (đo đồng thuận lẻ) | **Login-gated** → khó cào tự động (xem 2.5) |
| **Group Zalo đầu tư** | group kín | Phím hàng riêng môi giới/đội | Rất cao | TB nhưng **kín** | **Không cào được** → chỉ thủ công/được mời |
| **KOL YouTube / TikTok / Facebook CK** | video/clip | Nhận định, "kèo", review mã | Cao | TB–Cao (KOL lớn lay động lẻ) | **/last30days** (engagement video) hoặc API nền tảng |

> **Quy tắc trọng số nguồn:** môi giới/KOL có hồ sơ minh bạch > forum thảo luận có lập luận > room hô 1 chiều/nhóm kín. Tài khoản mới/bot/copy-paste → trọng số **0**.

---

## 2. Thu thập dữ liệu — crawl4ai là xương sống

### 2.1 Vì sao crawl4ai
VN **không có API MXH sạch** cho forum/báo. crawl4ai (đã cài `$HOME\.venv`, v0.8.9 — xem [[reference-crawl4ai-home-venv]]) trả **markdown sạch + render JS**, không phụ thuộc selector dễ vỡ. Gọi bằng:
```
$HOME\.venv\Scripts\python.exe  (Python 3.11.15)
```

### 2.2 Schema chuẩn hóa (1 schema chung cho MỌI nguồn VN)

```python
# Mọi collector trả về list[dict] theo đúng schema này → hạ nguồn xử lý đồng nhất.
ITEM_SCHEMA = {
    "nguon":      str,    # fireant|f247|vietstock|bovagau|cafef|24hmoney|vneconomy|tnck|telegram|facebook|youtube|tiktok
    "loai":       str,    # forum|news|room|kol_video|group
    "id":         str,
    "thoi_gian":  str,    # ISO8601
    "tac_gia": {
        "id":            str,
        "ten":           str,    # LƯU DẠNG HASH nếu là cá nhân (mục 2.6)
        "tuoi_tk_ngay":  int,    # tuổi tài khoản (ngày) nếu lấy được
        "so_bai":        int,
        "uy_tin":        str,    # moi_gioi|kol|thanh_vien|moi|bot_nghi
    },
    "noi_dung":      str,
    "ma_nhac_den":   list,   # ["HPG","SSI"] — regex mã VN 3 ký tự in hoa, lọc từ khóa
    "tuong_tac":  {"like": int, "reply": int, "view": int, "share": int},
    "huong_ho":      str,    # mua|ban|trung_lap  (chiều khuyến nghị/PR)
    "sentiment":     None,   # điền sau ở mục 4, [-1,1]
    "co_dau_hieu_lai": False, # điền sau ở mục 5
}

import re
# Mã VN: 3 ký tự in hoa (HOSE/HNX); lọc nhiễu từ viết tắt thường gặp.
_MA_RE = re.compile(r"\b([A-Z]{3})\b")
_STOP_MA = {"VND","USD","CTG","GDP","CPI","FED","ROE","ROA","EPS","NĐT","CTY","HĐQT","BCT","VAS","IFR"}
def trich_ma(text: str) -> list[str]:
    return sorted({m for m in _MA_RE.findall(text) if m not in _STOP_MA})
```

### 2.3 Collector forum/báo VN (Fireant, F247, Vietstock, CafeF, 24hMoney, VnEconomy, TNCK)

```python
# $HOME\.venv\Scripts\python.exe
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

async def cao_trang(url: str, render_js: bool = True, wait: str | None = None) -> str:
    """Cào 1 URL → trả markdown sạch. Forum SPA (Fireant) cần render_js=True."""
    cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_for=wait,            # vd "css:.comment-item" cho trang JS
        page_timeout=30000,
    )
    async with AsyncWebCrawler(headless=True) as crawler:
        res = await crawler.arun(url=url, config=cfg)
        return res.markdown if res.success else ""

# Cấu hình nguồn: KHÔNG hardcode CSS selector (dễ vỡ) — lấy markdown rồi để LLM/parse bóc.
NGUON_VN = {
    "fireant":   {"loai": "forum", "url": "https://fireant.vn/ma-chung-khoan/{ma}", "render_js": True},
    "vietstock": {"loai": "forum", "url": "https://finance.vietstock.vn/{ma}/tin-moi-nhat.htm", "render_js": True},
    "f247":      {"loai": "forum", "url": "https://f247.com/search?q={ma}", "render_js": True},
    "cafef":     {"loai": "news",  "url": "https://cafef.vn/tim-kiem.chn?keywords={ma}", "render_js": False},
    "24hmoney":  {"loai": "news",  "url": "https://24hmoney.vn/search?q={ma}", "render_js": True},
    "vneconomy": {"loai": "news",  "url": "https://vneconomy.vn/tim-kiem.htm?q={ma}", "render_js": False},
    "tnck":      {"loai": "news",  "url": "https://www.tinnhanhchungkhoan.vn/tim-kiem/?q={ma}", "render_js": False},
}
# ⚠️ URL pattern thay đổi theo thời gian → dùng skill firecrawl-map hoặc kiểm tay trước khi chạy hàng loạt.

async def thu_thap_ma(ma: str, nguon: str) -> dict:
    cfg = NGUON_VN[nguon]
    md = await cao_trang(cfg["url"].format(ma=ma.lower()), render_js=cfg["render_js"])
    # Bóc bài/bình luận bằng LLM (xem mục 4.3) → list item theo ITEM_SCHEMA.
    return {"nguon": nguon, "loai": cfg["loai"], "ma": ma, "markdown": md}
```

> **Mẹo bóc nội dung:** thay vì viết parser CSS cho từng site (vỡ liên tục), đưa markdown crawl4ai cho **LLM trích cấu trúc** (skill `firecrawl-agent` hoặc LLM nội bộ) theo `ITEM_SCHEMA`. Bền hơn nhiều với forum VN hay đổi giao diện.

### 2.4 Telegram room phím hàng — KHÔNG cần telethon

```python
# Bản xem public của kênh Telegram: https://t.me/s/<ten_kenh> → HTML tĩnh, crawl4ai cào thẳng.
async def cao_telegram_public(ten_kenh: str) -> str:
    return await cao_trang(f"https://t.me/s/{ten_kenh}", render_js=False)

# Cần lịch sử sâu / kênh không bật preview → telethon (ĐÃ cài v1.44; cần TELEGRAM_API_ID/HASH
# từ my.telegram.org). Chỉ kênh/nhóm PUBLIC, không đụng tin nhắn cá nhân (ToS + pháp lý — mục 2.6).
```

### 2.5 Facebook / Zalo group kín — chiến lược A + B + C (KHÔNG dùng credential cá nhân)

Group FB/Zalo kín **không cào tự động hợp lệ được** (login-gated, Zalo không có API, tự động hóa nick cá nhân vi phạm ToS → rủi ro khóa nick thật). **Không đưa tài khoản cá nhân cho bot.** Thay vào đó dùng 3 hướng bổ sung nhau:

- **A. Bắt "tiếng vọng" công khai (chính).** Nội dung nhóm kín thường rò ra kênh công khai trong vài giờ (Telegram public, F247, ảnh chụp trên Fireant, comment CafeF) → cào các kênh CÔNG KHAI này (mục 2.3–2.4) vẫn bắt được tín hiệu phối hợp/đội lái. Trễ vài giờ, sót một phần — chấp nhận được.
- **B. Analyst nhập tay sự kiện lớn.** Là thành viên nhóm → khi thấy hô hàng rần rộ / úp bô / tin đồn mạnh, điền vào template chuẩn; loader nạp vào pipeline buzz/đội lái:
  - Template: `templates/tin_hieu_fb_zalo.md` (mỗi tín hiệu 1 khối `=== TÍN HIỆU === … === HẾT ===`).
  - Loader: `templates/nhap_tay_loader.py` → `doc_tin_hieu(path)` trả `list[dict]` đúng `ITEM_SCHEMA` (tự bắt mã, ẩn danh tác giả theo NHÓM, cờ `co_dau_hieu_lai` từ cảm nhận analyst).
  - Chỉ nhập **sự kiện lớn**, không cần mọi tin. Không ghi tên người cụ thể (riêng tư).
- **C. Chỉ Fanpage / KOL CÔNG KHAI.** Theo Page/KOL công khai (crawlable hợp lệ) thay vì group kín — KOL lớn thường đăng công khai trước, group kín chỉ nhắc lại.

> **Tùy chọn hạn chế (D):** chỉ khi thật cần, dùng `firecrawl-interact` với **phiên do chính anh đăng nhập** để xem nội dung anh được phép thấy — không headless, không lưu credential, dùng lẻ tẻ. Vẫn xám ToS → ưu tiên A/B/C.
> → Trong report luôn **ghi rõ** lớp FB/Zalo là điểm mù một phần, không suy diễn lấp chỗ trống.

### 2.6 Tần suất, lưu trữ, tuân thủ

```
Tần suất:
  - Phiên giao dịch (9h–15h) mã/room nóng: 15–30 phút/lần.
  - Forum/báo thường: 2–4 giờ/lần. Backfill lịch sử: batch hằng ngày.
Tuân thủ:
  - Chỉ nguồn CÔNG KHAI. Không cào tin nhắn cá nhân/nhóm kín không được phép.
  - Tên người dùng cá nhân → LƯU DẠNG HASH; chỉ giữ chỉ tiêu tổng hợp.
  - Tôn trọng robots.txt + rate-limit; xóa raw text >30 ngày, giữ metric tổng hợp.
```

---

## 3. crawl4ai vs /last30days — dùng cái nào? (đánh giá theo yêu cầu)

| Tiêu chí | **crawl4ai** | **/last30days** |
|---|---|---|
| Phủ **forum VN** (F247/Fireant/Vietstock/Bovagau) | ✅ Cào thẳng được | ❌ Không chạm tới |
| Phủ **báo VN** (CafeF/24hMoney/VnEconomy/TNCK) | ✅ | ❌ (chỉ "web" chung, không sâu) |
| Phủ **KOL YouTube/TikTok** | ⚠️ Khó (anti-bot, JS nặng) | ✅ Có engagement video, gọn |
| Phủ **X/Reddit/HN/GitHub** | ✅ nhưng VN gần như rỗng | ✅ thế mạnh — nhưng **ít data về CP VN** |
| **FB/Zalo group kín** | ❌ | ❌ (cả hai mù) |
| Recency 30 ngày, đa nền sẵn | ⚠️ tự dựng | ✅ sẵn, nhanh |
| Kiểm soát/độ sâu/lưu trữ riêng | ✅ Toàn quyền | ❌ Hộp đen |
| Tiếng Việt + lóng | ✅ (lấy raw rồi tự NLP) | ⚠️ Tùy nguồn index |

**Kết luận (cho TTCK VN):**
1. **crawl4ai = công cụ CHÍNH** cho lõi tín hiệu VN: forum + báo (nơi chứa buzz lẻ và dấu hiệu đội lái). Đây là alpha venue mà last30days **không với tới**.
2. **/last30days = bổ trợ** cho **lớp KOL video (YouTube/TikTok)** và **cross-check nhanh** độ nóng đa nền — chỗ crawl4ai yếu vì anti-bot.
3. **Cả hai đều mù FB/Zalo kín** → mục 2.5 áp dụng.
4. Quy trình khuyến nghị: **crawl4ai dựng dữ liệu forum/báo theo mã → /last30days quét nhanh lớp video + tâm lý cross-platform → hợp nhất** ở mục 6. Không thay thế nhau, bổ sung nhau.

---

## 4. NLP tiếng Việt cho tin tài chính

### 4.1 Lexicon lóng chứng khoán VN (cốt lõi — VADER/FinBERT KHÔNG hiểu)

```python
# Cụm lóng → cực tính [-1..+1]. Đây là "kiến thức chiến trường", quan trọng hơn model.
LEXICON_CK_VN = {
    # --- Hô MUA / hưng phấn (+) ---
    "múc": 0.8, "kê": 0.6, "tất tay": 0.9, "all in": 0.9, "full cổ": 0.8, "full margin": 0.7,
    "gom": 0.5, "xúc": 0.7, "vào hàng": 0.6, "kèo thơm": 0.7, "hàng nóng": 0.5, "sóng": 0.5,
    "tím": 0.7, "trần": 0.6, "bốc đầu": 0.7, "break": 0.5, "về bờ": 0.4, "x2": 0.6, "x3": 0.7,
    "gồng lãi": 0.4, "đu theo lái": 0.3,
    # --- Hô BÁN / hoảng loạn (−) ---
    "xả": -0.8, "đạp": -0.7, "úp bô": -0.9, "đu đỉnh": -0.8, "bắt dao": -0.7, "bắt dao rơi": -0.8,
    "cháy tài khoản": -0.9, "call margin": -0.7, "force sell": -0.8, "giải chấp": -0.8,
    "gãy": -0.6, "thủng": -0.6, "sàn": -0.6, "lau sàn": -0.8, "kẹp": -0.6, "gồng lỗ": -0.6,
    "cắt lỗ": -0.5, "tháo chạy": -0.8, "phân phối": -0.6, "ra hàng": -0.5, "đẩy bô": -0.8,
    # --- Trung tính / cảnh báo thao túng (gắn cờ, không cộng cực tính) ---
    "lái": 0.0, "đội lái": 0.0, "hô": 0.0, "phòng hô": 0.0, "room": 0.0, "phím": 0.0,
    "cá mập": 0.0, "tây": 0.0, "tay to": 0.0, "bigboy": 0.0, "con hàng": 0.0,
}
# Cờ thao túng (xuất hiện → tăng nghi ngờ đội lái, mục 5):
TU_KHOA_LAI = ["hô", "phím", "kèo", "room", "đội lái", "lái kéo", "bắt đáy ngay",
               "không mua là tiếc", "cam kết", "target x", "về bờ chắc chắn", "tất tay luôn"]
```

### 4.2 Tiền xử lý văn bản VN (teencode, dấu, viết tắt)

```python
TEENCODE = {"ck": "chứng khoán", "cp": "cổ phiếu", "tt": "thị trường", "ace": "anh chị em",
            "nh": "ngân hàng", "bđs": "bất động sản", "kqkd": "kết quả kinh doanh",
            "lnst": "lợi nhuận sau thuế", "ko": "không", "k": "không", "dc": "được",
            "vol": "thanh khoản", "ae": "anh em", "bác": "bạn"}

def chuan_hoa(text: str) -> str:
    t = text.lower()
    for k, v in TEENCODE.items():
        t = re.sub(rf"\b{k}\b", v, t)
    return t
# Lưu ý: KHÔNG bỏ dấu nếu dùng LLM/underthesea (mất nghĩa). Bỏ dấu chỉ khi match lexicon thô.
```

### 4.3 Ba lựa chọn scoring (xếp theo độ phù hợp VN)

```python
# CHÍNH — LLM-based: xử lý lóng/teencode/châm biếm/đảo nghĩa tốt nhất, KHÔNG cần lib ngoài.
def sentiment_llm(text: str, ma: str | None = None) -> dict:
    """Trả {'diem': float[-1,1], 'nhan': 'mua/ban/trung_lap', 'la_ho_lai': bool, 'ly_do': str}."""
    from src.providers.base import get_llm
    ctx = f"Mã: {ma}\n" if ma else ""
    prompt = (f"{ctx}Đây là bình luận chứng khoán VN (có lóng, teencode). "
              f"Trả JSON: {{\"diem\": <-1..1>, \"nhan\": <\"mua\"|\"ban\"|\"trung_lap\">, "
              f"\"la_ho_lai\": <true nếu có dấu hiệu hô hàng/làm giá>, \"ly_do\": <1 câu>}}.\n"
              f"Văn bản: {text[:1000]}")
    import json
    return json.loads(get_llm().invoke(prompt).content)

# PHỤ — Lexicon thô: nhanh, offline, no-GPU; dùng lọc sơ bộ khối lượng lớn trước khi gọi LLM.
def sentiment_lexicon(text: str) -> dict:
    t = chuan_hoa(text)
    diem = [v for k, v in LEXICON_CK_VN.items() if k in t and v != 0.0]
    co_lai = any(kw in t for kw in TU_KHOA_LAI)
    s = sum(diem) / len(diem) if diem else 0.0
    return {"diem": max(-1.0, min(1.0, s)), "la_ho_lai": co_lai}

# OFFLINE — underthesea: ĐÃ cài (v9.5). Dùng word_tokenize() để TÁCH TỪ tiếng Việt trước khi
#   match lexicon (chính xác hơn split thô). LƯU Ý: underthesea.sentiment() là model GENERAL,
#   YẾU với tài chính (test thực tế: "cổ phiếu này tốt, nên mua" → trả 'neutral') → KHÔNG dùng
#   làm scorer CK; chỉ dùng tokenize. Chấm cảm xúc CK vẫn để LLM-based + lexicon.
from underthesea import word_tokenize, sentiment   # đã cài
def tach_tu(text: str) -> list[str]:
    return word_tokenize(text)                       # vd "đội lái kéo trần" → tách đúng cụm

# OFFLINE MẠNH — PhoBERT (ĐÃ cài torch 2.12 + transformers 5.12, chạy CPU). Có sẵn đầu sentiment
#   3 lớp VN qua model cộng đồng. Test thực tế MẠNH hơn underthesea (hiểu cả lóng):
#     "cổ phiếu này tốt, nên mua" → POS 0.99   (underthesea trả 'neutral' — SAI)
#     "mã này sắp úp bô, tháo chạy đi" → NEG 0.99 (hiểu "úp bô")
_phobert = None
def get_phobert():
    global _phobert
    if _phobert is None:
        from transformers import pipeline
        _phobert = pipeline("text-classification", model="wonrax/phobert-base-vietnamese-sentiment")
    return _phobert

def sentiment_phobert(text: str) -> dict:
    r = get_phobert()(text[:256])[0]                      # PhoBERT-base giới hạn 256 token
    diem = {"POS": 1.0, "NEU": 0.0, "NEG": -1.0}[r["label"]] * r["score"]
    return {"diem": diem, "nhan": {"POS": "mua", "NEU": "trung_lap", "NEG": "ban"}[r["label"]]}
# DÙNG: scorer OFFLINE cho BATCH lớn (rẻ, nhanh, không tốn API). LƯU Ý: model review-domain,
#   KHÔNG fine-tune riêng tài chính → ngữ cảnh phức tạp (châm biếm, đảo nghĩa, ngữ cảnh theo mã)
#   vẫn để LLM-based. Thứ tự dùng: lexicon lọc thô → PhoBERT batch → LLM cho ca khó/nghi lái.
```

> **Khuyến nghị (3 tầng, cân chi phí/độ chính xác cho khối lượng forum VN lớn):**
> **lexicon** lọc thô (rẻ nhất) → **PhoBERT** chấm batch offline (không tốn API) → **LLM-based** chỉ cho ca khó: |điểm| thấp/mâu thuẫn, châm biếm, hoặc **nghi hô lái** (cần hiểu ngữ cảnh + ý đồ).

---

## 5. PHÁT HIỆN ĐỘI LÁI / PHÍM HÀNG (trọng tâm VN)

### 5.1 Vòng đời một chiến dịch làm giá (Wyckoff phiên bản penny VN)

```
GĐ1 Gom hàng (âm thầm)   : buzz THẤP, giá đi ngang vùng đáy, KL nhỏ tăng dần.
GĐ2 Kéo (markup)         : giá tăng dần/tăng trần liên tiếp, buzz BẮT ĐẦU nóng, "sóng".
GĐ3 Hô hàng (phân phối)  : buzz BÙNG NỔ đa kênh, hô 1 chiều "múc/về bờ/x2", target cao,
                           chê người thận trọng → lùa lẻ vào để xả.
GĐ4 Xả / úp bô (markdown): giá quay đầu/sàn liên tiếp, room VẪN hô để có người đỡ → lẻ kẹp đỉnh.
```
→ **Buzz cực đại thường rơi vào GĐ3–4, tức ĐỈNH phân phối, không phải điểm mua.** Đây là cái bẫy số 1 với NĐT lẻ VN.

### 5.2 Tín hiệu định lượng nhận diện

```python
import numpy as np, pandas as pd

def phat_hien_doi_lai(
    df_buzz: pd.DataFrame,      # cột: ngay, ma, msg_count, unique_authors
    df_gia: pd.DataFrame,       # cột: ngay, ma, close, volume  (từ DataPro)
    df_text: pd.DataFrame,      # cột: ma, noi_dung, tac_gia_tuoi_tk_ngay, huong_ho
) -> dict:
    """Chấm điểm nghi ngờ làm giá [0..100] + cờ. Càng cao càng nên NÉ."""
    flags, score = [], 0.0

    # 1) Buzz đột biến trên nền thấp (z-score)
    z = (df_buzz["msg_count"] - df_buzz["msg_count"].rolling(30, min_periods=5).mean()) \
        / df_buzz["msg_count"].rolling(30, min_periods=5).std().replace(0, np.nan)
    if z.iloc[-1] > 3:
        score += 25; flags.append("Buzz đột biến >3σ")

    # 2) Phân kỳ: buzz bùng nổ NHƯNG giá đã tăng mạnh trước đó (phân phối)
    ret_20 = df_gia["close"].pct_change(20).iloc[-1]
    if z.iloc[-1] > 2 and ret_20 > 0.30:
        score += 25; flags.append(f"Buzz nóng sau khi giá đã +{ret_20:.0%}/20 phiên → nghi phân phối")

    # 3) Đồng loạt nhiều kênh + nội dung copy-paste (coordination)
    trung_lap = df_text["noi_dung"].str.slice(0, 80).duplicated().mean()
    if trung_lap > 0.3:
        score += 20; flags.append(f"{trung_lap:.0%} nội dung copy-paste → có tổ chức")

    # 4) Tỷ lệ tài khoản mới/bot cao
    ty_le_moi = (df_text["tac_gia_tuoi_tk_ngay"] < 30).mean()
    if ty_le_moi > 0.4:
        score += 15; flags.append(f"{ty_le_moi:.0%} tài khoản <30 ngày tuổi")

    # 5) Hô 1 chiều (chỉ mua, bịt rủi ro)
    ty_le_mua = (df_text["huong_ho"] == "mua").mean()
    if ty_le_mua > 0.85:
        score += 15; flags.append(f"{ty_le_mua:.0%} hô MUA một chiều")

    return {"diem_nghi_lai": min(score, 100), "co_dau_hieu_lai": score >= 50, "co": flags}
```

### 5.3 Checklist đỏ + cách dùng PHÒNG THỦ

| Dấu hiệu | Ngưỡng cảnh báo |
|---|---|
| Buzz z-score | > 3σ trên penny/midcap thanh khoản thấp |
| Giá đã chạy trước khi buzz nóng | +30%/20 phiên rồi mới "hô" |
| Nội dung copy-paste nhiều kênh | > 30% trùng |
| Tài khoản mới/bot | > 40% < 30 ngày |
| Hô 1 chiều mua | > 85% |
| Mã KHÔNG có cơ bản đỡ / tin đồn không kiểm chứng | có |

**Dùng phòng thủ (đây là mục tiêu chính, không phải để đu theo):**
- `diem_nghi_lai ≥ 50` → **NÉ**, không mua bằng tiền thật dù buzz hấp dẫn.
- Đang cầm sẵn → buzz cực đại + giá xa nền = vùng **canh thoát**, không gom thêm.
- Tuyệt đối không mua ở GĐ3–4. "Hô càng to, rủi ro úp bô càng lớn."
- Chéo với [[regulatory-knowledge]]: cảnh báo của UBCK/HOSE về giao dịch bất thường, và [[sentiment-analysis]] (margin căng khuếch đại giải chấp).

---

## 6. Buzz-factor định lượng theo mã

### 6.1 Buzz metrics (giữ phương pháp gốc, feed dữ liệu VN)

```python
def buzz_metrics(df: pd.DataFrame, window: str = "1D") -> pd.DataFrame:
    """df: cột thoi_gian, ma, noi_dung, tac_gia_id, tuong_tac_tong."""
    df["thoi_gian"] = pd.to_datetime(df["thoi_gian"])
    g = df.set_index("thoi_gian").sort_index().resample(window).agg(
        msg_count=("noi_dung", "count"),
        unique_authors=("tac_gia_id", "nunique"),
        engagement=("tuong_tac_tong", "sum"),
    )
    rm = g["msg_count"].rolling(30, min_periods=5).mean()
    rs = g["msg_count"].rolling(30, min_periods=5).std().replace(0, np.nan)
    g["buzz_zscore"] = (g["msg_count"] - rm) / rs
    return g
# unique_authors quan trọng ở VN: lọc bot/spam thổi msg_count giả.
```

### 6.2 Weighted sentiment phân tầng nguồn (VN-calibrated)

```python
TRONG_SO_NGUON = {       # uy tín cao → trọng số cao; room hô/nhóm kín → thấp
    "moi_gioi": 3.0, "kol": 2.0, "thanh_vien": 1.0, "moi": 0.2, "bot_nghi": 0.0,
}
TRONG_SO_KENH = {        # đóng góp IC lịch sử + chất lượng thông tin (hiệu chỉnh dần)
    "cafef": 0.20, "vneconomy": 0.15, "tnck": 0.15, "24hmoney": 0.10,
    "fireant": 0.15, "vietstock": 0.10, "f247": 0.08, "telegram": 0.05, "bovagau": 0.02,
}
```

### 6.3 Kiểm định IC / ICIR (phương pháp phổ quát — giữ)

```python
from scipy.stats import spearmanr
def ic(factor: pd.Series, fwd_ret: pd.Series) -> float:
    a = pd.concat([factor, fwd_ret], axis=1).dropna()
    return spearmanr(a.iloc[:, 0], a.iloc[:, 1])[0] if len(a) >= 5 else np.nan
def icir(ic_series: pd.Series) -> float:
    return ic_series.mean() / ic_series.std() if ic_series.std() > 0 else np.nan
```

| Chỉ tiêu | Yếu | Dùng được | Mạnh |
|---|---|---|---|
| \|IC\| | <0,03 | 0,03–0,08 | >0,08 |
| ICIR | <0,3 | 0,3–0,8 | >0,8 |

> **Cảnh báo VN:** IC sentiment MXH thường thấp (~0,03–0,06) và **suy giảm nhanh** do nhiễu đội lái. Dùng làm **factor bổ trợ**, không phải factor chính. Re-test IC định kỳ; orthogonalize với momentum/thanh khoản (xem [[factor-research]], [[multi-factor]]) để tránh đếm trùng — buzz tương quan cao với momentum giá ở penny VN.

---

## 7. Tích hợp pipeline

```bash
# .env (chỉ khi dùng API; mặc định ưu tiên crawl4ai không cần key)
SENTIMENT_MODEL=llm          # llm | phobert | lexicon  (cả 3 ĐÃ sẵn sàng; underthesea: tokenize)
TELEGRAM_API_ID=             # chỉ nếu cần telethon (ĐÃ cài) cho lịch sử sâu; lấy ở my.telegram.org
TELEGRAM_API_HASH=
```

```sql
-- Bảng factor sentiment MXH (DuckDB/SQLite)
CREATE TABLE social_factor_vn (
    ngay         DATE NOT NULL,
    ma           VARCHAR(10) NOT NULL,
    nguon        VARCHAR(20) NOT NULL,
    sentiment    FLOAT,         -- [-1,1]
    buzz_zscore  FLOAT,
    msg_count    INTEGER,
    diem_nghi_lai FLOAT,        -- [0,100] điểm nghi đội lái
    uy_tin_tg    VARCHAR(20),
    PRIMARY KEY (ngay, ma, nguon)
);
```

Liên kết: [[sentiment-analysis]] (tâm lý toàn TT), [[regulatory-knowledge]] (giải chấp/cảnh báo UBCK), [[etf-analysis]] (dòng ETF), [[factor-research]]/[[multi-factor]] (kiểm định factor).

---

## 8. Lưu ý & giới hạn (VN)

1. **MXH là factor BỔ TRỢ**, không phải tín hiệu live-trade. IC thấp, decay nhanh.
2. **Đội lái là rủi ro trung tâm**: cùng một buzz có thể là tiền thật HOẶC bẫy úp bô → luôn chạy mục 5 trước khi diễn giải bullish.
3. **Điểm mù dữ liệu**: FB/Zalo group kín không cào hợp lệ được → nêu rõ, không lấp bằng suy đoán.
4. **Buzz cực đại ≠ điểm mua** — thường là đỉnh phân phối ở penny/midcap.
5. **crawl4ai (forum/báo) + /last30days (KOL video)** bổ sung nhau; chọn đúng việc (mục 3).
6. **Chỉ nguồn công khai, hash danh tính, tôn trọng ToS/robots**; xóa raw >30 ngày.
7. **Lóng/teencode** đổi nhanh → cập nhật `LEXICON_CK_VN` định kỳ; ưu tiên LLM-based cho ngữ cảnh phức tạp.

---

*Phiên bản: v2.0-VN | Cập nhật: 2026-06-19 | Phạm vi: nghiên cứu định lượng / phát hiện làm giá (KHÔNG dùng làm tín hiệu giao dịch trực tiếp). Kế thừa khung gốc himself65/finance-skills, Việt hóa toàn diện cho TTCK VN.*


## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)

1. **Không bịa/cook số liệu.** Mọi số tài chính phải có nguồn thật. Luôn **audit nhanh, cross-check tối thiểu 2 nguồn uy tín** (vd `cafef.vn`, `vietstock.vn`) — dùng **crawl4ai** cào số rồi đối chiếu; nếu nguồn lệch nhau thì nêu rõ, không chọn bừa.
2. **Nếu DataPro VÀ vnstock đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
