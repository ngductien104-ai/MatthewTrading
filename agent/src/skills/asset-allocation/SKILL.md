---
name: asset-allocation
description: "Lý thuyết phân bổ tài sản & cách dùng optimizer cho danh mục VN — MPT / Black-Litterman / risk budgeting / all-weather, hướng dẫn 4 optimizer tích hợp và quy tắc tái cơ cấu. Lưu ý hạn chế công cụ đầu tư ở VN (thiếu ETF hàng hóa/REIT, không bán khống, đòn bẩy chỉ qua margin), phí: thuế bán 0,1%, T+2."
category: asset-class
---

# Phân bổ tài sản & Tối ưu danh mục (Việt Nam)

## Tổng quan

Từ lý thuyết phân bổ tài sản đến triển khai thực tế, skill này bao quát các khung kinh điển (MPT, BL, risk budgeting, all-weather) và cách dùng 4 optimizer tích hợp trong hệ thống. Kết quả có thể ghi thẳng vào `config.json`.

> **Hạn chế công cụ đầu tư ở TTCK VN — đọc trước tiên:**
> - **Lớp tài sản đầu tư được hẹp**: NĐT VN chủ yếu tiếp cận cổ phiếu, tiền gửi/trái phiếu, vàng, một số ETF (E1VFVN30, FUEVFVND...). **Thiếu công cụ hàng hóa/REIT/TIPS thanh khoản** → danh mục all-weather kiểu Bridgewater khó dựng đủ chân ở VN.
> - **Không bán khống đại trà; đòn bẩy chỉ qua margin** → ràng buộc `w ≥ 0`, tổng trọng số ≤ 1.
> - **Tương quan nội bộ cổ phiếu VN cao** (cụm quanh nhóm ngân hàng/BĐS) → lợi ích đa dạng hóa trong rổ cổ phiếu hạn chế.
> - **Phí & thuế**: thuế chuyển nhượng **0,1% chỉ chiều bán** + phí môi giới ~0,15% → tái cơ cấu dày bị bào mòn. Thanh toán **T+2**.

## Lý thuyết phân bổ tài sản

### 1. Lý thuyết danh mục hiện đại (MPT, Markowitz)

**Ý tưởng cốt lõi**: tối đa hóa lợi suất kỳ vọng cho một mức rủi ro cho trước (đường biên hiệu quả).

```
Bài toán tối ưu:
min  w'Σw              (phương sai danh mục)
s.t. w'μ = target_return
     Σw = 1
     w ≥ 0              (không bán khống — phù hợp ràng buộc TTCK VN)
```

| Ưu điểm | Nhược điểm |
|------|------|
| Chặt chẽ về toán học | Cực nhạy với đầu vào (garbage in, garbage out) |
| Trực quan hóa được đường biên hiệu quả | Hay cho trọng số cực đoan (dồn vào vài tài sản) |
| Khung nền tảng | Giả định phân phối chuẩn, bỏ qua đuôi dày (fat tail) |

**Lời khuyên thực chiến**: đừng dùng MPT thô. Thêm ràng buộc (chặn trên/dưới, giới hạn theo ngành) hoặc dùng phiên bản đã chính quy hóa (regularized).

### 2. Mô hình Black-Litterman

**Ý tưởng cốt lõi**: xuất phát từ cân bằng thị trường rồi lồng quan điểm nhà đầu tư.

```
Các bước:
1. Suy ngược lợi suất cân bằng thị trường: π = δΣw_mkt
2. Dựng ma trận quan điểm: P (ma trận chọn), Q (lợi suất quan điểm), Ω (độ bất định quan điểm)
3. Trộn hậu nghiệm: μ_BL = [(τΣ)^-1 + P'Ω^-1 P]^-1 [(τΣ)^-1 π + P'Ω^-1 Q]
4. Chạy tối ưu Markowitz với μ_BL hậu nghiệm
```

**Ví dụ quan điểm (TTCK VN)**:
- Quan điểm tuyệt đối: "Nhóm ngân hàng tăng 12% trong 1 năm tới"  → `P=[1,0,0], Q=[0,12]`
- Quan điểm tương đối: "Nhóm ngân hàng vượt nhóm BĐS 5%"  → `P=[1,-1,0], Q=[0,05]`

**Hướng dẫn tham số**:
- `τ` (hệ số bất định): `0,025–0,05`
- `Ω`: đặt theo độ tự tin của quan điểm — tự tin cao = phương sai nhỏ

### 3. Phân bổ theo ngân sách rủi ro (Risk Budgeting)

