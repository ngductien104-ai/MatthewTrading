---
name: correlation-analysis
description: "Phân tích tương quan & đồng tích hợp (cointegration) cho TTCK VN — quét cặp đồng pha, phân tích tương quan lợi suất chuyên sâu, phân cụm ngành, tương quan thực hiện theo chế độ thị trường, kiểm định Engle-Granger/Johansen, half-life, hedge ratio động Kalman, liên thông xuyên thị trường, sinh tín hiệu cặp. LƯU Ý: VN cấm bán khống cổ phiếu → pairs trading cổ điển long/short 2 cổ phiếu KHÔNG thực hiện được; khung này dùng cho relative-value long-only, phòng hộ beta bằng VN30F, phân cụm rủi ro."
category: analysis
---

# Phân tích tương quan & đồng tích hợp (Việt Nam)

## Mục đích

Tương quan là công cụ nền tảng cho relative value, xây dựng danh mục và quản trị rủi ro. Skill này gồm bốn chế độ phân tích (quét cặp đồng pha / tương quan lợi suất chuyên sâu / phân cụm ngành / tương quan thực hiện), khung kiểm định đồng tích hợp đầy đủ, phân tích liên thông xuyên thị trường, và quy trình từ phân tích đến tín hiệu giao dịch cặp.

> **Cảnh báo đặc thù VN — đọc trước tiên:** **TTCK VN cấm bán khống cổ phiếu** và gần như không có cho vay chứng khoán (SBL) cho NĐT thường. Vì vậy **pairs trading cổ điển (long mã rẻ / short mã đắt) KHÔNG thực hiện được với hai cổ phiếu.** Khung đồng tích hợp/Z-Score dưới đây ở VN dùng cho:
> 1. **Relative-value xoay vòng (long-only)**: khi cặp lệch khỏi cân bằng, **chuyển vốn** từ mã đắt sang mã rẻ, không mở vị thế short.
> 2. **Phòng hộ beta bằng VN30F**: short hợp đồng tương lai chỉ số để trung hòa beta của một rổ long cổ phiếu.
> 3. **Spread giữa các kỳ hạn VN30F** (calendar spread) — phái sinh được phép 2 chiều.
> 4. **Tìm mã thay thế** khi mã đích cạn room ngoại / kém thanh khoản.
> 5. **Phân cụm rủi ro & kiểm tra đa dạng hóa danh mục.**
> Đọc tín hiệu "short spread" bên dưới theo nghĩa **giảm tỷ trọng mã đắt / phòng hộ VN30F**, không phải bán khống cổ phiếu.

---

## Chế độ 1: Quét cặp đồng pha (Co-Movement Discovery)

**Tình huống**: cho một mã đích, quét một rổ để tìm các mã tương quan cao, lập danh sách ứng viên cùng ngành/cùng nhân tố — phục vụ relative value hoặc tìm mã thay thế.

### Quy trình

```
1. Lấy chuỗi lợi suất ngày của mã đích và N ứng viên
2. Tính tương quan Pearson / Spearman giữa mã đích và từng ứng viên
3. Xếp hạng giảm dần theo tương quan, giữ Top-K (thường K=10–20)
4. Kiểm định đồng tích hợp trên Top-K để giữ các cặp có cân bằng dài hạn thật
5. Xuất danh sách ứng viên + tóm tắt tương quan
```

```python
import pandas as pd
import numpy as np
from scipy.stats import pearsonr, spearmanr

def scan_correlated_assets(
    target_returns: pd.Series,
    universe_returns: pd.DataFrame,
    top_k: int = 20,
    min_corr: float = 0.5,
    method: str = "pearson",
) -> pd.DataFrame:
    """Quét các mã tương quan cao với mã đích.

    Args:
        target_returns: Chuỗi lợi suất ngày của mã đích
        universe_returns: Ma trận lợi suất rổ ứng viên, cột là mã
        top_k: Số ứng viên trả về
        min_corr: Ngưỡng tương quan tuyệt đối tối thiểu
        method: "pearson" hoặc "spearman"

    Returns:
        DataFrame gồm symbol / corr / p_value / rank
    """
    aligned = universe_returns.dropna(axis=1, how="any")
    aligned, target_aligned = aligned.align(target_returns, join="inner", axis=0)

    results = []
    for col in aligned.columns:
        if method == "spearman":
            corr, p = spearmanr(target_aligned, aligned[col])
        else:
            corr, p = pearsonr(target_aligned, aligned[col])
        results.append({"symbol": col, "corr": corr, "p_value": p})

    df = pd.DataFrame(results)
    df = df[df["corr"].abs() >= min_corr].sort_values("corr", ascending=False)
    df["rank"] = range(1, len(df) + 1)
    return df.head(top_k).reset_index(drop=True)
```

**Hướng dẫn sàng lọc**:

| Tương quan | Kết luận | Hành động tiếp theo |
|---------|------|---------|
| > 0,8 | Đồng pha mạnh | Đưa vào hàng đợi kiểm định đồng tích hợp |
| 0,6 – 0,8 | Đồng pha vừa | Kiểm tra cùng ngành/nhân tố trước khi test đồng tích hợp |
| < 0,6 | Tương quan yếu | Thường không phù hợp relative value |
| Âm và < −0,6 | Nghịch pha mạnh | Hiếm ở VN (đa số cổ phiếu đồng pha theo index); cẩn thận chiều spread |

> **Đặc thù VN:** do thị trường lẻ chi phối và beta cao, **đa số cổ phiếu VN đồng pha mạnh với VN-Index** trong pha sóng → tương quan dương rất phổ biến, tương quan âm bền vững gần như không có giữa hai cổ phiếu. Lọc theo tương quan đơn thuần dễ ra toàn cặp "cùng trôi theo index" — phải dùng đồng tích hợp + cùng ngành để lọc cặp relative-value thật.

---

## Chế độ 2: Tương quan lợi suất chuyên sâu (hai mã)

**Tình huống**: nghiên cứu tương quan đầy đủ cho hai mã — nhiều hệ số tương quan, Beta/R², tương quan cuốn chiếu, Z-Score của spread.

### Chỉ tiêu cốt lõi

