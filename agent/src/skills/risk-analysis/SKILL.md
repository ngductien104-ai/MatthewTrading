---
name: risk-analysis
description: "Đo lường rủi ro & kiểm định sức chịu đựng (stress test) cho danh mục cổ phiếu VN — tính VaR/CVaR/sụt giảm tối đa, mô phỏng Monte Carlo, phân tích rủi ro đuôi (EVT), stress test theo kịch bản lịch sử VN (2008/2018/2020/2022). Lưu ý: biên độ trần/sàn cắt đuôi 1 phiên nhưng chuỗi sàn do giải chấp margin tạo đuôi nhiều phiên; cấm bán khống nên phòng hộ chỉ qua tiền mặt/VN30F."
category: analysis
---

# Đo lường rủi ro & kiểm định sức chịu đựng (Việt Nam)

## Mục đích

Phương pháp đo rủi ro có hệ thống: VaR/CVaR, mô phỏng Monte Carlo, thiết kế stress test, phân tích rủi ro đuôi. Cung cấp lớp đánh giá rủi ro cho kết quả backtest và ràng buộc kiểm soát rủi ro cho phân bổ tài sản.

> **Đặc thù rủi ro TTCK VN — đọc trước tiên:**
> - **Biên độ trần/sàn** (HOSE ±7%, HNX ±10%, UPCoM ±15%) **cắt đuôi lợi suất 1 phiên** → VaR/kurtosis tính trên dữ liệu ngày sẽ **đánh giá THẤP rủi ro thật**. Rủi ro lớn nằm ở **chuỗi sàn liên tiếp** (giải chấp margin) — phải đo trên lợi suất nhiều phiên / drawdown, không chỉ 1 ngày.
> - **Cấm bán khống cổ phiếu** → không thể phòng hộ đuôi bằng short cổ phiếu; chỉ còn **nâng tiền mặt** hoặc **short VN30F (phái sinh)**.
> - **Vòng xoáy giải chấp**: giá giảm → call margin → force-sell → sàn → call thêm. Đây là cơ chế tạo đuôi trái nguy hiểm nhất ở VN, không có trong phân phối chuẩn.

## Phương pháp đo rủi ro

### 1. VaR (Value at Risk)

**Định nghĩa**: mức lỗ tối đa kỳ vọng trong một khoảng thời gian, tại một mức tin cậy cho trước.

#### Ba cách tính

| Phương pháp | Công thức / các bước | Ưu | Nhược |
|------|----------|------|------|
| Mô phỏng lịch sử | Sắp xếp lợi suất lịch sử, lấy phân vị | Không giả định phân phối | Phụ thuộc mẫu lịch sử |
| Tham số (chuẩn) | `VaR = μ − z_α × σ` | Dễ tính | Giả định phân phối chuẩn (sai cho VN fat-tail) |
| Monte Carlo | Mô phỏng N đường, lấy phân vị | Linh hoạt | Nặng tính toán |

#### Cài đặt — mô phỏng lịch sử

```python
import numpy as np
import pandas as pd

def historical_var(returns: pd.Series, confidence: float = 0.95, horizon: int = 1) -> float:
    """
    Args:
        returns: Chuỗi lợi suất ngày
        confidence: Mức tin cậy, thường 0.95 hoặc 0.99
        horizon: Kỳ nắm giữ (phiên), mặc định 1
    Returns:
        Giá trị VaR (dương = mức lỗ)
    """
    sorted_returns = returns.sort_values()
    index = int((1 - confidence) * len(sorted_returns))
    var_1d = -sorted_returns.iloc[index]
    return var_1d * np.sqrt(horizon)  # quy tắc căn bậc hai theo thời gian
```

#### Cài đặt — tham số

```python
from scipy.stats import norm

def parametric_var(returns: pd.Series, confidence: float = 0.95, horizon: int = 1) -> float:
    mu = returns.mean()
    sigma = returns.std()
    z = norm.ppf(1 - confidence)
    var_1d = -(mu + z * sigma)
    return var_1d * np.sqrt(horizon)
```