**Ý tưởng cốt lõi**: phân bổ theo đóng góp rủi ro thay vì theo tỷ trọng vốn.

```
Đóng góp rủi ro: RC_i = w_i × (Σw)_i / σ_p
Mục tiêu: RC_i / σ_p = budget_i  (với mọi i)
```

| Chiến lược | Ngân sách rủi ro | Tình huống dùng tốt |
|------|---------|---------|
| Đóng góp rủi ro bằng nhau | Mỗi tài sản 1/N | Khi không biết tài sản nào tốt nhất |
| Nghiêng về cổ phiếu | Cổ phiếu 60%, trái phiếu 30%, vàng 10% | Khi muốn cổ phiếu đóng góp rủi ro nhiều hơn |
| Ngân sách rủi ro động | Điều chỉnh theo độ mạnh tín hiệu | Khi có khả năng định thời điểm thị trường |

### 4. Chiến lược All-Weather

**Khung Bridgewater**: phân bổ rủi ro đều qua các trạng thái kinh tế.

```
Trạng thái kinh tế      Phân bổ tài sản
─────────              ─────────
Tăng trưởng lên         Cổ phiếu + hàng hóa + trái phiếu doanh nghiệp
Tăng trưởng xuống       Trái phiếu chính phủ + trái phiếu chống lạm phát
Lạm phát lên            Hàng hóa + trái phiếu chống lạm phát + nợ thị trường mới nổi
Lạm phát xuống          Cổ phiếu + trái phiếu chính phủ

Ví dụ phân bổ rút gọn cho NĐT VN (do thiếu công cụ hàng hóa/REIT/TIPS):
- 30% cổ phiếu VN (ETF VN30 như E1VFVN30, hoặc rổ VN30/VNMidcap)
- 40% trái phiếu / tiền gửi kỳ hạn (TPCP khó mua lẻ → thay bằng quỹ TP hoặc tiền gửi)
- 15% vàng (theo giá vàng trong nước/quốc tế)
- 15% tiền mặt / tiền gửi ngắn hạn (thay phần hàng hóa/REIT vốn hiếm ở VN)

Lưu ý: đây là phiên bản đơn giản hóa — không nên hiểu là "all-weather đầy đủ"
vì thị trường VN chưa đủ công cụ để phân bổ rủi ro qua mọi trạng thái lạm phát.
```

## Hướng dẫn 4 Optimizer

### Tổng quan các optimizer tích hợp

Cấu hình trong `config.json` qua `optimizer` và `optimizer_params`:

| optimizer | Tên hiển thị | Ý tưởng cốt lõi | Tình huống dùng tốt |
|-----------|--------|---------|---------|
| `equal_volatility` | Biến động bằng nhau | Trọng số theo nghịch đảo biến động | Baseline đơn giản, hiệu quả |
| `risk_parity` | Cân bằng rủi ro | Cân bằng đóng góp rủi ro có tính tương quan | Phân bổ bền vững dài hạn |
| `mean_variance` | Trung bình–Phương sai | Tối đa Sharpe hoặc tối thiểu phương sai | Khi có dự báo lợi suất |
| `max_diversification` | Đa dạng hóa tối đa | Tối đa tỷ số đa dạng hóa | Khi muốn danh mục tương quan thấp |

### 1. `equal_volatility`

```json
{
  "optimizer": "equal_volatility",
  "optimizer_params": {
    "lookback": 60
  }
}
```

**Nguyên lý**: `w_i = (1/σ_i) / Σ(1/σ_j)`

| Tham số | Mặc định | Mô tả |
|------|--------|------|
| lookback | 60 | Cửa sổ tính biến động (số phiên) |

**Ưu điểm**: đơn giản, nhanh, không cần dự báo lợi suất, không cần ma trận tương quan.
**Nhược điểm**: bỏ qua tương quan giữa các tài sản.

### 2. `risk_parity`

```json
{
  "optimizer": "risk_parity",
  "optimizer_params": {
    "lookback": 60
  }
}
```

**Nguyên lý**: tìm trọng số sao cho mỗi tài sản đóng góp lượng rủi ro bằng nhau.

| Tham số | Mặc định | Mô tả |
|------|--------|------|
| lookback | 60 | Cửa sổ ước lượng ma trận hiệp phương sai |

**Ưu điểm**: tính đến tương quan, dàn rủi ro đều hơn, bền vững dài hạn.
**Nhược điểm**: cần giải lặp, nhạy với ước lượng hiệp phương sai.

### 3. `mean_variance`

