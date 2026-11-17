---
name: industry-atlas
description: Nghiên cứu một ngành toàn cầu và ghi vào Atlas (vault Obsidian 25_Atlas) — ngành làm gì, quy mô, thị trường ngách, chuỗi giá trị đầu vào→vận hành→đầu ra, quốc gia nào mạnh ở mắt xích nào, doanh nghiệp đại chúng và tư nhân, thang phân khúc cạnh tranh, mắt xích Việt Nam. Dùng khi anh nhắc tới một ngành, hỏi "ngành X gồm những ai", hoặc khi chạy /atlas hoc-tiep gặp mục loại nganh.
category: research
---
# Industry Atlas — quy trình nghiên cứu một ngành

Luật gốc: `Obsidian/MatthewObsidian/25_Atlas/_HeThong/KIEN_TRUC.md`. Đọc nó trước nếu chưa đọc trong phiên.

## Nguyên tắc không thương lượng

- Trí nhớ của model chỉ dùng để **biết phải tìm gì**. Số chỉ vào ghi chú khi có nguồn + năm + nhãn `[gốc]` / `[thứ cấp]` / `[ước tính]`. Không có thì ghi `chưa có`.
- Hai nguồn lệch nhau thì ghi cả hai và nêu lý do lệch (khác định nghĩa thị trường là nguyên nhân thường gặp nhất), không lấy trung bình.
- Mắt xích VN lấy số theo skill `data-routing` (DataPro + VNDIRECT MCP), không dùng nguồn khác thay.

## Nguồn chuẩn theo loại thông tin

| Cần biết | Tìm ở đâu trước | Nhãn |
|---|---|---|
| Quy mô thị trường, tăng trưởng | hiệp hội ngành / cơ quan thống kê (vd bán dẫn: WSTS, SIA, SEMI; thép: worldsteel; dầu khí: IEA, EIA; dệt may: WTO, ITC Trade Map) | `[thứ cấp]` |
| Thị phần | BCTN của doanh nghiệp đầu ngành (mục Competition / Market position) rồi mới tới công ty nghiên cứu | `[gốc]` / `[thứ cấp]` |
| Ai bán cho ai | mục Customers, Suppliers, Concentration of risk trong 10-K / 20-F / BCTN; danh sách nhà cung cấp doanh nghiệp tự công bố | `[gốc]` |
| Biên lợi nhuận theo mắt xích | BCTC của 2–3 doanh nghiệp thuần mắt xích đó | `[gốc]` rồi `[ước tính]` |
| Doanh nghiệp tư nhân, quỹ PE/VC | thông cáo gọi vốn, báo chí tài chính, website quỹ | `[thứ cấp]` |
| Vốn hoá, doanh thu nhanh | `yfinance` (venv dự án) cho mã nước ngoài | `[thứ cấp]` |
| Chính sách, trợ cấp, hạn chế xuất khẩu | văn bản cơ quan ban hành | `[gốc]` |

Tra web bằng `firecrawl-search` / `firecrawl-scrape` hoặc crawl4ai (`$HOME\.venv`). PDF gốc lưu `_atlas_raw/<tổ chức>/`, mỗi tài liệu đã đọc có một ghi chú trong `25_Atlas/Nguon/`.

## L1 — Thẻ ngành (một phần của phiên)

1. Xác định mã GICS 6 số trong `_HeThong/GICS.md`; tạo `Nganh/<mã>_<Tên>/<Tên>_MOC.md` từ `Templates/Nganh.md`.
2. Viết mục 1 (ngành làm gì) bằng lời thường, cho người chưa biết gì về ngành.
3. Lấy quy mô thị trường từ hiệp hội ngành + 2 nguồn thứ cấp đối chiếu.
4. Liệt kê 5–8 mắt xích theo thứ tự thượng nguồn → hạ nguồn; ghi vào `mat_xich` bằng slug không dấu (vd `thiet_ke_fabless`). **Tên mắt xích là khoá**: thẻ doanh nghiệp phải dùng đúng các slug này.
5. Top 10 doanh nghiệp (tên, quốc gia, mắt xích) — chưa cần thẻ riêng.
6. 5 quốc gia chủ chốt + vì sao mạnh.
7. Điền `cap_do: L1`, `cap_nhat`, `han_xem_lai` (+6 tháng), `nguon`.

## L2 — Bản đồ ngành (2–3 phiên)

1. `ChuoiGiaTri.md` — mỗi mắt xích một mục: làm gì · đầu vào · đầu ra · rào cản gia nhập · biên lợi nhuận điển hình · ai thống trị · điểm nghẽn.
2. `ThiTruongNgach.md` — các ngách đang vận hành, quy mô, tăng trưởng, ai dẫn đầu từng ngách.
3. `DiaLy.md` — ma trận quốc gia × mắt xích; vì sao lợi thế đó hình thành (tài nguyên, chính sách, cụm công nghiệp, nhân lực).
4. `CanhTranh.md` — thang phân khúc cao → thấp; với mỗi cặp bậc kề nhau: cái gì ngăn bậc dưới leo lên. Đây là chỗ trả lời câu kiểu "A với B ai đẳng cấp hơn, vì sao".
5. 20–30 thẻ `DoanhNghiep/` từ `Templates/DoanhNghiep.md`, đủ frontmatter, gồm cả doanh nghiệp tư nhân/nhà nước quan trọng. Ưu tiên phủ **mọi mắt xích** trước khi thêm tên thứ hai ở cùng mắt xích.
6. Điền quan hệ `mua_tu` / `ban_cho` / `doi_thu_*` — chỉ quan hệ có nguồn.
7. Mục 8 của `_MOC`: doanh nghiệp VN ở đâu trong chuỗi; liên kết sang `10_CoPhieu/<MÃ>` nếu vault đã có.
8. Nâng `cap_do: L2`.

## Đóng phiên

```bash
cd agent
../.venv/Scripts/python.exe -m src.atlas.schema
../.venv/Scripts/python.exe -m src.atlas.build     # có từ Giai đoạn 1
../.venv/Scripts/python.exe -m src.atlas.status
```

Sửa đến khi `schema` hết lỗi. Rồi cập nhật `_HeThong/HANG_DOI.md` (trạng thái + việc hở), thêm 3–5 dòng vào `NHAT_KY_HOC.md`, thêm ngành vào bảng ở `Atlas_Home.md`.

## Trả lời anh

Khi anh hỏi về ngành: trả lời bằng lời từ ghi chú trong vault, dẫn bản đồ `BanDo_<Tên>.html`, nói rõ cấp độ hiện tại (L1/L2) và phần nào còn hở. Không trộn kiến thức chưa có nguồn vào như thể đã kiểm.