> **Cảnh báo VN:** VaR tham số (giả định chuẩn) **đánh giá thấp rủi ro** vì lợi suất cổ phiếu VN fat-tail nặng. Ngược lại, VaR lịch sử **1 ngày** lại bị biên độ trần/sàn "ép" về tối đa ±7% → vẫn không thấy hết rủi ro chuỗi sàn. Khuyến nghị: dùng VaR lịch sử với **horizon 5–10 phiên**, hoặc tính trực tiếp trên drawdown, để bắt được rủi ro giải chấp nhiều phiên.

### 2. CVaR / ES (Conditional VaR / Expected Shortfall)

**Định nghĩa**: mức lỗ bình quân vượt ngưỡng VaR — bảo thủ hơn VaR.

```python
def historical_cvar(returns: pd.Series, confidence: float = 0.95) -> float:
    """CVaR = trung bình mọi khoản lỗ vượt VaR."""
    var = historical_var(returns, confidence)
    tail_losses = returns[returns < -var]
    return -tail_losses.mean() if len(tail_losses) > 0 else var
```

**So sánh VaR vs CVaR**:

| Chỉ tiêu | VaR(95%) | CVaR(95%) | Ý nghĩa |
|------|----------|-----------|------|
| Giá trị điển hình | −2,5% | −4,0% | CVaR thường 1,3–1,8× VaR; với VN (chuỗi sàn) hệ số này có thể cao hơn |
| Tính dưới cộng (subadditive) | Không thỏa | Thỏa | CVaR dùng được để phân rã rủi ro danh mục |
| Quy định | Basel II | Basel III | Xu hướng chuyển sang CVaR |

### 3. Phân tích sụt giảm tối đa (Max Drawdown) — ⭐ chỉ tiêu cốt lõi cho VN

```python
def max_drawdown_analysis(equity: pd.Series) -> dict:
    """
    Args:
        equity: Chuỗi giá trị tài sản ròng
    Returns:
        dict: max_drawdown, peak_date, trough_date, recovery_date, duration
    """
    peak = equity.cummax()
    drawdown = (equity - peak) / peak
    max_dd = drawdown.min()
    trough_idx = drawdown.idxmin()
    peak_idx = equity[:trough_idx].idxmax()

    # Ngày hồi phục
    recovery = equity[trough_idx:][equity[trough_idx:] >= equity[peak_idx]]
    recovery_date = recovery.index[0] if len(recovery) > 0 else None

    return {
        'max_drawdown': max_dd,
        'peak_date': peak_idx,
        'trough_date': trough_idx,
        'recovery_date': recovery_date,
        'underwater_days': (trough_idx - peak_idx).days,
        'recovery_days': (recovery_date - trough_idx).days if recovery_date else None
    }
```

> Vì biên độ ngày bị chặn, **drawdown (sụt giảm tích lũy nhiều phiên) phản ánh rủi ro VN tốt hơn VaR 1 ngày.** Tham chiếu lịch sử VN-Index: 2008 −66%, 2018 −27%, COVID 2020 −34% (trong ~1 tháng), 2022 −43% (đỉnh 1.530 → đáy ~870). Danh mục dùng margin có thể sụt sâu hơn nhiều do giải chấp.

### 4. Mô phỏng Monte Carlo

#### Chuyển động Brown hình học (GBM)

```python
def monte_carlo_gbm(S0: float, mu: float, sigma: float,
                     T: int = 252, n_paths: int = 10000) -> np.ndarray:
    """
    Args:
        S0: Giá ban đầu
        mu: Lợi suất kỳ vọng/năm
        sigma: Biến động/năm
        T: Số phiên mô phỏng
        n_paths: Số đường mô phỏng
    Returns:
        Ma trận giá (n_paths, T)
    """
    dt = 1 / 252
    Z = np.random.standard_normal((n_paths, T))
    log_returns = (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * Z
    prices = S0 * np.exp(np.cumsum(log_returns, axis=1))
    return prices
```

> **Hạn chế GBM ở VN:** GBM giả định lợi suất chuẩn, độc lập → **không** tái hiện được chuỗi sàn (tự tương quan âm/dương theo cụm), biên độ trần/sàn, và rủi ro thanh khoản. Dùng GBM cho ước lượng thô; với đuôi trái nên kết hợp **bootstrap lịch sử** (lấy mẫu lại các đoạn khủng hoảng thật) hoặc mô phỏng có nhảy (jump).

