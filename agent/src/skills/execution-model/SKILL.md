---
name: execution-model
description: "Mô hình hóa thực thi lệnh (chỉ cho backtest) trên TTCK VN — công thức trượt giá (slippage), tác động thị trường tuyến tính/căn bậc hai, logic VWAP/TWAP theo khung phiên HOSE, ước lượng chi phí giao dịch (phí môi giới + thuế bán 0,1%). Lưu ý đặc thù: thanh toán T+2 (không bán cổ phiếu vừa mua cùng phiên), mã trần/sàn không khớp được, bước giá & lô 100, room ngoại."
category: strategy
---

# Mô hình hóa thực thi lệnh (Việt Nam)

## Mục đích

Cung cấp giả định thực thi sát thực tế hơn cho backtest: mô hình trượt giá, ước lượng tác động thị trường, nguyên lý thuật toán thực thi. Skill này **chỉ phục vụ mô phỏng backtest**, không thực thi lệnh thật.

> **Đặc thù thực thi TTCK VN — đọc trước tiên:**
> - **Thanh toán T+2**: mua phiên T, cổ phiếu về tài khoản chiều T+2 → **không thể bán cổ phiếu vừa mua trong cùng phiên / ngày kế tiếp**. Backtest phải trễ tín hiệu và khóa vị thế mới mua.
> - **Biên độ trần/sàn** (HOSE ±7%, HNX ±10%, UPCoM ±15%): khi mã **dư mua trần / dư bán sàn**, gần như **không khớp được** → phải bỏ qua phiên đó trong backtest, đừng giả định fill.
> - **Lô chẵn 100 cp** (HOSE), **bước giá** theo mức giá; **room ngoại** cạn → NĐT nước ngoài không mua được.

## Mô hình trượt giá (Slippage)

### Vì sao cần mô hình trượt giá

```
Backtest lý tưởng: khớp tại giá đóng cửa, trượt giá = 0
Thực tế:
1. Sổ lệnh có chênh mua–bán (bid-ask spread)
2. Lệnh lớn đẩy giá (market impact) — đặc biệt mã mid/small thanh khoản thấp
3. Có độ trễ từ tín hiệu đến khi khớp

Không mô hình trượt giá → backtest quá lạc quan → thua khi giao dịch thật.
```

### 1. Trượt giá cố định

```python
def fixed_slippage(price: float, direction: int, bps: float = 10.0) -> float:
    """
    Args:
        price: Giá gốc
        direction: 1=mua, -1=bán
        bps: Trượt giá tính theo điểm cơ bản (1bp = 0,01%), mặc định 10bp
    Returns:
        Giá khớp sau trượt
    """
    slippage = price * bps / 10000
    return price + direction * slippage
```

**Tham chiếu trượt giá cố định theo nhóm thanh khoản VN:**

| Nhóm | Ví dụ | Trượt giá gợi ý (bps) | Ghi chú |
|------|------|-------------|------|
| Bluechip VN30 | VCB, FPT, HPG, VNM | 5–10 | Thanh khoản tốt nhất TTCK VN |
| Midcap (VNMidcap) | DGC, PVD, DCM | 10–20 | Thanh khoản khá |
| Smallcap HOSE | các mã ngoài VN100 | 20–40 | Thanh khoản trung bình |
| Penny / UPCoM | mã GTGD thấp | 40–100+ | Thanh khoản kém, bước giá rộng, dễ trần/sàn |

> Lưu ý **bước giá tối thiểu** đã là một sàn trượt giá tự nhiên: HOSE <10.000đ → 10đ; 10.000–49.950đ → 50đ; ≥50.000đ → 100đ. Mã giá thấp có bước giá chiếm tỷ lệ % lớn → trượt giá thực tế cao hơn cảm giác.

### 2. Mô hình tác động tuyến tính