```python
import statsmodels.api as sm
from scipy.stats import pearsonr, spearmanr, kendalltau

def bivariate_correlation_analysis(
    y: pd.Series,
    x: pd.Series,
    rolling_window: int = 60,
) -> dict:
    """Phân tích tương quan chuyên sâu cho hai mã.

    Args:
        y: Chuỗi lợi suất ngày của mã A
        x: Chuỗi lợi suất ngày của mã B
        rolling_window: Độ dài cửa sổ cuốn chiếu (phiên)

    Returns:
        Dict các thống kê tương quan
    """
    # Căn chỉnh hai chuỗi.
    df = pd.concat([y.rename("y"), x.rename("x")], axis=1).dropna()
    y_clean, x_clean = df["y"], df["x"]

    # Tương quan tĩnh.
    pearson_r, pearson_p = pearsonr(y_clean, x_clean)
    spearman_r, spearman_p = spearmanr(y_clean, x_clean)
    kendall_r, kendall_p = kendalltau(y_clean, x_clean)

    # OLS: y = α + β·x
    x_const = sm.add_constant(x_clean)
    ols = sm.OLS(y_clean, x_const).fit()
    beta = ols.params["x"]
    alpha = ols.params["const"]
    r_squared = ols.rsquared

    # Tương quan Pearson cuốn chiếu.
    rolling_corr = y_clean.rolling(rolling_window).corr(x_clean)

    # Spread và Z-Score theo hedge ratio.
    spread = y_clean - beta * x_clean
    spread_mean = spread.rolling(rolling_window).mean()
    spread_std = spread.rolling(rolling_window).std()
    z_score = (spread - spread_mean) / spread_std

    return {
        "pearson": {"r": round(pearson_r, 4), "p": round(pearson_p, 6)},
        "spearman": {"r": round(spearman_r, 4), "p": round(spearman_p, 6)},
        "kendall": {"r": round(kendall_r, 4), "p": round(kendall_p, 6)},
        "beta": round(beta, 4),
        "alpha": round(alpha, 6),
        "r_squared": round(r_squared, 4),
        "rolling_corr": rolling_corr,
        "spread": spread,
        "z_score": z_score,
        "spread_mean": spread_mean,
        "spread_std": spread_std,
    }
```

### Hướng dẫn chọn hệ số tương quan

| Hệ số | Giả định | Dùng tốt khi | Không phù hợp khi |
|------|------|---------|--------|
| Pearson | Tuyến tính, xấp xỉ chuẩn | Chuỗi lợi suất | Đuôi nặng / nhiều ngoại lai (cổ phiếu VN) |
| Spearman | Đơn điệu | Xếp hạng/phân vị, nhiều ngoại lai | Khi cần thông tin độ lớn |
| Kendall | Nhất quán thứ tự | Mẫu nhỏ, phân phối chưa rõ | Mẫu lớn (tính chậm) |

**Quy tắc thực chiến**: thường báo cả ba hệ số. Nếu Pearson và Spearman lệch >0,1 thì quan hệ nhiều khả năng phi tuyến/đuôi nặng → ưu tiên Spearman. Ở VN, các phiên trần/sàn tạo ngoại lai → Spearman thường đáng tin hơn Pearson.

---

## Chế độ 3: Phân cụm ngành (Sector Clustering)

**Tình huống**: phân cụm phân cấp trên ma trận tương quan của N mã để phát hiện cấu trúc ngành, kiểm tra đa dạng hóa danh mục, tìm mã tương đồng.

```python
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage, dendrogram, fcluster
from scipy.spatial.distance import squareform
import matplotlib.pyplot as plt
import seaborn as sns

def sector_clustering(
    returns: pd.DataFrame,
    method: str = "ward",
    n_clusters: int = 5,
    figsize: tuple = (12, 10),
) -> dict:
    """Phân cụm ngành.

    Args:
        returns: Ma trận lợi suất ngày đa mã, cột là mã
        method: Phương pháp liên kết: "ward" / "complete" / "average"
        n_clusters: Số cụm mục tiêu
        figsize: Kích thước heatmap

    Returns:
        Dict gồm ma trận tương quan, nhãn cụm, đối tượng hình
    """
    # 1. Ma trận tương quan
    corr_matrix = returns.corr(method="pearson")

    # 2. Ma trận khoảng cách: distance = 1 − |tương quan|
    distance_matrix = 1 - corr_matrix.abs()
    condensed = squareform(distance_matrix.values, checks=False)

    # 3. Phân cụm phân cấp
    linkage_matrix = linkage(condensed, method=method)
    labels = fcluster(linkage_matrix, n_clusters, criterion="maxclust")
    cluster_df = pd.DataFrame({"symbol": corr_matrix.columns, "cluster": labels})

    # 4. Heatmap sắp theo cụm
    order = cluster_df.sort_values("cluster").index
    sorted_corr = corr_matrix.iloc[order, order]

    fig_heatmap, ax = plt.subplots(figsize=figsize)
    sns.heatmap(
        sorted_corr,
        cmap="RdYlGn",
        center=0,
        vmin=-1,
        vmax=1,
        annot=len(corr_matrix) <= 20,
        fmt=".2f",
        ax=ax,
        cbar_kws={"label": "Tương quan Pearson"},
    )
    ax.set_title(f"Heatmap tương quan (thứ tự cụm {method.upper()})")

    # 5. Dendrogram
    fig_dendro, ax2 = plt.subplots(figsize=(figsize[0], 6))
    dendrogram(
        linkage_matrix,
        labels=list(corr_matrix.columns),
        ax=ax2,
        leaf_rotation=90,
        color_threshold=0,
    )
    ax2.set_title(f"Dendrogram phân cấp (liên kết {method.upper()})")
    ax2.set_ylabel("Khoảng cách")

    return {
        "corr_matrix": corr_matrix,
        "cluster_labels": cluster_df,
        "linkage_matrix": linkage_matrix,
        "fig_heatmap": fig_heatmap,
        "fig_dendrogram": fig_dendro,
        "n_clusters": n_clusters,
    }
```

### So sánh ba phương pháp liên kết

| Phương pháp | Đặc điểm | Dùng tốt khi | Điểm yếu |
|------|------|---------|------|
| Ward | Tối thiểu phương sai nội cụm, cụm gọn | **Mặc định khuyến nghị**, phát hiện ngành | Hợp cụm dạng cầu, kém cho hình bất thường |
| Complete | Dùng khoảng cách lớn nhất, bảo thủ | Khi cần tương đồng nội cụm cao | Có thể tạo cụm dài |
| Average | Dùng khoảng cách trung bình, dung hòa | Phân tích chung | Nhạy nhiễu |

> **Ứng dụng VN:** phân cụm thường tái hiện đúng các "họ" cổ phiếu VN — họ ngân hàng, họ chứng khoán, họ thép, họ Vingroup, nhóm dầu khí (theo giá dầu), nhóm điện/nước phòng thủ. Dùng để **kiểm tra đa dạng hóa**: nếu danh mục "10 mã" nhưng 7 mã rơi vào 1 cụm (vd toàn ngân hàng + chứng khoán) → thực chất chỉ là 1 cú đặt cược beta, không đa dạng hóa.

---

## Chế độ 4: Tương quan thực hiện (Realized Correlation)

**Tình huống**: tính chuỗi tương quan cuốn chiếu và phân tích tương quan theo chế độ thị trường (tăng/giảm/biến động cao) để thấy tương quan biến đổi động.