#### Phân tích kết quả mô phỏng

```python
def analyze_mc_results(paths: np.ndarray, confidence: float = 0.95) -> dict:
    final_prices = paths[:, -1]
    returns = final_prices / paths[:, 0] - 1

    return {
        'mean_return': np.mean(returns),
        'median_return': np.median(returns),
        'std_return': np.std(returns),
        'var': -np.percentile(returns, (1 - confidence) * 100),
        'cvar': -np.mean(returns[returns < -np.percentile(returns, (1-confidence)*100)]),
        'prob_loss': np.mean(returns < 0),
        'worst_5pct': np.percentile(returns, 5),
        'best_5pct': np.percentile(returns, 95),
    }
```

## Khung kiểm định sức chịu đựng (Stress Test)

### Kịch bản lịch sử (TTCK Việt Nam)

| Kịch bản | Giai đoạn | VN-Index | Bối cảnh / cú sốc |
|------|--------|---------|---------|
| Khủng hoảng tài chính 2008 | 2007.10–2009.02 | **−66%** (1.170 → ~235) | Khủng hoảng toàn cầu + lạm phát/lãi suất VN tăng vọt |
| Bất ổn vĩ mô 2011 | 2011 | −27% | Lạm phát ~18%, lãi suất điều hành rất cao, siết tín dụng |
| Đỉnh 2018 / thương chiến | 2018.04–2018.12 | −27% (1.204 → ~880) | Thương chiến Mỹ–Trung, khối ngoại bán ròng, margin căng |
| Sốc COVID 2020 | 2020.01–2020.03 | **−34%** (~990 → ~660) trong ~6 tuần | Bán tháo toàn cầu, sau đó hồi phục chữ V |
| Khủng hoảng trái phiếu 2022 | 2022.04–2022.11 | **−43%** (1.530 → ~870) | Vạn Thịnh Phát/SCB, vỡ TPDN BĐS, giải chấp margin chuỗi sàn |

> Giai đoạn 2022 là kịch bản đặc thù VN quan trọng nhất: **vòng xoáy margin + đóng băng trái phiếu doanh nghiệp BĐS** → sàn hàng loạt nhiều phiên, thanh khoản bốc hơi. Mọi stress test danh mục VN nên có riêng kịch bản "giải chấp margin + đóng băng TPDN".

### Thiết kế kịch bản giả định (sốc theo lớp tài sản VN)

```python
STRESS_SCENARIOS = {
    'lai_suat_tang_200bp': {       # NHNN nâng lãi suất mạnh (như 2022)
        'co_phieu': -0.20,         # cổ phiếu giảm 20% (nhạy lãi suất cao)
        'tpcp_10y': -0.08,         # TPCP 10 năm giảm 8%
        'tpdn_bds': -0.25,         # trái phiếu DN BĐS giảm mạnh / mất thanh khoản
        'vang_sjc': +0.05,         # vàng SJC tăng
        'usd_vnd': +0.03,          # tỷ giá tăng
    },
    'giai_chap_margin': {          # vòng xoáy call margin / force-sell
        'co_phieu_largecap': -0.20,
        'co_phieu_midsmall': -0.40, # mid/small bị xả mạnh hơn, chuỗi sàn
        'tien_mat': 0.0,
        'note': 'thanh khoản bốc hơi, khó thoát hàng đúng giá',
    },
    'khoi_ngoai_rut_von': {        # USD mạnh → khối ngoại bán ròng
        'usd_vnd': +0.05,
        'co_phieu_bluechip': -0.15, # VN30 bị bán ròng nặng
        'tpcp': -0.03,
        'co_phieu_midsmall': -0.10,
    },
    'dong_bang_tpdn_bds': {        # khủng hoảng niềm tin TPDN BĐS (2022)
        'co_phieu_bds': -0.45,
        'co_phieu_nganhang': -0.25, # lo nợ xấu BĐS lây sang ngân hàng
        'co_phieu_chung_khoan': -0.40,
        'tpdn_bds': -0.50,
        'vang_sjc': +0.10,
    },
}
```

