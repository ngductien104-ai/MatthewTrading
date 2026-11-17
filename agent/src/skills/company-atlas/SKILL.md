---
name: company-atlas
description: Dựng hồ sơ sâu (L3) một doanh nghiệp toàn cầu cho Atlas từ báo cáo thường niên gốc (10-K, 20-F, Annual/Integrated Report, Business Report) — lịch sử, mô hình kinh doanh, đầu vào và nhà cung cấp, đầu ra và khách hàng, vị thế so với đối thủ trên/cùng/dưới phân khúc, số 5 năm. Dùng khi anh hỏi sâu về một doanh nghiệp nước ngoài, so sánh hai doanh nghiệp, hoặc khi /atlas hoc-tiep gặp mục loại dn.
category: research
---
# Company Atlas — hồ sơ sâu một doanh nghiệp (L3)

Luật gốc: `Obsidian/MatthewObsidian/25_Atlas/_HeThong/KIEN_TRUC.md`. Doanh nghiệp **Việt Nam** không đi đường này cho phần BCTC — dùng Phase 0 `agent/scripts/evidence_pack.py` theo CLAUDE.md; skill này chỉ thêm thẻ Atlas cho nó.

## Bước 1 — Lấy tài liệu gốc

| Nơi niêm yết | Tài liệu | Lấy ở đâu |
|---|---|---|
| Mỹ | 10-K (+ 10-Q mới nhất) | SEC EDGAR — xem skill `edgar-sec-filings` |
| Nước ngoài có ADR ở Mỹ (TSMC, ASML, Toyota…) | 20-F hoặc 40-F | SEC EDGAR |
| Nhật | 有価証券報告書 (Yuho) / Integrated Report tiếng Anh | trang IR công ty, EDINET |
| Hàn | Business Report (사업보고서) | DART, trang IR |
| Châu Âu | Annual Report / Universal Registration Document | trang IR công ty |
| Trung Quốc, Hồng Kông | Annual Report | HKEXnews, CNINFO, trang IR |
| Tư nhân | không có BCTN — thông cáo, hồ sơ gọi vốn, báo chí | ghi nhãn `[thứ cấp]` |

Lưu PDF/HTML vào `_atlas_raw/<DN>/`. Tạo `25_Atlas/Nguon/<DN>_<loại>_<năm>.md` từ `Templates/Nguon.md`.

## Bước 2 — Đọc theo thứ tự này

Cấu trúc 10-K / 20-F (BCTN nơi khác có mục tương đương):

1. **Item 1 Business** (20-F: Item 4) — mảng kinh doanh, sản phẩm, khách hàng, nhà cung cấp, đối thủ, nhà máy. Đây là nguồn chính của mô hình kinh doanh và quan hệ chuỗi.
2. **Item 1A Risk Factors** (20-F: Item 3.D) — tìm *phụ thuộc*: một khách hàng, một nhà cung cấp, một quốc gia. Rủi ro doanh nghiệp tự khai là bản đồ điểm nghẽn.
3. **Item 2 Properties** — nhà máy đặt ở đâu → toạ độ địa lý của chuỗi.
4. **Item 7 MD&A** (20-F: Item 5) — vì sao doanh thu/biên thay đổi, capex, kế hoạch.
5. **Thuyết minh Segment information** — doanh thu theo mảng và theo địa lý; **khách hàng >10% doanh thu** (bắt buộc công bố theo ASC 280 / IFRS 8).
6. **Thuyết minh Commitments / Purchase obligations** — cam kết mua dài hạn hé lộ nhà cung cấp chiến lược.

Số nào ghi vào thẻ cũng kèm **số trang** trong ghi chú Nguồn.

Ba bài học từ hồ sơ đầu tiên (TSMC, 11/2026):