```python
def linear_impact(price: float, direction: int,
                  volume_traded: float, adv: float,
                  impact_coeff: float = 0.1) -> float:
    """
    Tác động thị trường tuyến tính: impact ∝ khối lượng giao dịch / ADV

    Args:
        price: Giá gốc
        direction: 1=mua, -1=bán
        volume_traded: Quy mô lệnh (cp hoặc giá trị)
        adv: Khối lượng giao dịch bình quân ngày (Average Daily Volume)
        impact_coeff: Hệ số tác động, thường 0,05–0,2
    Returns:
        Giá khớp sau tác động
    """
    participation_rate = volume_traded / adv
    impact = impact_coeff * participation_rate
    return price * (1 + direction * impact)
```

**Tham chiếu hệ số tác động:**

| Nhóm | impact_coeff | Ghi chú |
|------|-------------|------|
| Bluechip VN30 | 0,05–0,10 | Biên độ ±7%, sổ lệnh dày |
| Midcap | 0,10–0,20 | Phần bù thanh khoản |
| Smallcap / penny | 0,20–0,40 | Sổ lệnh mỏng, dễ đẩy trần/sàn |

### 3. Mô hình tác động căn bậc hai (Almgren-Chriss)

```python
import numpy as np

def sqrt_impact(price: float, direction: int,
                volume_traded: float, adv: float,
                volatility: float, eta: float = 0.5) -> float:
    """
    Tác động căn bậc hai (được học thuật chấp nhận rộng rãi):
    impact = η × σ × sqrt(V/ADV)

    Args:
        price: Giá gốc
        direction: 1=mua, -1=bán
        volume_traded: Quy mô lệnh
        adv: Khối lượng giao dịch bình quân ngày
        volatility: Biến động ngày (độ lệch chuẩn)
        eta: Hệ số đàn hồi tác động, thường 0,3–0,8
    Returns:
        Giá khớp sau tác động
    """
    participation = volume_traded / adv
    impact = eta * volatility * np.sqrt(participation)
    return price * (1 + direction * impact)
```

**Ưu điểm mô hình căn bậc hai**:
- Được hậu thuẫn thực nghiệm mạnh nhất (chuẩn trong tài liệu tài chính).
- Tác động biên giảm dần khi lệnh lớn hơn (trực giác đúng).
- Tham số ước lượng được từ dữ liệu lịch sử.

### Cây quyết định chọn mô hình trượt giá

```
Vốn backtest so với ADV của mã:
├── Vốn < 0,5% ADV   → trượt giá cố định (10bps) là đủ
├── Vốn 0,5–5% ADV   → mô hình tác động tuyến tính
└── Vốn > 5% ADV     → mô hình căn bậc hai (bắt buộc)

Lưu ý VN: nhiều mã mid/small có ADV rất thấp → ngay cả vốn vừa phải cũng vượt 5% ADV.
Với quỹ quy mô lớn, phần lớn rổ ngoài VN30 rơi vào ngưỡng căn bậc hai.
```

## Nguyên lý thuật toán thực thi

### VWAP (giá bình quân gia quyền khối lượng)

```
Mục tiêu: khớp quanh giá bình quân gia quyền khối lượng trong phiên.

VWAP = Σ(Giá_i × KL_i) / Σ(KL_i)

Logic thực thi:
1. Dự báo phân bố khối lượng trong phiên (VN thường dạng chữ U, dồn về ATO/ATC).
2. Chẻ lệnh theo phân bố dự báo.
3. Khớp theo tỷ lệ trong từng lát thời gian.

Khung phiên HOSE & phân bố khối lượng điển hình (dạng chữ U):
09:00–09:15  ATO (khớp định kỳ mở cửa)      ~12%
09:15–11:30  Khớp liên tục sáng (sôi động)  ~33%
11:30–13:00  NGHỈ TRƯA (không giao dịch)
13:00–14:30  Khớp liên tục chiều            ~30%
14:30–14:45  ATC (khớp định kỳ đóng cửa)    ~25%  ← thường nặng nhất, NĐT/quỹ tranh giá đóng cửa

VWAP trong backtest:
- Backtest ngày: dùng thẳng trường VWAP làm giá khớp (nếu có).
- Backtest phút: mô phỏng chẻ lệnh theo phân bố trên.
```