### Các bước thực hiện stress test

1. **Chọn kịch bản**: lịch sử hoặc giả định.
2. **Áp cú sốc**: nhân cú sốc kịch bản với vị thế hiện tại.
3. **Tính lỗ danh mục**: `lỗ = Σ(tỷ_trọng_i × cú_sốc_i)`.
4. **Đánh giá đủ vốn**: so lỗ với ngân sách rủi ro; kiểm tra **ngưỡng call margin** có bị kích hoạt không (đặc biệt nếu dùng đòn bẩy).

## Phân tích rủi ro đuôi (Extreme Value Theory, EVT)

### Phương pháp POT (Peaks Over Threshold)

```python
from scipy.stats import genpareto

def fit_gpd_tail(returns: pd.Series, threshold_pct: float = 5.0) -> dict:
    """
    Khớp đuôi phân phối bằng Generalized Pareto Distribution.
    Args:
        returns: Lợi suất ngày
        threshold_pct: Phân vị ngưỡng (lấy X% xấu nhất)
    """
    threshold = np.percentile(returns, threshold_pct)
    exceedances = threshold - returns[returns < threshold]  # đổi sang dương

    shape, loc, scale = genpareto.fit(exceedances)

    return {
        'threshold': threshold,
        'n_exceedances': len(exceedances),
        'shape_xi': shape,      # ξ>0 đuôi béo, ξ=0 đuôi mũ, ξ<0 đuôi chặn
        'scale_sigma': scale,
        'tail_type': 'đuôi béo (nguy hiểm)' if shape > 0 else 'đuôi mỏng (an toàn hơn)',
    }
```

> **Lưu ý EVT cho VN:** biên độ trần/sàn tạo "đuôi chặn" giả tạo ở mức ±7% trên dữ liệu 1 ngày → ξ có thể ra âm một cách đánh lừa. Nên chạy EVT trên **lợi suất tích lũy 5 phiên** để lộ đuôi béo thật từ chuỗi sàn.

### Chỉ tiêu rủi ro đuôi

| Chỉ tiêu | Cách tính | Ý nghĩa |
|------|------|------|
| Độ nhọn (Kurtosis) | `returns.kurtosis()` | >3 = đuôi béo; cổ phiếu VN thường cao do sóng đầu cơ + chuỗi trần/sàn |
| Độ lệch (Skewness) | `returns.skew()` | <0 = lệch trái (cú giảm sâu nhiều hơn cú tăng sốc) |
| Tỷ lệ đuôi | 5% xấu nhất / 5% tốt nhất | >1 = rủi ro giảm lớn hơn |
| Hill estimator | Chỉ số đuôi | `α<2` = đuôi cực béo |

## Khung phân tích

### Dữ liệu đầu vào

```
Bắt buộc:
- Chuỗi lợi suất (ngày trở lên) hoặc chuỗi NAV
- Tỷ trọng danh mục (nếu là danh mục)

Tùy chọn:
- Lợi suất benchmark (VN-Index/VN30 — cho rủi ro tương đối)
- Ngân sách rủi ro / ràng buộc; mức margin/đòn bẩy đang dùng
```

### Các bước phân tích

1. **Tiền xử lý**: tính lợi suất, kiểm tra khuyết, xử lý ngoại lai (lưu ý phiên trần/sàn, phiên nghỉ giao dịch).
2. **Thống kê mô tả**: trung bình / biến động / độ lệch / độ nhọn / sụt giảm tối đa.
3. **VaR/CVaR**: so 3 phương pháp ở cả 95% và 99%; **kèm horizon 5–10 phiên** cho rủi ro chuỗi sàn.
4. **Monte Carlo**: 10.000 đường; cân nhắc bootstrap lịch sử cho đuôi.
5. **Stress test**: tối thiểu 3 kịch bản lịch sử VN + 2 kịch bản giả định (bắt buộc có "giải chấp margin").
6. **Phân tích đuôi**: khớp GPD, xác định loại đuôi (chạy thêm trên lợi suất 5 phiên).
7. **Khuyến nghị kiểm soát rủi ro**.

