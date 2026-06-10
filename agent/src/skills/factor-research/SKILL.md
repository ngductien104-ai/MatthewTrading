---
name: factor-research
description: "Khung nghiên cứu nhân tố (factor) cho thị trường VN — phân tích IC/IR, backtest theo nhóm phân vị, kết hợp đa nhân tố, trung lập ngành theo ICB. Dùng cho đánh giá nhân tố cross-sectional trên rổ cổ phiếu .VN. Nguồn: DataPro (giá/KL/khối ngoại) + vnstock (cơ bản)."
category: analysis
---

# Khung nghiên cứu nhân tố (Việt Nam)

## Mục đích

Đánh giá có hệ thống sức mạnh dự báo của một hoặc nhiều nhân tố. Dùng kiểm định thống kê IC/IR và backtest theo nhóm phân vị để xác định nhân tố có khả năng chọn cổ phiếu hay không, từ đó sàng lọc và kết hợp nhân tố.

Tình huống áp dụng:
- Kiểm định hiệu lực nhân tố đơn (momentum, value, quality, volatility, **dòng tiền khối ngoại**...)
- Xác định trọng số kết hợp đa nhân tố
- Phân tích suy giảm nhân tố (IC thay đổi theo kỳ nắm giữ)
- So sánh nhân tố giữa các ngành/thị trường

## Quy trình

1. **Tính giá trị nhân tố**: tính exposure cho từng mã trên cross-section → xuất factor CSV (`index=date`, `columns=mã .VN`)
2. **Tính lợi suất**: lợi suất forward N ngày của từng mã → return CSV (cùng cấu trúc)
3. **Gọi tool `factor_analysis`**: truyền factor CSV, return CSV, thư mục output
4. **Diễn giải**: đánh giá hiệu lực theo IC/IR + backtest phân vị
5. **Sàng lọc/kết hợp**: giữ nhân tố hiệu lực, kết hợp đều trọng số hoặc theo IC

**Then chốt**: dòng (ngày) và cột (mã) của factor CSV và return CSV phải khớp CHÍNH XÁC. Lợi suất phải là forward return SAU ngày quan sát nhân tố (tránh nhìn trước).

## Tham số tool `factor_analysis`

| Tham số | Kiểu | Bắt buộc | Mặc định | Mô tả |
|------|------|------|------|------|
| factor_csv | string | Có | - | Đường dẫn CSV giá trị nhân tố |
| return_csv | string | Có | - | Đường dẫn CSV lợi suất |
| output_dir | string | Có | - | Thư mục output |
| n_groups | integer | Không | 5 | Số nhóm phân vị |

## File output

| File | Nội dung |
|------|------|
| ic_series.csv | Chuỗi IC theo ngày |
| ic_summary.json | IC trung bình, độ lệch chuẩn IC, IR, tỷ lệ IC > 0 |
| group_equity.csv | Đường vốn lũy kế từng nhóm phân vị |

## Chuẩn diễn giải IC/IR

| Chỉ tiêu | Ngưỡng | Diễn giải |
|------|------|------|
| IC trung bình | > 0,03 | Nhân tố có sức dự báo cơ bản |
| IC trung bình | > 0,05 | Sức dự báo mạnh |
| IC trung bình | > 0,10 | Cao bất thường → kiểm tra nhìn trước |
| IR (IC mean / IC std) | > 0,5 | Hiệu lực ổn định |
| IR | > 1,0 | Cực mạnh, rất hiếm |
| Tỷ lệ IC > 0 | > 55% | Hướng nhân tố ổn định |
| Tỷ lệ IC > 0 | < 50% | Hướng không ổn định, không dùng được |

Lưu ý: IC âm vẫn hữu ích (nhân tố nghịch) — xét theo giá trị tuyệt đối, đảo dấu khi dùng.

## Diễn giải backtest phân vị

Chia mã thành N nhóm theo giá trị nhân tố từ thấp đến cao (mặc định 5), nắm giữ đều trọng số trong mỗi nhóm.

**Tiêu chí**:
- **Đơn điệu**: vốn cuối từ `Group_1` → `Group_N` nên tăng (hoặc giảm) đơn điệu. Đơn điệu càng tốt → phân biệt càng mạnh.
- **Chênh lệch long-short**: chênh vốn nhóm cao nhất vs thấp nhất. Càng lớn → chọn lọc càng mạnh. *(Ở VN long-short chỉ là thước đo phân tích — NĐT lẻ KHÔNG bán khống được; thực chiến dùng phía LONG nhóm tốt nhất.)*
- **Phi tuyến**: nếu chỉ nhóm đầu-cuối khác biệt còn giữa giống nhau → nhân tố chỉ hiệu lực ở đuôi.
- **Ổn định**: đường vốn nhóm nên mượt; giật mạnh = nhân tố bất ổn.

**Cảnh báo**: các nhóm không khác biệt → nhân tố vô hiệu; hình chữ V/V ngược → quan hệ phi tuyến; một nhóm rơi liên tục → có thể dùng đảo chiều.

## Kết hợp nhân tố

### Đều trọng số
Chuẩn hóa từng nhân tố rồi cộng đều. Hợp khi ít nhân tố, IC chênh nhỏ.
```
Composite = Z(factor1) + Z(factor2) + ... ;  Z() = chuẩn hóa Z-score cross-sectional
```

