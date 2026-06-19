---
name: quant-statistics
description: "Phương pháp thống kê định lượng cho TTCK VN — kiểm định nghiệm đơn vị ADF / đồng tích hợp, mô hình biến động GARCH, chẩn đoán hồi quy (phương sai thay đổi / tự tương quan), Bootstrap, kiểm định giả thuyết. Lưu ý VN: cấm bán khống → pair-trading cổ điển không khả thi (long-only / phòng hộ VN30F)."
category: analysis
---

# Phương pháp thống kê định lượng (Việt Nam)

## Mục đích

Bộ phương pháp thống kê dùng trong đầu tư định lượng: kiểm định chuỗi thời gian, mô hình biến động, chẩn đoán hồi quy, suy luận thống kê — nền tảng cho phát triển chiến lược & nghiên cứu nhân tố. Phần lớn là **phương pháp phổ quát** (toán không đổi theo thị trường); các điểm đặc thù VN được đánh dấu ⚠️.

> **Nguồn dữ liệu:** giá/KL từ **DataPro** (mã `.VN`), dùng **log-return**. Chuỗi P/E–P/B nếu cần lấy từ skill định giá ([[valuation-model]]) — KHÔNG dùng `ratio()` vnstock (lỗi thời).

## Kiểm định chuỗi thời gian

### 1. Kiểm định nghiệm đơn vị ADF (tính dừng)

**Vì sao quan trọng:** hồi quy trực tiếp chuỗi không dừng dễ tạo **hồi quy giả** (spurious), kết luận sai.

```python
from statsmodels.tsa.stattools import adfuller

def adf_test(series: pd.Series, significance: float = 0.05) -> dict:
    """
    Kiểm định ADF: H0 = có nghiệm đơn vị (không dừng), H1 = dừng.

    Args:
        series: chuỗi thời gian
        significance: mức ý nghĩa
    Returns:
        kết quả kiểm định
    """
    result = adfuller(series.dropna(), autolag='AIC')
    return {
        'adf_statistic': result[0],
        'p_value': result[1],
        'lags_used': result[2],
        'is_stationary': result[1] < significance,
        'critical_values': result[4],  # 1%, 5%, 10%
    }
```

**Quy tắc quyết định:**

| p-value | Kết luận | Hành động |
|-----|------|------|
| < 0,01 | Dừng mạnh | Dùng trực tiếp cho hồi quy/mô hình |
| 0,01–0,05 | Dừng | Dùng được |
| 0,05–0,10 | Bằng chứng yếu | Sai phân rồi kiểm lại |
| > 0,10 | Không dừng | Phải sai phân hoặc xử lý bằng đồng tích hợp |

**Tính dừng của các chuỗi tài chính thường gặp:**

| Chuỗi | Kết quả điển hình | Xử lý |
|------|---------|---------|
| Chuỗi giá | Không dừng (nghiệm đơn vị) | Dùng log-return |
| Log-return | Dừng | Dùng trực tiếp |
| Chuỗi P/E, P/B | Thường không dừng | Dùng thay đổi hoặc log |
| Chuỗi biến động | Thường dừng | Dùng trực tiếp |
| Khối lượng | Có thể không dừng | Dùng log hoặc chuẩn hóa |

### 2. Kiểm định đồng tích hợp (cointegration)

**Mục đích:** xác định hai chuỗi không dừng có quan hệ cân bằng dài hạn không (nền tảng pair-trading / chênh lệch thống kê).

```python
from statsmodels.tsa.stattools import coint

def cointegration_test(y: pd.Series, x: pd.Series) -> dict:
    """
    Kiểm định đồng tích hợp Engle-Granger hai bước.
    H0: không có quan hệ đồng tích hợp.

    Args:
        y, x: hai chuỗi giá
    Returns:
        kết quả kiểm định
    """
    score, p_value, critical = coint(y, x)
    return {
        'test_statistic': score,
        'p_value': p_value,
        'is_cointegrated': p_value < 0.05,
        'critical_values': {'1%': critical[0], '5%': critical[1], '10%': critical[2]},
    }
```

**Áp dụng pair-trading:**