```python
def realized_correlation(
    y: pd.Series,
    x: pd.Series,
    benchmark: pd.Series,
    windows: list = [20, 60, 120],
    vol_window: int = 20,
    vol_threshold: float = 1.5,
) -> dict:
    """Tương quan cuốn chiếu + tương quan theo chế độ.

    Args:
        y, x: Chuỗi lợi suất ngày của hai mã
        benchmark: Lợi suất ngày của chỉ số tham chiếu (VN-Index/VN30) để gán chế độ
        windows: Danh sách cửa sổ cuốn chiếu (phiên)
        vol_window: Cửa sổ biến động
        vol_threshold: Ngưỡng biến động cao (bội số biến động trung bình)

    Returns:
        Chuỗi tương quan cuốn chiếu + tóm tắt tương quan theo chế độ
    """
    df = pd.concat([y.rename("y"), x.rename("x"),
                    benchmark.rename("bm")], axis=1).dropna()

    # Chuỗi tương quan cuốn chiếu.
    rolling_corrs = {}
    for w in windows:
        rolling_corrs[f"roll_{w}d"] = df["y"].rolling(w).corr(df["x"])

    # Gán nhãn chế độ.
    bm_ret_252 = df["bm"].rolling(252).mean()
    bm_vol = df["bm"].rolling(vol_window).std()
    bm_vol_mean = bm_vol.rolling(252).mean()

    df["regime"] = "sideways"
    df.loc[df["bm"] > bm_ret_252, "regime"] = "bull"
    df.loc[df["bm"] < -bm_ret_252.abs(), "regime"] = "bear"
    df.loc[bm_vol > bm_vol_mean * vol_threshold, "regime"] = "high_vol"

    # Tương quan có điều kiện.
    cond_corr = {}
    for regime in ["bull", "bear", "sideways", "high_vol"]:
        mask = df["regime"] == regime
        if mask.sum() >= 30:
            r, p = pearsonr(df.loc[mask, "y"], df.loc[mask, "x"])
            cond_corr[regime] = {"corr": round(r, 4), "p": round(p, 6), "n": int(mask.sum())}
        else:
            cond_corr[regime] = {"corr": None, "p": None, "n": int(mask.sum())}

    return {
        "rolling_corrs": pd.DataFrame(rolling_corrs),
        "regime_labels": df["regime"],
        "conditional_corr": cond_corr,
    }
```

### Hành vi tương quan điển hình theo chế độ (VN)

| Chế độ thị trường | Tương quan cổ phiếu–cổ phiếu | Cổ phiếu–trái phiếu | Đặc trưng TTCK VN |
|---------|---------|---------|--------|
| Tăng (bull) | Vừa (0,4–0,6) | Thấp hoặc âm | Mid/small chạy theo dòng tiền lẻ, đồng pha mạnh |
| Giảm (bear) | **Cao (0,7–0,9)** | Âm (TPCP trú ẩn) | Bán tháo diện rộng, tương quan nhảy vọt |
| Biến động cao | **Rất cao (0,8+)** | Âm | Khủng hoảng (2022) → tương quan → 1, sàn la liệt |
| Đi ngang (sideways) | Thấp (0,2–0,4) | Gần 0 | Phân hóa mạnh, lý tưởng cho relative-value xoay vòng |

---

## Phân tích đồng tích hợp (Cointegration)

Tương quan đo mức đồng pha. Đồng tích hợp đo có tồn tại **quan hệ cân bằng dài hạn** hay không. Tương quan cao không bảo đảm đồng tích hợp, và tương quan thấp không loại trừ đồng tích hợp.

### Engle-Granger hai bước

Phù hợp cặp hai biến, nhanh và trực quan.

```python
from statsmodels.tsa.stattools import coint, adfuller
import statsmodels.api as sm
import numpy as np

def engle_granger_coint(
    y: pd.Series,
    x: pd.Series,
    significance: float = 0.05,
) -> dict:
    """Kiểm định đồng tích hợp Engle-Granger hai bước.

    H0: Không có quan hệ đồng tích hợp (phần dư có nghiệm đơn vị).

    Args:
        y, x: Hai chuỗi GIÁ. Phải là chuỗi không dừng (dùng giá, không dùng lợi suất).
        significance: Mức ý nghĩa

    Returns:
        Kết quả kiểm định + chuỗi spread
    """
    # Bước 1: ước lượng vector đồng tích hợp bằng OLS.
    x_const = sm.add_constant(x)
    ols = sm.OLS(y, x_const).fit()
    hedge_ratio = ols.params[x.name if x.name else "x"]
    intercept = ols.params["const"]
    residuals = ols.resid

    # Bước 2: kiểm định tính dừng của phần dư bằng ADF.
    adf_res = adfuller(residuals, autolag="AIC")
    adf_stat, adf_p = adf_res[0], adf_res[1]

    # Hàm coint của statsmodels.
    coint_stat, coint_p, crit_vals = coint(y, x)

    return {
        "method": "Engle-Granger",
        "is_cointegrated": coint_p < significance,
        "coint_p": round(coint_p, 6),
        "coint_stat": round(coint_stat, 4),
        "critical_values": {"1%": crit_vals[0], "5%": crit_vals[1], "10%": crit_vals[2]},
        "hedge_ratio": round(hedge_ratio, 6),
        "intercept": round(intercept, 6),
        "spread": residuals,
        "adf_on_spread": {"stat": round(adf_stat, 4), "p": round(adf_p, 6)},
    }
```

**Lưu ý**: Engle-Granger chỉ phát hiện một vector đồng tích hợp và kết quả phụ thuộc thứ tự `y`, `x`. Thực chiến: test cả hai chiều, giữ chiều có p-value nhỏ hơn.

### Kiểm định Johansen cho nhiều biến

Phù hợp ba mã trở lên và để ước lượng số vector đồng tích hợp (rank).