### Theo IC
Trọng số theo |IC trung bình|.
```
weight_i = |IC_mean_i| / sum(|IC_mean_j|) ;  Composite = sum(weight_i * Z(factor_i))
```

### Trực giao hóa (Schmidt)
Khử cộng tuyến trước khi kết hợp (khi các nhân tố tương quan cao): xếp theo IC giảm dần → giữ nhân tố đầu → hồi quy nhân tố sau lên các nhân tố trước, lấy phần dư → kết hợp đều phần dư.

## Bẫy thường gặp

### Nhìn trước (look-ahead)
- Nhân tố tính từ dữ liệu ngày T trở về trước; lợi suất dùng T+1..T+N.
- SAI: tính nhân tố bằng giá đóng T rồi tương quan với lợi suất NGÀY T → IC thổi phồng giả tạo.
- ĐÚNG: nhân tố tại T, lợi suất từ đóng T → đóng T+1 trở đi.

### Phân phối lệch
- Một số nhân tố (vốn hóa, thanh khoản) lệch phải mạnh → IC bị outlier chi phối.
- Giải: rank cross-sectional hoặc Z-score trước khi tính IC.

### Trung lập ngành (theo ICB) ⭐
- Giá trị nhân tố dễ giống nhau trong cùng ngành → chọn cổ phiếu dồn vào vài ngành.
- Giải: Z-score TRONG từng ngành (trung lập ngành) để khử hiệu ứng ngành.
- **VN dùng phân ngành ICB**: `Listing(source="VCI").symbols_by_industries()` (`icb_code`/`icb_name`); ngân hàng nhận diện bằng `Company.overview().is_bank`.

### Mẫu quá nhỏ / thanh khoản mỏng (đặc thù VN)
- Mỗi cross-section cần ≥5 mã hợp lệ để IC có ý nghĩa; backtest phân vị cần ≥ `n_groups` mã.
- **Thị trường VN nhỏ**: hạn chế universe ở rổ thanh khoản (**VN30 / VN100 / HOSE thanh khoản cao**); tránh UPCOM/penny mỏng (giá nhiễu, khó khớp).

### Biên độ giá (đặc thù VN)
- Trần/sàn ngày (HOSE ±7%, HNX ±10%, UPCOM ±15%) **chặn** lợi suất ngày → biến dạng đuôi phân phối; nhân tố reversal/momentum ngắn hạn bị ảnh hưởng. Cân nhắc lợi suất nhiều ngày.

### Đông đúc nhân tố (crowding)
- Nhân tố kinh điển (momentum, value) có thể mất alpha khi quá phổ biến → soi IC theo thời gian xem có suy giảm.

### Thiên kiến sống sót
- Chỉ backtest trên mã còn niêm yết hôm nay → thổi phồng hiệu suất. Dùng full-sample gồm mã đã hủy niêm yết/chuyển sàn (UPCOM).

## Nguồn dữ liệu (VN)

| Đầu vào nhân tố | Nguồn |
|------|------|
| Giá / khối lượng / **dòng tiền khối ngoại** (factor flow) | **DataPro** (`source="datapro"`, mã `.VN`; `FRN_BUY_VOL/FRN_SELL_VOL`) |
| Cơ bản (ROE, biên, tăng trưởng, P/E, P/B...) | **vnstock KBS** (`ratio`, `income`/`balancesheet`) — point-in-time qua `fundamental_fields` |
| Phân ngành (trung lập ngành) | **vnstock** `Listing.symbols_by_industries()` (ICB); `Company.overview().is_bank/icb_code_lv2` |
| Lợi suất forward (return CSV) | **DataPro** giá đóng cửa điều chỉnh, dịch N ngày |

## Phụ thuộc

```bash
pip install pandas numpy scipy
```

## Dùng nhân tố từ Alpha Zoo

Thay vì tính lại nhân tố từ OHLCV mỗi lần, ưu tiên tái dùng 450+ alpha dựng sẵn trong Alpha Zoo (alpha101/gtja191/qlib158/academic). Mỗi alpha đã được kiểm metadata (`AlphaMeta`), kiểm shape theo `panel["close"]`, loại nếu phát sinh `±inf` hoặc >95% NaN — nên factor CSV đưa vào `factor_analysis` đã được kiểm sơ bộ.

```python
from src.factors.registry import Registry

registry = Registry()
ids = registry.list(theme="momentum")          # duyệt danh mục theo chủ đề
# Công thức alpha là MATH thuần (tương thích mọi OHLCV) → áp được cho panel .VN dựng từ DataPro,
# dù tag universe gốc là CN/US. Tự kiểm warmup_bars + NaN trên dữ liệu VN trước khi dùng.
factor_panel = registry.compute("alpha101_001", panel)   # panel = DataFrame .VN từ DataPro
factor_panel.to_csv("factor_alpha101_001.csv")
```

Để kết hợp nhiều alpha đã kiểm định thành một tín hiệu, xem `ZooSignalEngine` của skill `multi-factor`. Để duyệt danh mục + xem `__alpha_meta__`, xem skill `alpha-zoo`.