```python
import statsmodels.api as sm

def find_hedge_ratio(y: pd.Series, x: pd.Series) -> dict:
    """
    Tính tỷ lệ phòng hộ: y = α + β×x + ε ;  Spread = y − β×x
    """
    x_const = sm.add_constant(x)
    model = sm.OLS(y, x_const).fit()
    spread = y - model.params[1] * x
    return {
        'hedge_ratio': model.params[1],
        'intercept': model.params[0],
        'spread_mean': spread.mean(),
        'spread_std': spread.std(),
        'half_life': compute_half_life(spread),  # tốc độ hồi quy về trung bình
    }

def compute_half_life(spread: pd.Series) -> float:
    """Ước lượng half-life bằng hồi quy OLS."""
    spread_lag = spread.shift(1)
    delta = spread - spread_lag
    model = sm.OLS(delta.dropna(), sm.add_constant(spread_lag.dropna())).fit()
    half_life = -np.log(2) / model.params[1]
    return half_life
```

**Tín hiệu pair-trading:**

```
z_score = (spread − mean) / std

| z_score | Tín hiệu |
|---------|------|
| > 2,0 | Short spread (bán y, mua x) |
| > 1,5 | Short spread nhỏ |
| < −1,5 | Long spread nhỏ |
| < −2,0 | Long spread (mua y, bán x) |
| Về gần 0 | Đóng vị thế |
```

> ⚠️ **VN CẤM BÁN KHỐNG CỔ PHIẾU → pair-trading cổ điển (đồng thời short chân đắt) KHÔNG khả thi.**
> Đồng tích hợp vẫn hữu ích nhưng chỉ thực thi được:
> - **Relative-value long-only:** khi z_score < −2 → chỉ MUA chân rẻ (y), KHÔNG short chân đắt; chốt khi z về 0. Bỏ qua tín hiệu z > 2 (không short được).
> - **Phòng hộ beta bằng VN30F:** giữ rổ long + short VN30F để trung hòa thị trường, thay vì short cổ phiếu.
> - **Chuyển hóa luân phiên cặp/ngành:** dùng spread để chuyển tỷ trọng giữa hai mã cùng ngành (overweight chân rẻ, underweight chân đắt) trong danh mục long-only.
> Xem [[correlation-analysis]] / [[pair-trading]] cho khung relative-value VN.

### 3. Kiểm định nhân quả Granger

```python
from statsmodels.tsa.stattools import grangercausalitytests

def granger_test(data: pd.DataFrame, x_col: str, y_col: str, max_lag: int = 5):
    """
    Kiểm tra x có Granger-cause y không (lịch sử x có giúp dự báo y không).
    Lưu ý: nhân quả Granger KHÔNG phải nhân quả thật, chỉ là nhân quả dự báo.
    """
    results = grangercausalitytests(data[[y_col, x_col]].dropna(), maxlag=max_lag)
    return {lag: results[lag][0]['ssr_ftest'][1] for lag in range(1, max_lag+1)}
```
> Ứng dụng VN hữu ích: khối ngoại ròng → giá; basis VN30F → VN30 spot; GTGD → biến động.

## Mô hình biến động GARCH

### Mô hình GARCH(1,1)

```
Suất sinh lời: r_t = μ + ε_t
Biến động:     σ²_t = ω + α×ε²_{t-1} + β×σ²_{t-1}

Ý nghĩa tham số:
- ω (omega): nền phương sai dài hạn
- α (alpha): tác động cú sốc hôm qua lên biến động hôm nay
- β (beta): độ dai dẳng của biến động hôm qua sang hôm nay
- α + β: độ dai dẳng biến động (thường 0,95–0,99)
- Biến động dài hạn = sqrt(ω / (1 − α − β))
```

```python
from arch import arch_model

def fit_garch(returns: pd.Series) -> dict:
    """
    Khớp mô hình GARCH(1,1).

    Args:
        returns: chuỗi suất sinh lời ngày (dạng %)
    Returns:
        tham số mô hình và dự báo
    """
    model = arch_model(returns * 100, vol='Garch', p=1, q=1,
                       mean='Constant', dist='normal')
    result = model.fit(disp='off')
    forecast = result.forecast(horizon=5)  # dự báo biến động 5 ngày tới
    return {
        'omega': result.params['omega'],
        'alpha': result.params['alpha[1]'],
        'beta': result.params['beta[1]'],
        'persistence': result.params['alpha[1]'] + result.params['beta[1]'],
        'long_run_vol': np.sqrt(result.params['omega'] /
                        (1 - result.params['alpha[1]'] - result.params['beta[1]'])) / 100,
        'current_vol': np.sqrt(result.conditional_volatility[-1]) / 100,
        'forecast_vol_5d': np.sqrt(forecast.variance.values[-1, :]) / 100,
        'aic': result.aic,
        'bic': result.bic,
    }
```