```python
from statsmodels.tsa.vector_ar.vecm import coint_johansen

def johansen_coint(
    prices: pd.DataFrame,
    det_order: int = 0,
    k_ar_diff: int = 1,
) -> dict:
    """Kiểm định đồng tích hợp Johansen.

    Args:
        prices: Ma trận giá đa mã, cột là mã. Chuỗi phải không dừng.
        det_order: Thành phần xác định. -1=không chặn, 0=chặn, 1=xu thế
        k_ar_diff: Số sai phân trễ trong VAR, thường 1–5 chọn theo AIC

    Returns:
        Kết quả trace test và max-eigenvalue test
    """
    result = coint_johansen(prices.dropna(), det_order=det_order, k_ar_diff=k_ar_diff)
    n = prices.shape[1]

    # Trace test.
    trace_results = []
    for i in range(n):
        trace_results.append({
            "H0_rank_leq": i,
            "trace_stat": round(result.lr1[i], 4),
            "crit_10pct": result.cvt[i, 0],
            "crit_5pct": result.cvt[i, 1],
            "crit_1pct": result.cvt[i, 2],
            "reject_5pct": result.lr1[i] > result.cvt[i, 1],
        })

    # Max-eigenvalue test.
    maxeig_results = []
    for i in range(n):
        maxeig_results.append({
            "H0_rank_eq": i,
            "maxeig_stat": round(result.lr2[i], 4),
            "crit_10pct": result.cvm[i, 0],
            "crit_5pct": result.cvm[i, 1],
            "crit_1pct": result.cvm[i, 2],
            "reject_5pct": result.lr2[i] > result.cvm[i, 1],
        })

    # Vector đồng tích hợp, chuẩn hóa.
    coint_vectors = pd.DataFrame(
        result.evec[:, :sum(r["reject_5pct"] for r in trace_results)],
        index=prices.columns,
    )

    return {
        "method": "Johansen",
        "n_coint_vectors_trace": sum(r["reject_5pct"] for r in trace_results),
        "trace_test": pd.DataFrame(trace_results),
        "maxeig_test": pd.DataFrame(maxeig_results),
        "coint_vectors": coint_vectors,
        "eigenvalues": result.eig,
    }
```

**Quy tắc đọc rank Johansen**:

```
Bắt đầu trace test từ H0: rank=0 và đi lên.
Rank đầu tiên KHÔNG bác bỏ được chính là rank đồng tích hợp ước lượng.

rank = 0   → không đồng tích hợp
rank = 1   → một vector đồng tích hợp (phổ biến nhất — cân bằng dài hạn của một cặp)
rank = k-1 → k-1 vector (hệ liên kết chặt)
rank = k   → bản thân các chuỗi đã dừng, không cần đồng tích hợp
```

### Tính half-life

Half-life đo thời gian để spread hồi về cân bằng sau khi lệch. Là tham chiếu thực dụng cho kỳ nắm giữ kỳ vọng trong giao dịch cặp.

```python
def compute_half_life(spread: pd.Series) -> float:
    """Ước lượng half-life hồi quy về trung bình bằng OLS (đơn vị: phiên).

    Nguyên lý:
        Ước lượng ΔSpread_t = λ·Spread_{t-1} + ε
        Half-life = -ln(2) / λ, với λ phải âm để có hồi quy về trung bình

    Args:
        spread: Chuỗi spread, nên là chuỗi dừng

    Returns:
        Half-life (phiên). Giá trị âm/vô cực ⇒ phân kỳ.
    """
    spread_lag = spread.shift(1)
    delta = spread.diff()
    df = pd.concat([delta, spread_lag], axis=1).dropna()
    df.columns = ["delta", "lag"]

    x_const = sm.add_constant(df["lag"])
    ols = sm.OLS(df["delta"], x_const).fit()
    lam = ols.params["lag"]

    if lam >= 0:
        return float("inf")  # không hồi quy về trung bình

    half_life = -np.log(2) / lam
    return round(half_life, 1)
```

**Tham chiếu khoảng half-life**:

| Half-life | Ý nghĩa | Hướng dẫn giao dịch |
|-------|------|---------|
| < 5 phiên | Hồi cực nhanh | Vướng T+2 (không bán cổ phiếu vừa mua) → khó khai thác bằng cổ phiếu; cân nhắc phái sinh |
| 5–20 phiên | Hồi nhanh | Khoảng lý tưởng cho relative-value ngắn hạn ở VN |
| 20–60 phiên | Hồi trung bình | Nắm giữ trung hạn, cửa sổ 60–120 phiên |
| 60–180 phiên | Hồi chậm | Nắm giữ dài, theo dõi độ ổn định đồng tích hợp |
| > 180 phiên | Gần bước ngẫu nhiên | Rủi ro cao, dùng thận trọng |

> **Lưu ý T+2:** half-life < 5 phiên về lý thuyết hấp dẫn nhưng ở VN gần như **không khai thác được bằng cổ phiếu** vì cổ phiếu vừa mua phải chờ ~2 phiên mới bán được. Half-life 5–20 phiên là vùng thực tế nhất.

### Hedge ratio động bằng Kalman Filter

OLS tĩnh không bắt được trôi dần của quan hệ đồng tích hợp. Kalman filter cho hedge ratio cập nhật liên tục.

```python
import numpy as np

def kalman_hedge_ratio(
    y: pd.Series,
    x: pd.Series,
    delta: float = 1e-4,
    vt: float = 1.0,
) -> pd.DataFrame:
    """Ước lượng hedge ratio động bằng Kalman filter.

    Phương trình trạng thái:
        β_t = β_{t-1} + w_t,  w ~ N(0, Q)
    Phương trình quan sát:
        y_t = β_t · x_t + v_t,  v ~ N(0, R)

    Args:
        y: Chuỗi giá mã A
        x: Chuỗi giá mã B
        delta: Cường độ nhiễu trạng thái. Lớn hơn ⇒ hedge ratio thích nghi nhanh hơn
        vt: Phương sai nhiễu quan sát

    Returns:
        DataFrame gồm hedge ratio động và spread
    """
    n = len(y)
    # Trạng thái: [β, α] = hedge ratio + chặn
    Wt = delta / (1 - delta) * np.eye(2)
    Vt = vt

    # Khởi tạo
    theta = np.zeros((n, 2))
    P = np.zeros((n, 2, 2))
    P[0] = np.eye(2)

    spread = np.zeros(n)
    spread[0] = float("nan")

    for t in range(1, n):
        F = np.array([x.iloc[t], 1.0])

        # Dự báo
        theta_pred = theta[t - 1]
        P_pred = P[t - 1] + Wt

        # Innovation
        innovation = y.iloc[t] - F @ theta_pred
        S = F @ P_pred @ F.T + Vt

        # Kalman gain
        K = P_pred @ F.T / S

        # Cập nhật
        theta[t] = theta_pred + K * innovation
        P[t] = (np.eye(2) - np.outer(K, F)) @ P_pred

        spread[t] = y.iloc[t] - theta[t, 0] * x.iloc[t] - theta[t, 1]

    return pd.DataFrame({
        "hedge_ratio": theta[:, 0],
        "intercept": theta[:, 1],
        "spread": spread,
    }, index=y.index)
```

**So sánh hedge ratio tĩnh vs động**:

| Phương pháp | Ưu | Nhược | Dùng tốt khi |
|------|------|------|------|
| OLS | Đơn giản, ổn định | Không bắt biến đổi theo thời gian | Cặp ổn định ngắn hạn |
| Rolling OLS | Biến thiên, trực quan | Nhạy cửa sổ, hiệu ứng biên | Cặp trung hạn |
| Kalman Filter | Cập nhật liên tục, thời gian thực | `delta` khó tinh chỉnh | Cặp dài hạn / có dịch chuyển cấu trúc |