> Lưu ý đặc thù VN: phiên **ATC (14:30–14:45)** thường dồn khối lượng rất lớn do quỹ/ETF và NĐT chốt theo giá đóng cửa; biến động giá ATC có thể mạnh. HNX/UPCoM khung phiên tương tự nhưng UPCoM không có ATO/ATC (chỉ khớp liên tục).

### TWAP (giá bình quân gia quyền thời gian)

```
Mục tiêu: khớp đều trong một khoảng thời gian định trước.

TWAP = chẻ lệnh đều theo thời gian.

Logic:
1. Định cửa sổ thực thi (vd 09:15–11:30).
2. Chia N lát thời gian.
3. Khớp tổng_lệnh / N trong mỗi lát.

Ưu/nhược:
+ Đơn giản, không cần dự báo khối lượng.
- Dễ gây tác động trong lát thanh khoản thấp (đầu/giữa phiên VN thường mỏng hơn ATC).
- Kém thích nghi hơn VWAP.
```

### Mô phỏng độ trễ thực thi trong backtest

```python
def delayed_execution(signal_series: pd.Series, delay_bars: int = 1) -> pd.Series:
    """
    Mô phỏng độ trễ từ lúc phát tín hiệu đến lúc khớp.

    Args:
        signal_series: Tín hiệu gốc
        delay_bars: Số nến trễ, mặc định 1 (tín hiệu cuối phiên T → khớp phiên T+1)
    Returns:
        Tín hiệu đã trễ

    TTCK VN: delay_bars=1 (khớp phiên kế tiếp). NGOÀI RA, do thanh toán T+2,
    cổ phiếu vừa mua KHÔNG bán được ngay — backtest phải khóa vị thế mới mua
    (xem chú thích phía dưới).
    """
    return signal_series.shift(delay_bars)
```

> **Quan trọng — khóa T+2:** ngoài độ trễ tín hiệu 1 phiên, engine còn phải đảm bảo **không bán cổ phiếu trong vòng ~2 phiên kể từ khi mua** (cổ phiếu chưa về tài khoản). Nếu bỏ qua, backtest sẽ tạo ra các vòng quay nhanh không thể thực hiện ở VN và phóng đại lợi nhuận.

## Mô hình chi phí giao dịch tổng hợp

### Phân rã tổng chi phí

```
Tổng chi phí = chi phí hiện (explicit) + chi phí ẩn (implicit)

Chi phí hiện:
- Phí môi giới: ~0,10–0,35% mỗi chiều (online thường ~0,15%; thỏa thuận theo quy mô).
- Thuế TNCN chuyển nhượng: 0,10% trên GIÁ TRỊ BÁN (chỉ tính chiều bán).
- Phí lưu ký VSD: rất nhỏ (~vài chục đồng/cp/tháng) — bỏ qua được.
  (VN KHÔNG có stamp duty kiểu HK/TQ; thuế bán 0,1% đóng vai trò tương tự.)

Chi phí ẩn:
- Chênh mua–bán: phụ thuộc bước giá & thanh khoản.
- Tác động thị trường: theo quy mô lệnh & thanh khoản.
- Chi phí cơ hội: lỡ giá tốt do không khớp / mã trần-sàn.
```

### Tham chiếu chi phí giao dịch (TTCK VN)

| Khoản mục | Mức điển hình |
|--------|-----|
| Phí môi giới (1 chiều) | 0,15% (online; có thể 0,10–0,35%) |
| Thuế chuyển nhượng | 0,10% (chỉ chiều BÁN) |
| Phí lưu ký | ~0% (bỏ qua) |
| Chênh mua–bán (ẩn) | 0,05–0,3% tùy thanh khoản |
| **Tổng 1 chiều mua** | ~0,15–0,20% |
| **Tổng 1 chiều bán** | ~0,25–0,30% (gồm thuế 0,1%) |
| **Tổng vòng (mua+bán)** | **~0,40–0,55%** |