- **Đọc thuyết minh trước khi viết mục khách hàng.** Câu tóm tắt ở Risk Factors ("largest customer 25%, 22%, 19%") không nói đó có phải cùng một khách qua các năm; bảng trong thuyết minh Segment/Major customers (Customer A, B, C) mới cho thấy ai lên ai xuống.
- **Báo cáo thường không nêu tên khách hàng và nhà cung cấp.** Quan hệ `mua_tu` / `ban_cho` phải lấy từ báo cáo của phía bên kia; ghi việc đó vào `HANG_DOI.md` thay vì đoán tên.
- **Chuỗi 5 năm cần hai bản báo cáo** (mỗi bản 20-F/10-K có 3 năm). Lấy bản của 2 năm trước, và kiểm năm trùng nhau khớp từng số.

Cách lấy file: trang nhà đầu tư thường chặn `curl`; WebFetch tải được PDF dưới 10 MB và lưu vào thư mục `tool-results` của phiên — chép sang `_atlas_raw/<DN>/`, đọc bằng `fitz` (venv dự án, chạy `python -I`).

Doanh nghiệp Hàn Quốc: đọc thẳng báo cáo kinh doanh (사업보고서) trên DART, không cần bản tiếng Anh.
1. Tìm số tiếp nhận `rcpNo` bằng POST `https://dart.fss.or.kr/dsab007/detailSearch.ax`, với `textCrpNm=<tên tiếng Hàn>` và `publicType=A001`.
2. Lấy mục lục: `dsaf001/main.do?rcpNo=<số>`. Mỗi mục có `dcmNo`, `eleId`, `offset`, `length`.
3. Tải từng mục bằng `curl` qua `report/viewer.do?rcpNo=&dcmNo=&eleId=&offset=&length=&dtd=dart4.xsd`, lưu vào `_atlas_raw/<DN>/`.
4. Đổi sang text với bảng thành dòng ` | `.

Các mục cần đọc:
- II: mô tả kinh doanh, nguyên liệu, thị phần;
- thuyết minh "영업부문": khách hàng lớn trên 10%;
- thuyết minh "매출액": doanh thu theo sản phẩm và vùng.

Báo cáo HTML không có số trang, nên trích theo mục. Bài học từ SK Hynix: cùng mẫu báo cáo Hàn Quốc, Samsung nêu tên khách và nhà cung cấp, SK Hynix thì không. Nêu tên là lựa chọn của từng hãng.

## Bước 3 — Viết thẻ `DoanhNghiep/<Tên>.md`

Theo `Templates/DoanhNghiep.md`, đủ 9 mục. Lưu ý:

- **Mục 5 Vị thế & phân khúc** phải trả lời được ba câu: cùng bậc với ai · ai ở bậc trên và *cái gì* giữ họ ở đó · ai ở bậc dưới và *cái gì* ngăn họ leo lên. So sánh bằng thứ đo được (giá bán bình quân, biên gộp, thị phần, công nghệ/tiến trình, tuổi thương hiệu), không bằng tính từ.
- **Mục 6** bảng 5 năm: doanh thu, biên gộp, LN ròng, capex — cùng đơn vị tiền gốc của báo cáo.
- `mua_tu` / `ban_cho` chỉ ghi quan hệ có trong tài liệu gốc hoặc nguồn thứ cấp nêu đích danh.
- Doanh nghiệp đối tác chưa có thẻ: cứ ghi tên, `schema.py` sẽ liệt kê "cần tạo thẻ" — đó là hàng đợi tự nhiên.
- `cap_do: L3`, `han_xem_lai` = ngày dự kiến ra BCTN năm sau.

## Bước 4 — So sánh hai doanh nghiệp (khi anh hỏi "A với B ai hơn")

Cả hai phải có thẻ ≥ L2. Trả lời theo khung: họ có cùng một cuộc chơi không (phân khúc, khách hàng) → nếu khác bậc thì khác ở đâu và vì sao → số chứng minh (giá bán, biên, vòng quay, ROIC) → mỗi bên thắng ở điều kiện nào. Thiếu thẻ thì làm thẻ trước, không so bằng trí nhớ.

## Đóng phiên

Giống `industry-atlas`: `schema` → `build` → `status`, cập nhật `HANG_DOI.md`, `NHAT_KY_HOC.md`, `Atlas_Home.md`.