### Biến thể GARCH

| Mô hình | Đặc điểm | Tình huống dùng |
|------|------|---------|
| GARCH(1,1) | Cơ sở, phản ứng cú sốc đối xứng | Mặc định |
| EGARCH | Bất đối xứng (hiệu ứng đòn bẩy) | Biến động khi giảm > khi tăng |
| GJR-GARCH | Dạng bất đối xứng khác | Như EGARCH, dễ diễn giải hơn |
| FIGARCH | Trí nhớ dài | Cụm biến động kéo dài rất lâu |

**Đặc điểm GARCH ở VN-Index (ĐỊNH TÍNH — ước lượng lại trên dữ liệu thật):**
```
- Hiệu ứng đòn bẩy rõ: biến động khi giảm > khi tăng → EGARCH/GJR thường khớp tốt hơn.
- Đuôi dày (fat tail) mạnh; ⚠️ biên độ trần/sàn ±7% (HOSE) CẮT đuôi phân phối trong 1 phiên,
  nhưng chuỗi sàn do giải chấp tạo cụm biến động kéo dài → cẩn trọng khi diễn giải α, β.
- α, β cụ thể PHẢI tự khớp trên VN-Index/mã; đừng bê tham số A股/BTC.
```

## Chẩn đoán hồi quy

### 1. Kiểm định phương sai thay đổi (heteroskedasticity)

```python
from statsmodels.stats.diagnostic import het_white, het_breuschpagan

def heteroscedasticity_test(model_result) -> dict:
    """Kiểm tra phần dư có phương sai thay đổi không. H0: phương sai đồng nhất."""
    white_stat, white_p, _, _ = het_white(model_result.resid, model_result.model.exog)
    bp_stat, bp_p, _, _ = het_breuschpagan(model_result.resid, model_result.model.exog)
    return {
        'white_p': white_p,
        'bp_p': bp_p,
        'has_heteroscedasticity': white_p < 0.05 or bp_p < 0.05,
        'fix': 'Dùng sai số chuẩn HAC (Newey-West) hoặc WLS' if white_p < 0.05 else 'Không cần điều chỉnh',
    }
```

**Khắc phục phương sai thay đổi:**
- Dùng `model.fit(cov_type='HAC', cov_kwds={'maxlags': 5})`
- Hoặc bình phương tối thiểu có trọng số (WLS)
- Dữ liệu tài chính gần như luôn có phương sai thay đổi → mặc định dùng sai số chuẩn HAC.

### 2. Kiểm định tự tương quan

```python
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.stats.stattools import durbin_watson

def autocorrelation_test(residuals: pd.Series, lags: int = 10) -> dict:
    """Kiểm tra phần dư có tự tương quan không. H0: không tự tương quan."""
    dw = durbin_watson(residuals)  # DW (chỉ bậc 1)
    lb_result = acorr_ljungbox(residuals, lags=lags)  # Ljung-Box (nhiều bậc)
    return {
        'durbin_watson': dw,
        'dw_interpretation': 'tự tương quan dương' if dw < 1.5 else 'không tự tương quan' if dw < 2.5 else 'tự tương quan âm',
        'ljung_box_p': lb_result['lb_pvalue'].values,
        'has_autocorrelation': any(lb_result['lb_pvalue'] < 0.05),
        'fix': 'Dùng sai số chuẩn Newey-West hoặc thêm biến trễ',
    }
```

### 3. Kiểm định đa cộng tuyến

```python
from statsmodels.stats.outliers_influence import variance_inflation_factor

def vif_test(X: pd.DataFrame) -> pd.DataFrame:
    """
    VIF kiểm tra đa cộng tuyến.  VIF > 10 → nghiêm trọng; VIF > 5 → cần lưu ý.
    """
    vif_data = pd.DataFrame()
    vif_data['feature'] = X.columns
    vif_data['VIF'] = [variance_inflation_factor(X.values, i) for i in range(X.shape[1])]
    vif_data['concern'] = vif_data['VIF'].apply(
        lambda x: 'nghiêm trọng' if x > 10 else 'lưu ý' if x > 5 else 'bình thường'
    )
    return vif_data
```