### Cấu hình chi phí trong backtest

```json
{
  "commission": 0.0025,
  "comment": "0,25% mỗi chiều (bảo thủ: gồm phí môi giới + ~thuế bán phân bổ + chênh giá)"
}
```

**Khuyến nghị**:
- VN bluechip VN30: `commission = 0,002–0,0025` (đã gồm mọi chi phí, bảo thủ).
- VN mid/smallcap: `commission = 0,003–0,005` (thanh khoản kém, trượt giá cao hơn).
- Lưu ý phí **bất đối xứng**: chiều bán đắt hơn chiều mua đúng 0,1% (thuế) — chiến lược vòng quay cao chịu thiệt rõ.

## Giả định thực thi trong backtest

### Cấu hình `config.json` liên quan

```json
{
  "commission": 0.0025,
  "engine": "daily",
  "interval": "1D"
}
```

### Giả định thực thi nâng cao (cài trong `signal_engine.py`)

```python
class SignalEngine:
    def __init__(self):
        # Tham số giả định thực thi
        self.execution_delay = 1       # trễ 1 phiên (T → T+1)
        self.settlement_lock = 2       # khóa T+2: cổ phiếu mới mua chưa bán được
        self.slippage_bps = 10         # trượt giá cố định 10bps (bluechip)
        self.max_participation = 0.05  # tỷ lệ tham gia tối đa 5% ADV

    def generate(self, data_map):
        for code, df in data_map.items():
            # 1. Sinh tín hiệu gốc
            raw_signal = self._compute_signal(df)

            # 2. Áp độ trễ thực thi
            delayed_signal = raw_signal.shift(self.execution_delay)

            # 3. Lọc thanh khoản (không giao dịch khi KL quá thấp so với nền)
            volume_ok = df['volume'] > df['volume'].rolling(20).mean() * 0.3
            delayed_signal[~volume_ok] = 0

            # 4. Bỏ qua phiên trần/sàn (không khớp được)
            #    vd: nếu high==low==trần hoặc giá chạm trần/sàn cả phiên → skip
            #    (chèn logic kiểm tra biên độ theo sàn niêm yết)

            signals[code] = delayed_signal
```

## Khung phân tích

### Đánh giá tác động của chi phí giao dịch

```
Bước 1: Ước lượng vòng quay danh mục/năm
  Vòng quay/năm = số lệnh/năm × 2 (mua + bán) / số vị thế

Bước 2: Tính lực cản chi phí/năm
  Chi phí/năm = vòng quay/năm × tổng chi phí 1 vòng

Bước 3: Đánh giá ảnh hưởng lên lợi suất
  Lợi suất ròng = lợi suất gộp − chi phí/năm

Ví dụ (VN):
  Vòng quay = 12 (tái cơ cấu hàng tháng)
  Chi phí 1 vòng (mua+bán) = ~0,45%
  Chi phí/năm = 12 × 0,45% = 5,4%
  Nếu lợi suất/năm chỉ 10% → chi phí ngốn hơn nửa lợi nhuận!
  → Chiến lược vòng quay cao ở VN bị phí + thuế bán bào mòn rất nặng.
```

### Phân tích độ nhạy với giả định thực thi

```markdown
### Kết quả backtest theo các mức trượt giá

| Trượt giá (bps) | Lợi suất/năm | Sharpe | Sụt giảm tối đa |
|-----------|---------|--------|---------|
| 0 (lý tưởng) | 18,2% | 1,05 | −22,5% |
| 10 | 15,8% | 0,92 | −23,0% |
| 20 | 13,1% | 0,78 | −23,5% |
| 40 | 8,5% | 0,52 | −24,2% |

Kết luận: chiến lược còn khả năng sinh lời ở mức trượt 20bps; ở 40bps (mã smallcap)
biên lợi nhuận mỏng → chỉ nên áp dụng cho rổ thanh khoản cao.
```