## Mẫu output

```markdown
## Báo cáo phân tích rủi ro (minh họa)

### Chỉ tiêu rủi ro cốt lõi
| Chỉ tiêu | Giá trị |
|------|-----|
| Biến động ngày | 1,9% |
| Biến động/năm | 30,2% |
| Sụt giảm tối đa | −38,5% (đỉnh 2022.04 → đáy 2022.11) |
| VaR(95%, 1 phiên) | −2,6% (bị biên độ chặn) |
| VaR(95%, 10 phiên) | −12,8% (bắt rủi ro chuỗi sàn) |
| CVaR(95%, 1 phiên) | −4,1% |
| Độ lệch | −0,55 |
| Độ nhọn | 6,8 (đuôi béo) |

### Kết quả stress test
| Kịch bản | Lỗ danh mục | Kích hoạt call margin? |
|------|---------|----------|
| Tái hiện COVID 2020 | −22,5% | Không |
| Lãi suất +200bp | −16,3% | Không |
| Giải chấp margin (mid/small) | −34,7% | CÓ |
| Đóng băng TPDN BĐS 2022 | −31,0% | CÓ |

### Monte Carlo (252 phiên, 10.000 đường)
| Thống kê | Giá trị |
|------|-----|
| Lợi suất kỳ vọng | +9,2% |
| Xác suất lỗ | 38% |
| Kịch bản 5% xấu nhất | −26,4% |

### Khuyến nghị kiểm soát rủi ro
1. Đặt ngưỡng cắt lỗ danh mục quanh −15% đến −20% (biên độ VN rộng, đừng đặt quá sát).
2. Giảm/khử đòn bẩy margin trước vùng rủi ro để tránh vòng xoáy giải chấp.
3. Phòng hộ beta bằng **short VN30F** hoặc **nâng tiền mặt** (KHÔNG short được cổ phiếu).
4. Tương quan tăng vọt trong khủng hoảng → lợi ích đa dạng hóa bị chiết khấu mạnh; giảm tập trung mid/small thanh khoản kém.
```

## Lưu ý quan trọng

1. **VaR không phải mức lỗ tối đa**: VaR chỉ nói "95% xác suất lỗ không vượt X"; 5% còn lại có thể tệ hơn nhiều — ở VN là chuỗi sàn.
2. **Giả định chuẩn rất nguy hiểm**: lợi suất cổ phiếu VN gần như luôn fat-tail → VaR tham số đánh giá thấp rủi ro.
3. **Biên độ trần/sàn che giấu rủi ro 1 ngày**: phải đo trên nhiều phiên / drawdown mới thấy rủi ro thật.
4. **Lịch sử ≠ tương lai**: mô phỏng lịch sử thất bại khi có đứt gãy cấu trúc (vd khủng hoảng TPDN 2022 là mới với thị trường).
5. **Tương quan bất ổn**: ma trận tương quan thời bình sụp đổ trong khủng hoảng (tương quan → 1, sàn la liệt 2022).
6. **Seed Monte Carlo**: đặt seed để tái lập; tối thiểu 10.000 đường.
7. **Quy tắc căn bậc hai theo thời gian** chỉ đúng khi lợi suất i.i.d.; sai khi có tự tương quan — mà chuỗi sàn VN có tự tương quan mạnh.
8. **Đòn bẩy margin là biến rủi ro số 1 ở VN**: stress test phải mô phỏng kích hoạt call margin / force-sell, không chỉ lỗ NAV.
9. **Rủi ro trong backtest**: `metrics.csv` đã có `max_drawdown` và `sharpe`; skill này phân tích sâu hơn.


## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)

1. **Không bịa/cook số liệu.** Mọi số tài chính phải có nguồn thật. Luôn **audit nhanh, cross-check tối thiểu 2 nguồn uy tín** (vd `cafef.vn`, `vietstock.vn`) — dùng **crawl4ai** cào số rồi đối chiếu; nếu nguồn lệch nhau thì nêu rõ, không chọn bừa.
2. **Nếu DataPro VÀ vnstock đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