---

## Tương quan xuyên thị trường (Cross-Market)

### Tương quan giữa các ngành HOSE

```python
# Mẫu hình tương quan ngành điển hình TTCK VN
VN_SECTOR_PATTERNS = {
    "manh_gt_0_7": [
        "Họ ngân hàng (VCB/BID/CTG/MBB/ACB/TCB)",
        "Họ chứng khoán (SSI/HCM/VND/VCI) — beta cao theo index",
        "Họ thép (HPG/HSG/NKG)",
        "Họ Vingroup (VIC/VHM/VRE)",
    ],
    "vua_0_4_to_0_7": [
        "BĐS ↔ xây dựng/vật liệu (thép, xi măng)",
        "Bán lẻ/tiêu dùng (MWG/FRT/PNJ/DGW)",
        "Dầu khí (GAS/PLX/PVS/PVD/BSR) — theo giá dầu Brent",
    ],
    "thap_hoac_am_lt_0_3": [
        "Điện/nước phòng thủ (POW/NT2/REE) ↔ nhóm đầu cơ",
        "Phòng thủ (dược, điện nước) ↔ chu kỳ",
    ],
}
```

### Phân tích liên thông xuyên thị trường

```python
def cross_market_correlation(
    markets: dict,  # {"VN-Index": series, "S&P500": series, "Brent": series, "USD/VND": series}
    rolling_window: int = 60,
    lag_days: list = [0, 1, 2, 3],
) -> dict:
    """Tương quan xuyên thị trường + phân tích dẫn-trễ (lead-lag).

    Args:
        markets: Chuỗi lợi suất ngày của từng thị trường/yếu tố
        rolling_window: Cửa sổ cuốn chiếu
        lag_days: Danh sách độ trễ cần test

    Returns:
        Ma trận tương quan, phân tích dẫn-trễ, tương quan cuốn chiếu
    """
    df = pd.DataFrame(markets).dropna()

    # Ma trận tương quan tĩnh
    static_corr = df.corr()

    # Tương quan dẫn-trễ để phát hiện truyền dẫn xuyên thị trường
    lead_lag = {}
    mkt_names = list(markets.keys())
    for i, m1 in enumerate(mkt_names):
        for m2 in mkt_names[i + 1:]:
            pair_key = f"{m1}_{m2}"
            lead_lag[pair_key] = {}
            for lag in lag_days:
                if lag == 0:
                    r, _ = pearsonr(df[m1], df[m2])
                else:
                    r, _ = pearsonr(df[m1].iloc[lag:], df[m2].iloc[:-lag])
                lead_lag[pair_key][f"lag_{lag}d"] = round(r, 4)

    # Tương quan cuốn chiếu
    rolling_corrs = {}
    for i, m1 in enumerate(mkt_names):
        for m2 in mkt_names[i + 1:]:
            key = f"{m1}_{m2}"
            rolling_corrs[key] = df[m1].rolling(rolling_window).corr(df[m2])

    return {
        "static_corr": static_corr,
        "lead_lag": pd.DataFrame(lead_lag).T,
        "rolling_corrs": pd.DataFrame(rolling_corrs),
    }
```

### Mẫu hình liên thông xuyên thị trường (thực nghiệm VN)

| Cặp thị trường | Tương quan TB | Chiều truyền dẫn | Độ trễ |
|-------|---------|---------|------|
| VN-Index ↔ S&P500 / Nasdaq | 0,2–0,4 | Mỹ dẫn qua đêm (tâm lý toàn cầu) | 1 phiên |
| VN-Index ↔ MSCI EM / Frontier | 0,3–0,5 | Dòng vốn ngoại (ETF) | 0–1 phiên |
| Nhóm dầu khí VN (GAS/PVS/PVD/BSR) ↔ Brent | 0,4–0,7 | Giá dầu dẫn | 0–1 phiên |
| Nhóm thép VN (HPG/HSG) ↔ giá HRC/thép Trung Quốc | 0,3–0,6 | Giá thép TQ dẫn | 0–2 phiên |
| VN-Index ↔ USD/VND | −0,2 đến 0,1 | USD/VND tăng → khối ngoại rút → VN yếu | 0–2 phiên |
| VN-Index ↔ A-share Trung Quốc | 0,1–0,3 | Liên thông yếu, đa phần độc lập | Bất ổn |

### Tác động của yếu tố tỷ giá lên tương quan xuyên thị trường

Khi so sánh xuyên thị trường, phải phân biệt lợi suất theo nội tệ và lợi suất đã điều chỉnh tỷ giá; nếu không, biến động tỷ giá tạo tương quan giả hoặc che giấu tương quan thật.

```python
def fx_adjusted_correlation(
    foreign_price: pd.Series,   # giá thị trường nước ngoài, mệnh giá ngoại tệ
    domestic_price: pd.Series,  # giá thị trường trong nước (VN)
    fx_rate: pd.Series,         # ngoại tệ / nội tệ, vd USD/VND
) -> dict:
    """Tương quan xuyên thị trường đã điều chỉnh tỷ giá.

    Args:
        foreign_price: Chuỗi giá nước ngoài (ngoại tệ)
        domestic_price: Chuỗi giá trong nước (VND)
        fx_rate: Tỷ giá dạng ngoại tệ / nội tệ (USD/VND)

    Returns:
        Tương quan thô vs tương quan điều chỉnh tỷ giá
    """
    # Lợi suất nước ngoài quy VND = lợi suất nước ngoài + lợi suất tỷ giá
    foreign_ret = foreign_price.pct_change()
    fx_ret = fx_rate.pct_change()
    foreign_ret_vnd = (1 + foreign_ret) * (1 + fx_ret) - 1

    domestic_ret = domestic_price.pct_change()

    df = pd.concat([foreign_ret.rename("foreign_raw"),
                    foreign_ret_vnd.rename("foreign_domestic"),
                    domestic_ret.rename("domestic"),
                    fx_ret.rename("fx")], axis=1).dropna()

    raw_corr, _ = pearsonr(df["foreign_raw"], df["domestic"])
    adj_corr, _ = pearsonr(df["foreign_domestic"], df["domestic"])
    fx_corr, _ = pearsonr(df["fx"], df["domestic"])

    return {
        "raw_corr_foreign_domestic": round(raw_corr, 4),
        "fx_adjusted_corr": round(adj_corr, 4),
        "fx_domestic_corr": round(fx_corr, 4),
        "fx_contribution": round(adj_corr - raw_corr, 4),
        "note": "fx_contribution > 0 nghĩa là tỷ giá khuếch đại tương quan xuyên thị trường",
    }
```