## Mẫu output

```markdown
## Phân tích chi phí thực thi (minh họa)

### Đặc điểm giao dịch của chiến lược
| Chỉ tiêu | Giá trị |
|------|-----|
| Số lệnh bình quân/năm | 48 |
| Vòng quay danh mục/năm | 4,8 lần |
| Số phiên nắm giữ bình quân | 25 |
| Quy mô lệnh bình quân | 500 triệu đồng |

### Ước lượng chi phí
| Khoản mục | Mỗi lệnh | Quy năm |
|--------|------|------|
| Phí môi giới | 0,15% | 1,44% |
| Thuế bán (0,1% × chiều bán) | 0,05% | 0,48% |
| Trượt giá ước tính | 0,10% | 0,96% |
| **Tổng** | **0,30%** | **2,88%** |

### Ảnh hưởng chi phí
- Lợi suất gộp: 15,0%
- Lợi suất ròng: 12,1%
- Lực cản chi phí: −2,88% (~19% lợi suất gộp)
- Kết luận: chi phí đáng kể; nên giảm vòng quay & tránh mã thanh khoản thấp.

### Đề xuất tối ưu
1. Giảm vòng quay (kéo dài kỳ nắm giữ) — thuế bán 0,1%/lần khiến trading dày bị phạt nặng.
2. Tránh giao dịch trong khung thanh khoản thấp; ưu tiên ATC cho lệnh lớn.
3. Dùng lệnh giới hạn (LO) thay lệnh thị trường; tránh "đu trần" mã đang trần.
```

## Lưu ý quan trọng

1. **Chỉ dùng cho backtest**: hệ thống không thực thi lệnh thật; mô hình này chỉ để tăng tính thực tế của backtest.
2. **Giả định bảo thủ**: thà ước lượng chi phí cao còn hơn thấp.
3. **Thanh toán T+2**: không thể bán cổ phiếu trong cùng phiên mua; cổ phiếu về chiều T+2 → backtest phải trễ tín hiệu **và** khóa vị thế mới mua.
4. **Ràng buộc trần/sàn**: khi mã dư mua trần / dư bán sàn cả phiên, không khớp được → bỏ qua phiên đó trong backtest (đừng giả định fill tại giá trần/sàn).
5. **Ràng buộc khối lượng**: quy mô lệnh không nên vượt 5–10% khối lượng phiên, nếu không mô hình tác động mất hiệu lực — ngưỡng này dễ chạm với mã mid/small VN.
6. **Lô & bước giá**: HOSE lô chẵn 100 cp; bước giá theo mức giá (10/50/100đ). Lệnh lẻ và mã giá thấp chịu ma sát cao hơn.
7. **Room ngoại**: với danh mục của NĐT nước ngoài, khi mã hết room → không mua được trên sàn (phải mua thỏa thuận, thường giá cao hơn) — backtest cho quỹ ngoại cần tính ràng buộc này.
8. **Phí bất đối xứng**: chiều bán đắt hơn chiều mua 0,1% (thuế) — phạt chiến lược vòng quay cao.
9. **Overfitting backtest**: dù đã tính trượt giá, chiến lược vẫn có thể overfit; kiểm chứng ngoài mẫu quan trọng hơn.
10. **`commission` trong config**: mặc định nên đặt ~`0,0025` (0,25%/chiều) là ước lượng all-in hợp lý cho cổ phiếu VN.


## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)

1. **Không bịa/cook số liệu.** Mọi số tài chính phải có nguồn thật. Luôn **audit nhanh, cross-check tối thiểu 2 nguồn uy tín** (vd `cafef.vn`, `vietstock.vn`) — dùng **crawl4ai** cào số rồi đối chiếu; nếu nguồn lệch nhau thì nêu rõ, không chọn bừa.
2. **Nếu DataPro VÀ vnstock đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