```json
{
  "optimizer": "mean_variance",
  "optimizer_params": {
    "lookback": 60,
    "risk_free": 0.0
  }
}
```

**Nguyên lý**: tối ưu Markowitz tối đa hóa Sharpe.

| Tham số | Mặc định | Mô tả |
|------|--------|------|
| lookback | 60 | Cửa sổ ước lượng trung bình & hiệp phương sai |
| risk_free | 0.0 | Lãi suất phi rủi ro (theo năm) |

**Ưu điểm**: tối ưu về lý thuyết (nếu đầu vào chính xác).
**Nhược điểm**: cực nhạy với đầu vào, hay cho trọng số cực đoan, thường kém ngoài mẫu.
**Khuyến nghị**: đừng để `lookback` quá ngắn (`<30` dễ overfit), nên thêm ràng buộc chặn trên/dưới. Với VN, cân nhắc đặt lãi suất phi rủi ro ~ lợi suất TPCP/tiền gửi kỳ hạn (đừng để 0 nếu so sánh với kênh gửi tiết kiệm).

### 4. `max_diversification`

```json
{
  "optimizer": "max_diversification",
  "optimizer_params": {
    "lookback": 60
  }
}
```

**Nguyên lý**: tối đa `DR = (w'σ) / σ_p` (tỷ số đa dạng hóa).

| Tham số | Mặc định | Mô tả |
|------|--------|------|
| lookback | 60 | Cửa sổ tính toán |

**Ưu điểm**: không cần dự báo lợi suất, hướng tới đa dạng hóa thật.
**Nhược điểm**: hiệu quả hạn chế trong môi trường tương quan cao — **đáng lưu ý ở VN** vì cổ phiếu nội bộ tương quan cao.

### Cây quyết định chọn optimizer

```
Có dự báo lợi suất không?
├── Có → mean_variance (nhớ thêm ràng buộc)
└── Không → Cần tính đến tương quan không?
    ├── Có → risk_parity (mặc định khuyến nghị)
    └── Không → Chênh lệch biến động giữa các tài sản có lớn không?
        ├── Có → equal_volatility
        └── Không → max_diversification
```

## Chiến lược tái cơ cấu

### Ba cơ chế kích hoạt

| Phương pháp | Điều kiện kích hoạt | Ưu điểm | Nhược điểm |
|------|---------|------|------|
| Định kỳ | Ngày cố định hàng tháng/quý | Đơn giản, chi phí dự đoán được | Có thể lỡ/trễ điều chỉnh |
| Theo ngưỡng | Lệch trọng số mục tiêu > X% | Chỉ giao dịch khi cần | Giao dịch dày khi thị trường biến động mạnh |
| Theo biến động | Chỉ số biến động vượt ngưỡng | Thích nghi với chế độ thị trường | Khó chọn tham số |

### Tần suất tái cơ cấu gợi ý

| Lớp tài sản | Tần suất gợi ý | Ngưỡng |
|---------|---------|------|
| Danh mục cổ phiếu | Hàng tháng | ±5% |
| Cổ phiếu–trái phiếu | Hàng quý | ±10% |
| Vĩ mô toàn cầu | Quý / nửa năm | ±10% |

> Lưu ý VN: thuế bán **0,1%** mỗi lần bán → tái cơ cấu dày bị phạt nặng. Ưu tiên kết hợp **định kỳ + ngưỡng** (chỉ giao dịch khi lệch vượt ngưỡng vào ngày tái cơ cấu) để giảm số lần bán. Tính cả ràng buộc **T+2** và **room ngoại** khi tăng tỷ trọng.

### Tái cơ cấu trong backtest

Cài logic tái cơ cấu trong `signal_engine.py`:

```python
# Ví dụ tái cơ cấu định kỳ (mỗi 20 phiên)
if bar_count % rebalance_freq == 0:
    # Tính lại trọng số
    new_weights = calculate_target_weights(data_map)
    for code, weight in new_weights.items():
        signals[code].iloc[i] = weight
```

## Phân tích tương quan chéo tài sản

### Ma trận tương quan minh họa (danh mục VN — số liệu phải hiệu chỉnh trên dữ liệu thật)

| | VN30 | VNMidcap | Trái phiếu/Quỹ TP | Vàng | Tiền gửi |
|--|------|----------|-------------------|------|----------|
| VN30 | 1,00 | 0,85 | −0,10 | 0,05 | 0,00 |
| VNMidcap | 0,85 | 1,00 | −0,08 | 0,03 | 0,00 |
| Trái phiếu/Quỹ TP | −0,10 | −0,08 | 1,00 | 0,15 | 0,10 |
| Vàng | 0,05 | 0,03 | 0,15 | 1,00 | 0,00 |
| Tiền gửi | 0,00 | 0,00 | 0,10 | 0,00 | 1,00 |