> **Đặc thù VN:** USD/VND được điều hành tương đối ổn định (biên độ thường ±3%/năm) nên đóng góp tỷ giá nhỏ hơn nhiều so với CNY/các đồng EM khác. Tuy vậy điều chỉnh tỷ giá vẫn quan trọng khi nhìn dưới góc **NĐT nước ngoài** (lợi suất quy USD): các đợt USD/VND mất giá mạnh (2022, 2024) trùng với khối ngoại bán ròng → tương quan VN-Index ↔ tỷ giá đổi dấu trong các giai đoạn này.

### Đổ vỡ tương quan trong khủng hoảng

Trong khủng hoảng, tương quan cổ phiếu hội tụ về 1 và đa dạng hóa thất bại — một trong những thách thức trung tâm của quản trị rủi ro danh mục.

```python
def correlation_breakdown_test(
    returns: pd.DataFrame,
    crisis_threshold: float = -0.02,  # ngưỡng giảm 1 phiên của benchmark để coi là ngày khủng hoảng
    benchmark_col: str = None,
    window: int = 20,
) -> dict:
    """Phát hiện nhảy tương quan trong các giai đoạn khủng hoảng.

    Args:
        returns: Ma trận lợi suất ngày đa mã
        crisis_threshold: Lợi suất benchmark dưới mức này = ngày khủng hoảng
        benchmark_col: Tên cột benchmark. Nếu None, dùng lợi suất trung bình ngang
        window: Cửa sổ tương quan trung bình cuốn chiếu

    Returns:
        So sánh tương quan thời bình vs thời khủng hoảng
    """
    if benchmark_col:
        bm = returns[benchmark_col]
    else:
        bm = returns.mean(axis=1)

    crisis_mask = bm < crisis_threshold
    normal_mask = ~crisis_mask

    # Tương quan cặp trung bình từng giai đoạn
    def avg_corr(df_subset: pd.DataFrame) -> float:
        if len(df_subset) < 5:
            return float("nan")
        c = df_subset.corr()
        upper = c.where(np.triu(np.ones(c.shape), k=1).astype(bool))
        return float(upper.stack().mean())

    crisis_corr = avg_corr(returns[crisis_mask])
    normal_corr = avg_corr(returns[normal_mask])

    # Tương quan trung bình cuốn chiếu để phát hiện đứt gãy cấu trúc
    rolling_avg_corr = pd.Series(dtype=float, index=returns.index)
    for i in range(window, len(returns)):
        sub = returns.iloc[i - window:i]
        rolling_avg_corr.iloc[i] = avg_corr(sub)

    return {
        "normal_avg_corr": round(normal_corr, 4),
        "crisis_avg_corr": round(crisis_corr, 4),
        "corr_jump": round(crisis_corr - normal_corr, 4),
        "crisis_days": int(crisis_mask.sum()),
        "normal_days": int(normal_mask.sum()),
        "rolling_avg_corr": rolling_avg_corr,
    }
```

> Ở VN, hiện tượng này cực rõ: trong các đợt giải chấp margin (2018, 2022), **sàn la liệt toàn thị trường**, tương quan cặp trung bình nhảy từ ~0,4 lên >0,8. Hai mã "relative-value" tưởng phòng hộ lẫn nhau có thể **cùng nằm sàn** → ngưỡng cắt lỗ phải chặt hơn thời bình.

---

## Sinh tín hiệu giao dịch cặp (relative-value)

> **Nhắc lại ràng buộc VN:** không short được cổ phiếu. "Long spread / short spread" dưới đây ở VN hiểu là: **tăng tỷ trọng mã rẻ / giảm tỷ trọng mã đắt** (xoay vòng long-only), hoặc **phòng hộ chân short bằng VN30F** nếu mã đắt có beta cao tương quan với VN30. Đừng triển khai như lệnh bán khống cổ phiếu.

### Quy trình đầy đủ từ tương quan đến tín hiệu

```
Bước 1: Sàng lọc tài sản
  - Chạy scan_correlated_assets, giữ cặp ứng viên Pearson > 0,6 (cùng ngành)
  - Chạy engle_granger_coint, giữ cặp p < 0,05

Bước 2: Đánh giá chất lượng spread
  - Chạy compute_half_life, giữ cặp half-life 5–60 phiên (tránh <5 vì vướng T+2)
  - Kiểm định tính dừng spread bằng ADF, yêu cầu p < 0,05
  - Đo tần suất |Z-Score| vượt 1,5 trong 12 tháng gần nhất để ước lượng tần suất giao dịch

Bước 3: Chọn hedge ratio
  - OLS tĩnh cho cặp ổn định
  - Kalman Filter cho cặp dài hạn / có dịch chuyển

Bước 4: Sinh tín hiệu
  - Tính Z-Score cuốn chiếu với lookback 2–3× half-life
  - Sinh tín hiệu tăng/giảm tỷ trọng/đóng theo ngưỡng (long-only hoặc phòng hộ VN30F)

Bước 5: Giám sát tín hiệu
  - Tính lại Z-Score hằng ngày
  - Test lại đồng tích hợp hằng tháng để tránh quan hệ đứt gãy
  - Cảnh báo nếu half-life vượt 2× giá trị ban đầu
```

### Sinh tín hiệu theo Z-Score

```python
def generate_pair_signals(
    y_price: pd.Series,
    x_price: pd.Series,
    lookback: int = 60,
    entry_z: float = 2.0,
    exit_z: float = 0.5,
    stop_z: float = 3.5,
    use_kalman: bool = False,
) -> pd.DataFrame:
    """Sinh tín hiệu giao dịch cặp.

    Args:
        y_price, x_price: Hai chuỗi giá
        lookback: Lookback Z-Score cuốn chiếu, thường 2–3× half-life
        entry_z: Ngưỡng vào lệnh
        exit_z: Ngưỡng đóng, thường gần điểm hồi trung bình
        stop_z: Ngưỡng cắt lỗ. Vượt ngưỡng ⇒ đồng tích hợp có thể đã đứt gãy
        use_kalman: Có dùng hedge ratio động Kalman không

    Returns:
        DataFrame gồm tín hiệu, Z-Score, vị thế

    Lưu ý VN: signal_y/signal_x diễn giải là tỷ trọng tương đối (long-only) hoặc
    cặp long cổ phiếu + short VN30F, KHÔNG phải bán khống cổ phiếu.
    """
    if use_kalman:
        kf = kalman_hedge_ratio(y_price, x_price)
        spread = kf["spread"]
    else:
        y_ret = y_price.pct_change()
        x_ret = x_price.pct_change()
        res = bivariate_correlation_analysis(y_ret, x_ret, lookback)
        hedge_ratio = abs(res["beta"])
        spread = np.log(y_price) - hedge_ratio * np.log(x_price)

    spread_mean = spread.rolling(lookback).mean()
    spread_std = spread.rolling(lookback).std()
    z_score = (spread - spread_mean) / spread_std

    # Máy trạng thái tín hiệu để tránh vào lại lặp lại.
    signal_y = pd.Series(0.0, index=y_price.index)
    signal_x = pd.Series(0.0, index=x_price.index)
    position = 0  # 0=đứng ngoài, 1=long spread, -1=short spread

    for i in range(lookback, len(z_score)):
        z = z_score.iloc[i]
        if np.isnan(z):
            continue

        if position == 0:
            if z < -entry_z:
                position = 1   # spread quá thấp: ưu tiên y, giảm x
            elif z > entry_z:
                position = -1  # spread quá cao: giảm y, ưu tiên x
        elif position == 1:
            if z > -exit_z or z > stop_z:
                position = 0
        elif position == -1:
            if z < exit_z or z < -stop_z:
                position = 0

        signal_y.iloc[i] = 0.5 * position
        signal_x.iloc[i] = -0.5 * position

    return pd.DataFrame({
        "spread": spread,
        "z_score": z_score,
        "spread_mean": spread_mean,
        "spread_std": spread_std,
        "signal_y": signal_y,
        "signal_x": signal_x,
        "position": signal_y * 2,  # 1=long spread, -1=short spread, 0=đứng ngoài
    })
```