### Checklist chẩn đoán hồi quy

```
□ 1. Tuyến tính: phần dư vs giá trị khớp không có mẫu rõ ràng
□ 2. Chuẩn: QQ-plot phần dư gần đường thẳng, Jarque-Bera p>0,05
□ 3. Phương sai thay đổi: White/BP p>0,05, hoặc dùng sai số chuẩn HAC
□ 4. Tự tương quan: DW≈2, Ljung-Box p>0,05
□ 5. Đa cộng tuyến: VIF<5
□ 6. Điểm ngoại lai: Cook's D < 4/n
```

## Phương pháp Bootstrap

### Bootstrap phi tham số

```python
def bootstrap_statistic(data: np.ndarray, statistic_func,
                        n_bootstrap: int = 10000,
                        confidence: float = 0.95) -> dict:
    """
    Ước lượng khoảng tin cậy của một thống kê bằng Bootstrap.

    Args:
        data: dữ liệu gốc
        statistic_func: hàm thống kê (vd np.mean, np.median)
        n_bootstrap: số lần lấy mẫu lại
        confidence: mức tin cậy
    Returns:
        ước lượng điểm và khoảng tin cậy
    """
    n = len(data)
    bootstrap_stats = np.array([
        statistic_func(np.random.choice(data, size=n, replace=True))
        for _ in range(n_bootstrap)
    ])
    alpha = 1 - confidence
    lower = np.percentile(bootstrap_stats, alpha/2 * 100)
    upper = np.percentile(bootstrap_stats, (1 - alpha/2) * 100)
    return {
        'point_estimate': statistic_func(data),
        'bootstrap_mean': np.mean(bootstrap_stats),
        'bootstrap_std': np.std(bootstrap_stats),
        'ci_lower': lower,
        'ci_upper': upper,
        'confidence': confidence,
    }
```

### Ứng dụng Bootstrap trong định lượng

| Tình huống | Phương pháp | Mục đích |
|------|------|------|
| Khoảng tin cậy Sharpe | Bootstrap chuỗi suất sinh lời | Sharpe có thực sự >0 không |
| Kiểm định lợi suất nhân tố | Bootstrap giá trị nhân tố | Phần bù nhân tố có bền không |
| Phân phối max drawdown | Bootstrap đường vốn | Phân phối xác suất sụt giảm tối đa |
| So sánh chiến lược | Paired Bootstrap | A có hơn B có ý nghĩa không |

```python
def bootstrap_sharpe(returns: pd.Series, n_bootstrap: int = 10000) -> dict:
    """Khoảng tin cậy Bootstrap cho tỷ số Sharpe."""
    def sharpe(r):
        return r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else 0
    result = bootstrap_statistic(returns.values, sharpe, n_bootstrap)
    result['is_significant'] = result['ci_lower'] > 0  # KTC 95% loại trừ 0
    return result
```

## Khung kiểm định giả thuyết

### Tra cứu nhanh các kiểm định thường dùng

| Mục tiêu kiểm định | Phương pháp | Giả thuyết không |
|---------|---------|--------|
| Trung bình = 0 | t-test | `μ = 0` |
| Hai trung bình bằng nhau | t-test độc lập | `μ1 = μ2` |
| Tính chuẩn | Jarque-Bera | Phân phối chuẩn |
| Tính dừng | ADF | Có nghiệm đơn vị (không dừng) |
| Tự tương quan | Ljung-Box | Không tự tương quan |
| Phương sai thay đổi | White / BP | Phương sai đồng nhất |
| Đồng tích hợp | Engle-Granger | Không đồng tích hợp |

### Vấn đề kiểm định bội (multiple testing)

```
Vấn đề: kiểm 100 nhân tố, lọc p<0,05 → kỳ vọng 5 dương tính giả.

Phương pháp hiệu chỉnh:
1. Bonferroni: p_adj = p × n_tests (thận trọng nhất)
2. Holm-Bonferroni: hiệu chỉnh từng bước (khá thận trọng)
3. Benjamini-Hochberg (FDR): kiểm soát tỷ lệ phát hiện sai (khuyên dùng)

from statsmodels.stats.multitest import multipletests
reject, p_adj, _, _ = multipletests(p_values, method='fdr_bh')
```