**Quy luật chính** (lưu ý: số trên là minh họa, phải tính lại từ dữ liệu DataPro):
- Tương quan cổ phiếu–trái phiếu thường âm (nền tảng của phân bổ), nhưng **không phải lúc nào cũng đúng** — 2022 cả cổ phiếu lẫn trái phiếu cùng giảm (kèm khủng hoảng TPDN).
- Vàng tương quan thấp với cổ phiếu → vai trò phòng hộ.
- **VN30 và VNMidcap tương quan rất cao (~0,85)** → đa dạng hóa trong rổ cổ phiếu VN hạn chế; cả hai cùng cụm quanh nhóm ngân hàng/BĐS, nên trong sốc thị trường tương quan còn tăng vọt.
- Tiền gửi ~ phi rủi ro, tương quan ~0 → "chân" giảm biến động an toàn nhất ở VN.

## Mẫu output

```markdown
## Khuyến nghị phân bổ tài sản

### Phương án phân bổ (minh họa — số liệu lấy từ nguồn thật)
| Tài sản | Trọng số | Đóng góp rủi ro | Lợi suất kỳ vọng (năm) |
|------|------|---------|--------------|
| ETF VN30 (E1VFVN30) | 30% | 45% | 10% |
| Quỹ trái phiếu / tiền gửi | 40% | 15% | 6% |
| Vàng | 15% | 20% | 5% |
| Tiền gửi ngắn hạn | 15% | 20% | 5% |

### Cấu hình optimizer
```json
{
  "optimizer": "risk_parity",
  "optimizer_params": {"lookback": 60}
}
```

### Rủi ro / Lợi suất kỳ vọng
| Chỉ tiêu | Giá trị |
|------|-----|
| Lợi suất kỳ vọng/năm | 7,5% |
| Biến động kỳ vọng/năm | 9,0% |
| Sharpe kỳ vọng | 0,80 |
| Sụt giảm tối đa kỳ vọng | −13% |

### Quy tắc tái cơ cấu
- Tần suất: hàng quý (phiên đầu tháng 3/6/9/12)
- Ngưỡng: kích hoạt khi tài sản lệch mục tiêu ±10%
- Chi phí: ước tính chi phí giao dịch/năm ~0,3% (gồm thuế bán 0,1%)
```

## Lưu ý quan trọng

1. **Optimizer cần đủ công cụ**: cần tối thiểu 3 tài sản để tối ưu có ý nghĩa; với 2 tài sản thường `equal_volatility` là đủ.
2. **Cửa sổ `lookback`**: quá ngắn (`<20`) nhiễu, quá dài (`>120`) phản ứng chậm; 60 là mặc định hợp lý.
3. **Bẫy `mean_variance`**: dễ overfit nhất, Sharpe ngoài mẫu thường bị cắt nửa trở lên.
4. **Chi phí tái cơ cấu**: tái cơ cấu dày ăn vào lợi suất; với danh mục cổ phiếu VN, **thuế bán 0,1% + phí môi giới ~0,15%** là đáng kể (chiều bán đắt hơn chiều mua).
5. **Hạn chế công cụ ở VN**: thiếu ETF hàng hóa/REIT/TIPS thanh khoản → các chân "chống lạm phát" của all-weather khó dựng; thực tế danh mục thường rút về cổ phiếu / trái phiếu (tiền gửi) / vàng.
6. **Ràng buộc đòn bẩy**: tổng trọng số ≤ 1,0; không dùng đòn bẩy trừ khi chỉ định rõ (ở VN đòn bẩy chỉ qua margin, có lãi vay và rủi ro call margin).
7. **Room ngoại**: danh mục NĐT nước ngoài phải kiểm tra room trước khi tăng tỷ trọng — mã hết room không mua được trên sàn.
8. **Survivorship bias**: tương quan lịch sử có thể méo do hủy niêm yết / niêm yết mới; rổ chỉ số VN thay đổi thành phần định kỳ.


## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)

1. **Không bịa/cook số liệu.** Mọi số tài chính phải có nguồn thật. Luôn **audit nhanh, cross-check tối thiểu 2 nguồn uy tín** (vd `cafef.vn`, `vietstock.vn`) — dùng **crawl4ai** cào số rồi đối chiếu; nếu nguồn lệch nhau thì nêu rõ, không chọn bừa.
2. **Nếu DataPro VÀ vnstock đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