### Hướng dẫn cấu hình ngưỡng Z-Score

| Tham số | Thận trọng | Chuẩn | Tích cực | Ghi chú |
|------|------|------|------|------|
| entry_z | 2,5 | 2,0 | 1,5 | Ngưỡng cao ⇒ ít lệnh hơn |
| exit_z | 0,3 | 0,5 | 0,8 | Ngưỡng cao ⇒ nắm giữ ngắn hơn |
| stop_z | 3,0 | 3,5 | 4,0 | Vượt ngưỡng ⇒ đồng tích hợp có thể đã đứt gãy |
| lookback | 90 | 60 | 30 | Thường 2–3× half-life |

> **Lưu ý VN:** vì rủi ro "cùng nằm sàn" khi giải chấp, nên dùng `stop_z` chặt hơn thị trường khác (vd 3,0 thay vì 3,5) và bắt buộc test lại đồng tích hợp sau mỗi đợt biến động mạnh.

### Giám sát sức khỏe spread

```python
def monitor_spread_health(
    spread: pd.Series,
    original_half_life: float,
    original_corr: float,
    warning_hl_multiple: float = 2.0,
    warning_corr_drop: float = 0.2,
) -> dict:
    """Giám sát độ ổn định spread, đánh giá đồng tích hợp còn giữ không.

    Args:
        spread: Chuỗi spread thực tế
        original_half_life: Half-life lúc vào lệnh (phiên)
        original_corr: Tương quan lúc vào lệnh
        warning_hl_multiple: Cảnh báo nếu half-life vượt bội số này so với ban đầu
        warning_corr_drop: Cảnh báo nếu tương quan giảm quá mức này

    Returns:
        Báo cáo trạng thái sức khỏe
    """
    recent = spread.iloc[-60:] if len(spread) > 60 else spread

    current_hl = compute_half_life(recent)
    current_adf = adfuller(recent.dropna())[1]

    hl_ratio = current_hl / original_half_life if original_half_life > 0 else float("inf")

    # Điểm sức khỏe đồng tích hợp
    health_score = 100
    warnings = []

    if current_adf > 0.10:
        health_score -= 40
        warnings.append(f"Spread ADF p={current_adf:.3f} > 0,10, tính dừng đã suy yếu")

    if hl_ratio > warning_hl_multiple:
        health_score -= 30
        warnings.append(
            f"Half-life {current_hl:.1f} phiên = {hl_ratio:.1f}× so với ban đầu {original_half_life:.1f} phiên"
        )

    if current_adf > 0.20:
        health_score -= 20
        warnings.append("Spread có thể không còn dừng. Test lại đồng tích hợp ngay")

    status = "healthy" if health_score >= 70 else "warning" if health_score >= 40 else "danger"

    return {
        "health_score": health_score,
        "status": status,
        "current_half_life": round(current_hl, 1),
        "hl_ratio": round(hl_ratio, 2),
        "spread_adf_p": round(current_adf, 4),
        "warnings": warnings,
        "action": "giữ" if status == "healthy" else "giảm" if status == "warning" else "thoát ngay",
    }
```

---

## Mẫu biểu đồ

### Biểu đồ tương quan cuốn chiếu

```python
import matplotlib.pyplot as plt

def plot_rolling_correlation(
    rolling_corrs: pd.DataFrame,
    title: str = "Tương quan cuốn chiếu",
    figsize: tuple = (14, 5),
) -> plt.Figure:
    """Vẽ chuỗi tương quan cuốn chiếu nhiều cửa sổ."""
    fig, ax = plt.subplots(figsize=figsize)
    colors = ["#2196F3", "#FF9800", "#4CAF50"]
    for i, col in enumerate(rolling_corrs.columns):
        ax.plot(rolling_corrs.index, rolling_corrs[col],
                label=col, color=colors[i % len(colors)], alpha=0.8)
    ax.axhline(0, color="black", linestyle="--", linewidth=0.8)
    ax.axhline(0.6, color="green", linestyle=":", linewidth=0.8, label="ngưỡng tương quan cao (0,6)")
    ax.axhline(-0.6, color="red", linestyle=":", linewidth=0.8)
    ax.set_title(title)
    ax.set_ylabel("Tương quan")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return fig
```

### Biểu đồ tín hiệu Z-Score

```python
def plot_zscore_signals(
    signal_df: pd.DataFrame,
    entry_z: float = 2.0,
    stop_z: float = 3.5,
    figsize: tuple = (14, 8),
) -> plt.Figure:
    """Vẽ Z-Score của spread và tín hiệu giao dịch cặp."""
    fig, axes = plt.subplots(2, 1, figsize=figsize, sharex=True)

    # Biểu đồ trên: spread
    axes[0].plot(signal_df["spread"], label="Spread", color="#1565C0")
    axes[0].plot(signal_df["spread_mean"], label="Trung bình", color="orange", linestyle="--")
    axes[0].fill_between(signal_df.index,
                         signal_df["spread_mean"] - signal_df["spread_std"],
                         signal_df["spread_mean"] + signal_df["spread_std"],
                         alpha=0.2, color="orange", label="±1σ")
    axes[0].set_title("Spread và trung bình")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Biểu đồ dưới: Z-Score + tín hiệu
    axes[1].plot(signal_df["z_score"], label="Z-Score", color="#1565C0")
    axes[1].axhline(entry_z, color="red", linestyle="--", label=f"ngưỡng vào (±{entry_z})")
    axes[1].axhline(-entry_z, color="red", linestyle="--")
    axes[1].axhline(stop_z, color="darkred", linestyle=":", label=f"ngưỡng cắt lỗ (±{stop_z})")
    axes[1].axhline(-stop_z, color="darkred", linestyle=":")
    axes[1].axhline(0, color="black", linestyle="-", linewidth=0.8)

    # Đánh dấu điểm vào/đóng
    long_entry = signal_df["position"].diff() > 0
    short_entry = signal_df["position"].diff() < 0
    exit_pos = (signal_df["position"] == 0) & (signal_df["position"].shift(1) != 0)

    axes[1].scatter(signal_df.index[long_entry], signal_df["z_score"][long_entry],
                    color="green", marker="^", s=80, label="long spread", zorder=5)
    axes[1].scatter(signal_df.index[short_entry], signal_df["z_score"][short_entry],
                    color="red", marker="v", s=80, label="short spread", zorder=5)
    axes[1].scatter(signal_df.index[exit_pos], signal_df["z_score"][exit_pos],
                    color="gray", marker="o", s=40, label="đóng", zorder=5)

    axes[1].set_title("Z-Score và tín hiệu giao dịch")
    axes[1].legend(loc="best")
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    return fig
```