### Ý nghĩa thống kê trong backtest tài chính

```
Kiểm định ý nghĩa Sharpe:
H0: Sharpe = 0 (chiến lược vô hiệu)
H1: Sharpe > 0

Thống kê kiểm định: t = Sharpe × sqrt(n) / sqrt(1 + 0,5×Sharpe²)
với n = số kỳ quan sát (năm)

Quy tắc kinh nghiệm:
- Sharpe > 0,5 và backtest >5 năm → có thể có ý nghĩa
- Sharpe > 1,0 và backtest >3 năm → khả năng có ý nghĩa
- Sharpe > 2,0 → cảnh báo overfitting (khó duy trì thực tế)
⚠️ VN: lịch sử dữ liệu sạch ngắn (HOSE từ 2000, thanh khoản/đại chúng thực sự ~2015+) →
   số quan sát ĐỘC LẬP ít hơn vẻ ngoài → đòi hỏi Sharpe cao hơn để tin, và OOS bắt buộc.
```

## Mẫu output

```markdown
## Báo cáo kiểm định thống kê

### Kiểm định tính dừng
| Chuỗi | Thống kê ADF | p-value | Kết luận |
|------|----------|-----|------|
| Giá | −1,23 | 0,65 | Không dừng |
| Suất sinh lời | −15,8 | 0,000 | Dừng *** |

### Kiểm định đồng tích hợp
| Cặp | Thống kê | p-value | Đồng tích hợp |
|------|--------|-----|------|
| VCB/CTG | −4,52 | 0,002 | Có ** (chỉ thực thi long-only chân rẻ — cấm bán khống) |

### Mô hình GARCH (VN-Index)
| Tham số | Giá trị | Ý nghĩa |
|------|-----|------|
| α | 0,08 | Tác động cú sốc |
| β | 0,88 | Độ dai dẳng biến động |
| Biến động dài hạn | 22,5% | Quy năm |

### Kết quả Bootstrap
| Chỉ tiêu | Ước lượng điểm | KTC 95% | Có ý nghĩa |
|------|--------|--------|------|
| Sharpe | 1,25 | [0,62, 1,88] | Có |
| Alpha (tháng) | 0,8% | [0,1%, 1,5%] | Có |
```

## Lưu ý

1. **Dữ liệu tài chính phi chuẩn**: hầu hết chuỗi suất sinh lời đuôi dày → cẩn trọng với kiểm định giả định phân phối chuẩn.
2. **Kiểm định bội**: khi backtest nhiều chiến lược/nhân tố, BẮT BUỘC hiệu chỉnh kiểm định bội (kiểm soát FDR).
3. **Kiểm out-of-sample**: ý nghĩa thống kê KHÔNG đảm bảo sinh lời; vẫn cần OOS.
4. **Đồng tích hợp có thể đổ vỡ**: quan hệ lịch sử không đảm bảo bền → relative-value cần giám sát liên tục.
5. **GARCH dự báo ngắn hạn**: độ chính xác giảm nhanh sau 5–10 ngày.
6. **Cẩn trọng mẫu nhỏ**: dữ liệu tài chính trông lớn nhưng số quan sát độc lập có thể ít (đặc biệt VN, dữ liệu sạch ngắn).
7. **Rủi ro p-hacking**: đừng chỉnh đến khi p<0,05; định trước kế hoạch kiểm định.
8. ⚠️ **Cấm bán khống (VN)**: mọi tín hiệu cần short chân đắt (pair, z>2) KHÔNG thực thi được — chuyển long-only chân rẻ / phòng hộ VN30F. T+2,5 ảnh hưởng tốc độ vào-ra.

## Phụ thuộc

```bash
pip install pandas numpy statsmodels arch scipy
```


## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)

1. **Không bịa/cook số liệu.** Mọi số tài chính phải có nguồn thật. Luôn **audit nhanh, cross-check tối thiểu 2 nguồn uy tín** (vd `cafef.vn`, `vietstock.vn`) — dùng **crawl4ai** cào số rồi đối chiếu; nếu nguồn lệch nhau thì nêu rõ, không chọn bừa.
2. **Nếu DataPro VÀ vnstock đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