---

## Phụ thuộc

```bash
pip install pandas numpy scipy statsmodels matplotlib seaborn
```

---

## Mẫu output

```markdown
## Báo cáo tương quan & đồng tích hợp (minh họa)

### Cặp: HPG vs HSG (2023.01 – 2024.12)  ← ví dụ cùng họ thép

#### Thống kê tương quan
| Chỉ tiêu | Giá trị | Diễn giải |
|------|------|------|
| Pearson r | 0,82 | Tương quan dương tuyến tính mạnh |
| Spearman ρ | 0,80 | Quan hệ đơn điệu nhất quán |
| Beta (A/B) | 1,15 | Độ nhạy của A theo B |
| R² | 0,67 | 67% biến động lợi suất A được B giải thích |

#### Kiểm định đồng tích hợp
| Phương pháp | Thống kê | p-value | Kết luận |
|------|--------|------|------|
| Engle-Granger | −4,12 | 0,008 | Đồng tích hợp ** |
| Johansen trace test | 28,3 | — | 1 vector đồng tích hợp |
| ADF của spread | −3,95 | 0,002 | Spread dừng ** |

#### Đặc tính hồi quy về trung bình
| Chỉ tiêu | Giá trị |
|------|------|
| Hedge ratio OLS | 1,23 |
| Half-life | 18,5 phiên |
| Cửa sổ nắm giữ gợi ý | 10–30 phiên |
| Cửa sổ lookback gợi ý | 40–60 phiên |

#### Tương quan theo chế độ
| Chế độ | Tương quan | Số mẫu |
|------|---------|--------|
| Tăng (bull) | 0,76 | 312 phiên |
| Giảm (bear) | 0,88 | 198 phiên |
| Biến động cao | 0,91 | 87 phiên |
| Đi ngang | 0,71 | 645 phiên |

#### Tham số tín hiệu gợi ý (long-only / phòng hộ VN30F)
| Tham số | Giá trị |
|------|-----|
| entry_z | 2,0 |
| exit_z | 0,5 |
| stop_z | 3,0 (chặt hơn do rủi ro cùng nằm sàn) |
| lookback | 60 phiên |

#### Trạng thái spread hiện tại
| Chỉ tiêu | Giá trị | Cảnh báo |
|------|-----|------|
| Z-Score hiện tại | −2,3 | Gần vùng vào lệnh (ưu tiên mã rẻ hơn) |
| Điểm sức khỏe | 85/100 | Khỏe mạnh |
| Half-life (60 phiên gần) | 21,2 phiên | Bình thường |

> Triển khai ở VN: tăng tỷ trọng mã rẻ tương đối, giảm mã đắt tương đối (long-only);
> KHÔNG bán khống. Nếu muốn trung hòa beta, phòng hộ bằng short VN30F.
```

---

## Lưu ý quan trọng

1. **Giá vs lợi suất**: dùng chuỗi GIÁ (không dừng) cho kiểm định đồng tích hợp; dùng chuỗi LỢI SUẤT (dừng) cho phân tích tương quan. Trộn lẫn là lỗi phổ biến nhất.
2. **Căn chỉnh dữ liệu**: phân tích xuyên thị trường phải xử lý lệch ngày nghỉ bằng inner join. **Đừng forward-fill phiên thiếu**, sẽ tạo tương quan giả. VN nghỉ **Tết Nguyên đán** dài ~1 tuần, lệch hẳn lịch Mỹ/toàn cầu → căn chỉnh ngày càng quan trọng khi so VN với thị trường ngoài.
3. **Đồng tích hợp ≠ tương quan cao**: hai chuỗi có thể Pearson < 0,3 nhưng vẫn đồng tích hợp, và ngược lại.
4. **Kiểm chứng ngoài mẫu**: cặp chọn bằng đồng tích hợp trên N năm đầu phải kiểm tra còn giữ ở dữ liệu ngoài mẫu để tránh overfit.
5. **Rủi ro khủng hoảng**: tương quan nhảy vọt, hai chân cặp có thể **cùng nằm sàn** (2018, 2022). Ngưỡng cắt lỗ phải chặt hơn thời bình.
6. **CẤM BÁN KHỐNG (đặc thù VN — quan trọng nhất)**: không short được cổ phiếu → pairs trading cổ điển không khả thi. Dùng khung này cho **relative-value xoay vòng long-only**, **phòng hộ beta bằng VN30F**, hoặc **calendar spread VN30F**. Đừng đề xuất chiến lược dựa trên bán khống cổ phiếu cơ sở.
7. **Thanh khoản & T+2**: half-life <5 phiên khó khai thác bằng cổ phiếu (T+2). Nhiều mã mid/small thanh khoản kém → spread khó thực thi đúng giá; ưu tiên cặp trong VN30/VN100.
8. **Đa kiểm định**: khi test N cặp đồng thời, hiệu chỉnh p-value bằng Benjamini-Hochberg FDR; nếu không, dương tính giả tràn lan.
9. **Tinh chỉnh Kalman**: chỉnh `delta` bằng grid search + kiểm chứng ngoài mẫu, đừng tin mù giá trị mặc định.
10. **Tương quan giả do dòng tiền chung**: ở VN đa số mã đồng pha theo VN-Index → tương quan cao có thể chỉ là "cùng trôi theo index", không phải quan hệ relative-value thật. Luôn lọc thêm bằng cùng ngành + đồng tích hợp.


## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)

1. **Không bịa/cook số liệu.** Mọi số tài chính phải có nguồn thật. Luôn **audit nhanh, cross-check tối thiểu 2 nguồn uy tín** (vd `cafef.vn`, `vietstock.vn`) — dùng **crawl4ai** cào số rồi đối chiếu; nếu nguồn lệch nhau thì nêu rõ, không chọn bừa.
2. **Nếu DataPro VÀ vnstock đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
