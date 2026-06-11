---
name: credit-analysis
description: "Phân tích thu nhập cố định & tín dụng tại VN — định giá trái phiếu/YTM, duration/convexity/DV01, đường cong lợi suất TPCP, mô hình rủi ro vỡ nợ (Altman Z, Merton/KMV), phân tích chênh lệch tín dụng, và đặc thù trái phiếu doanh nghiệp VN (khủng hoảng TPDN 2022, trái phiếu BĐS, NĐ 65/08). Nguồn: HNX/VBMA (TPCP, TPDN) + vnstock KBS (cơ bản tổ chức phát hành)."
category: analysis
---

# Phân tích thu nhập cố định & tín dụng (Việt Nam)

## Phạm vi áp dụng

Ưu tiên dùng skill này khi câu hỏi liên quan:
- Định giá trái phiếu, tính YTM, phân tích duration/convexity
- Xếp hạng tín nhiệm, ước lượng xác suất vỡ nợ (PD)
- Phân tích chênh lệch tín dụng (credit spread) & chiến lược
- Quản trị rủi ro lãi suất (DV01, key-rate duration, miễn dịch)
- Cấu trúc thị trường trái phiếu Việt Nam (TPCP & TPDN)

## ⚠️ Đặc thù tín dụng Việt Nam (đọc TRƯỚC)

1. **Văn hóa xếp hạng tín nhiệm còn sơ khai**: phần lớn trái phiếu DN Việt Nam (đặc biệt giai đoạn bùng nổ 2019–2021) **không xếp hạng**. CRA nội địa mới nổi: **FiinRatings, Saigon Ratings (S&I)**. Đừng giả định có rating đáng tin như Mỹ/TQ; tự ước lượng PD bằng mô hình (Altman/Merton) + đọc BCTC.
2. **Khủng hoảng TPDN 2022 là bối cảnh nền**: sự kiện **Tân Hoàng Minh** (4/2022) và **Vạn Thịnh Phát/SCB** (10/2022) làm niềm tin sụp đổ, thị trường đóng băng, hàng loạt tổ chức phát hành (nhất là **BĐS**) **không đảo được nợ → vỡ nợ/giãn hoãn**. Rủi ro tín dụng VN là RẤT THỰC, không chỉ lý thuyết.
3. **Phát hành RIÊNG LẺ áp đảo**: chủ yếu bán cho **NĐT chuyên nghiệp** (NĐ 65/2022 siết định nghĩa); **NĐ 08/2023** cho phép giãn nợ tới 2 năm, trả nợ bằng tài sản → "cứu" thanh khoản tạm thời.
4. **"Trái phiếu 3 không"**: không xếp hạng – không tài sản đảm bảo – không bảo lãnh. Rất phổ biến thời bùng nổ → rủi ro cao.
5. **Không có "城投债" (LGFV) kiểu TQ**: rủi ro tín dụng đặc trưng VN nằm ở **trái phiếu doanh nghiệp BĐS** (xem mục VI).

---

## I. Khung phân tích tín dụng

### 1.1 Xếp hạng: chủ thể vs lô trái phiếu
| Loại | Định nghĩa |
|------|------|
| Xếp hạng chủ thể (Issuer) | Năng lực trả nợ tổng thể của tổ chức phát hành |
| Xếp hạng lô (Issue) | Chất lượng tín dụng một trái phiếu cụ thể (tính TSĐB, thứ tự ưu tiên, điều khoản) |

Thang quốc tế tham chiếu (S&P/Moody's): AAA…BBB- là **ngưỡng đầu tư**; BB+ trở xuống là **đầu cơ/lợi suất cao**; D là vỡ nợ. **VN**: hầu hết TPDN nếu quy đổi sẽ rơi vùng đầu cơ; rating nội địa (nếu có) cần đọc kèm triển vọng.

### 1.2 Mô hình Altman Z-Score (dự báo kiệt quệ tài chính)
```
Z = 1.2·X1 + 1.4·X2 + 3.3·X3 + 0.6·X4 + 1.0·X5
  X1 = Vốn lưu động / Tổng tài sản     (thanh khoản)
  X2 = LN giữ lại / Tổng tài sản        (tích lũy LN)
  X3 = EBIT / Tổng tài sản              (khả năng sinh lời)
  X4 = Vốn hóa thị trường / Tổng nợ     (đòn bẩy)
  X5 = Doanh thu / Tổng tài sản         (hiệu suất tài sản)

Z > 2,99 An toàn | 1,81 < Z < 2,99 Vùng xám | Z < 1,81 Nguy hiểm
Biến thể: Z' (DN chưa niêm yết, X4 dùng giá trị sổ sách); Z'' (phi sản xuất, bỏ X5).
Hạn chế: không dùng cho DN tài chính; cần hiệu chỉnh tham số cho VN.
```

### 1.3 Mô hình cấu trúc Merton & KMV (EDF)
Coi vốn chủ sở hữu là **quyền chọn mua** trên tài sản DN (giá thực hiện = mệnh giá nợ):
```
E = V·N(d1) − D·e^(−rT)·N(d2)
d1 = [ln(V/D) + (r + σ_V²/2)T] / (σ_V·√T) ;  d2 = d1 − σ_V·√T
PD (trung tính rủi ro) = N(−d2)
Khoảng cách tới vỡ nợ DD = [ln(V/D) + (μ − σ_V²/2)T] / (σ_V·√T)
```
KMV (thương mại hóa Merton): điểm kích hoạt vỡ nợ `DP = nợ ngắn hạn + 0,5×nợ dài hạn`; ánh xạ DD → EDF qua dữ liệu thực nghiệm. **Ở VN** thiếu cơ sở dữ liệu vỡ nợ lịch sử → coi PD/EDF là tương đối, không tuyệt đối.

---

## II. Sản phẩm thu nhập cố định

### 2.1 Đường cong lợi suất Trái phiếu Chính phủ (TPCP)
- **Đường chuẩn VN**: TPCP do **Kho bạc Nhà nước** phát hành, **đấu thầu qua HNX**; kỳ hạn chuẩn 5/7/10/15/20/30 năm, **TPCP 10 năm là lãi suất tham chiếu cốt lõi**. Trái phiếu Chính phủ bảo lãnh (VDB, VBSP) và trái phiếu chính quyền địa phương (nhỏ).
- Người mua chính: ngân hàng thương mại, bảo hiểm, BHXH.
```
Chênh lệch kỳ hạn (term spread):
  10Y − 2Y: dự báo chu kỳ kinh tế (đảo ngược ⇒ cảnh báo suy thoái)
Hình dạng: dốc lên (kỳ vọng mở rộng) | phẳng (chuyển pha) | đảo ngược (cảnh báo)
```

### 2.2 Chỉ tiêu trái phiếu cốt lõi
```
YTM: lợi suất làm hiện giá dòng tiền = giá thị trường:  P = Σ C/(1+y)^t + F/(1+y)^n
Current yield = coupon năm / giá
Duration điều chỉnh (MD) = Macaulay / (1 + y/m);  ΔP/P ≈ −MD·Δy + 0,5·CX·(Δy)²
DV01 = MD × P × 0,0001  (biến động giá khi lãi suất đổi 1 điểm cơ bản)
Chênh lệch tín dụng = YTM trái phiếu − YTM TPCP cùng kỳ hạn
```

### 2.3 ABS/MBS
Chứng khoán hóa ở VN còn **rất sơ khai** (gần như chưa có thị trường ABS/MBS retail). Giữ khung lý thuyết (phân lớp Senior/Mezzanine/Junior, CPR/SMM, tăng tín nhiệm, vượt lãi) để tham chiếu khi gặp cấu trúc tương tự, nhưng **chưa áp dụng đại trà tại VN**.

---

## III. Quản trị rủi ro lãi suất

```
Macaulay duration = Σ t·CF_t/(1+y)^t / P            (đơn vị: năm)
Modified duration = Macaulay / (1 + y/m)            (độ nhạy giá theo lãi suất)
Effective duration = (P_down − P_up) / (2·P0·Δy)    (cho trái phiếu có quyền chọn)
Convexity = Σ t(t+1)·CF_t/(1+y)^(t+2) / P           (hiệu ứng bậc hai; lồi dương = tốt)
Key-rate duration: độ nhạy theo từng điểm kỳ hạn (1Y…30Y); Σ KRD ≈ MD
```
**Chiến lược miễn dịch (immunization)**: khớp duration tài sản = duration nghĩa vụ; tái cân bằng định kỳ và khi lãi suất biến động mạnh (>50bp). Bảo hiểm/quỹ TPCP VN dùng khớp duration để phòng rủi ro lãi suất.

---

## IV. Phân tích chênh lệch tín dụng

```
Credit spread = phần bù rủi ro vỡ nợ + phần bù thanh khoản (+ thuế nếu có)
Chuẩn so sánh ở VN: TPDN vs TPCP cùng kỳ hạn (hoặc vs TPDN AAA nội địa nếu có rating).

Động lực mở rộng/thu hẹp:
  Vĩ mô: tăng trưởng GDP/PMI, chính sách tiền tệ (NHNN), sự kiện tín dụng (làn sóng vỡ nợ 2022)
  Ngành: chính sách BĐS, tín dụng ngân hàng, môi trường tái cấp vốn
  Cá biệt: hạ rating, BCTC xấu đi, áp lực đáo hạn → spread bật tăng
"Chạy về chất lượng" (flight to quality): TPCP lợi suất giảm + spread TPDN mở rộng — đòn kép với trái phiếu lợi suất cao.
```
Chiến lược: thu hẹp spread (mua TPDN bị định giá thấp + phòng hộ lãi suất bằng HĐTL TPCP/VN30F) khi chu kỳ phục hồi; cẩn trọng giai đoạn đáo hạn dồn dập + chính sách siết.

---

## V. Mã Python (universal — docstring tiếng Việt)

```python
import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm
from scipy.optimize import fsolve


def bond_price(face, coupon_rate, ytm, n_periods, freq=1):
    """Định giá trái phiếu coupon (chiết khấu dòng tiền). face mệnh giá; coupon_rate & ytm
    là lãi suất năm (thập phân); n_periods số kỳ trả lãi còn lại; freq số lần trả/năm."""
    c = face * coupon_rate / freq
    y = ytm / freq
    if y == 0:
        return c * n_periods + face
    return c * (1 - (1 + y) ** -n_periods) / y + face / (1 + y) ** n_periods


def ytm_solve(price, face, coupon_rate, n_periods, freq=1):
    """Giải YTM năm hóa từ giá thị trường (số nghiệm Brent)."""
    return brentq(lambda y: bond_price(face, coupon_rate, y, n_periods, freq) - price, -0.5, 10.0)


def modified_duration(face, coupon_rate, ytm, n_periods, freq=1):
    """Duration điều chỉnh (độ nhạy giá theo lãi suất)."""
    c = face * coupon_rate / freq
    y = ytm / freq
    price = bond_price(face, coupon_rate, ytm, n_periods, freq)
    mac = (sum(t * c / (1 + y) ** t for t in range(1, n_periods))
           + n_periods * (c + face) / (1 + y) ** n_periods) / price / freq
    return mac / (1 + ytm / freq)


def convexity(face, coupon_rate, ytm, n_periods, freq=1):
    """Độ lồi (convexity), hiệu ứng bậc hai của giá theo lãi suất."""
    c = face * coupon_rate / freq
    y = ytm / freq
    price = bond_price(face, coupon_rate, ytm, n_periods, freq)
    s = (sum(t * (t + 1) * c / (1 + y) ** (t + 2) for t in range(1, n_periods))
         + n_periods * (n_periods + 1) * (c + face) / (1 + y) ** (n_periods + 2))
    return s / price / freq ** 2


def dv01(face, coupon_rate, ytm, n_periods, freq=1, par_amount=1_000_000):
    """DV01: thay đổi giá (đồng) khi lãi suất biến động 1bp, theo mệnh giá nắm giữ."""
    md = modified_duration(face, coupon_rate, ytm, n_periods, freq)
    return md * (bond_price(face, coupon_rate, ytm, n_periods, freq) / 100) * 0.0001 * par_amount


def altman_z(working_capital, retained_earnings, ebit, market_cap,
             total_debt, revenue, total_assets, model="original"):
    """Altman Z-Score đánh giá rủi ro vỡ nợ. model: original | prime | double_prime."""
    x1 = working_capital / total_assets
    x2 = retained_earnings / total_assets
    x3 = ebit / total_assets
    x4 = market_cap / total_debt
    x5 = revenue / total_assets
    if model == "original":
        z, safe, distress = 1.2*x1 + 1.4*x2 + 3.3*x3 + 0.6*x4 + 1.0*x5, 2.99, 1.81
    elif model == "prime":
        z, safe, distress = 0.717*x1 + 0.847*x2 + 3.107*x3 + 0.420*x4 + 0.998*x5, 2.90, 1.23
    elif model == "double_prime":
        z, safe, distress = 6.56*x1 + 3.26*x2 + 6.72*x3 + 1.05*x4, 2.60, 1.10
    else:
        raise ValueError(f"model không hợp lệ: {model}")
    level = "An toàn" if z > safe else "Nguy hiểm" if z < distress else "Vùng xám"
    return {"z_score": round(z, 4), "muc_rui_ro": level}


def merton_pd(equity_value, equity_vol, debt_face, risk_free, T):
    """Merton: ước lượng giá trị tài sản, khoảng cách tới vỡ nợ (DD) và PD trung tính rủi ro.
    equity_value & debt_face cùng đơn vị (vd tỷ đồng); equity_vol & risk_free thập phân; T năm."""
    def eqs(p):
        V, sV = p
        d1 = (np.log(V/debt_face) + (risk_free + 0.5*sV**2)*T) / (sV*np.sqrt(T))
        d2 = d1 - sV*np.sqrt(T)
        return [V*norm.cdf(d1) - debt_face*np.exp(-risk_free*T)*norm.cdf(d2) - equity_value,
                norm.cdf(d1)*sV*V - equity_vol*equity_value]
    V0 = equity_value + debt_face
    V, sV = fsolve(eqs, [V0, equity_vol*equity_value/V0])
    d2 = (np.log(V/debt_face) + (risk_free - 0.5*sV**2)*T) / (sV*np.sqrt(T))
    return {"gia_tri_tai_san": round(V, 2), "DD": round(d2, 3), "PD_RN": f"{norm.cdf(-d2)*100:.2f}%"}
```
Đường cong lợi suất (Nelson-Siegel/Svensson) khớp từ điểm TPCP HNX: dùng `scipy.optimize.minimize` tối thiểu hóa bình phương sai số giữa lợi suất mô hình và lợi suất quan sát theo kỳ hạn [0.5,1,2,3,5,7,10,15,30]; tham số `beta0` (mức), `beta1` (độ dốc), `beta2` (độ cong), `lambda` (tốc độ suy giảm).

---

## VI. Đặc thù thị trường trái phiếu Việt Nam

### 6.1 Cấu trúc thị trường
| Phân khúc | Tổ chức phát hành | Quản lý/đăng ký | Rủi ro tín dụng |
|------|------|------|------|
| TPCP | Kho bạc Nhà nước | Đấu thầu HNX | Không (tín nhiệm quốc gia) |
| TP Chính phủ bảo lãnh | VDB, VBSP | KBNN/Bộ Tài chính | Rất thấp (gần chủ quyền) |
| TP chính quyền địa phương | UBND tỉnh/TP (HCM, HN) | Bộ Tài chính | Thấp |
| TPDN chào bán **ra công chúng** | DN niêm yết/đại chúng | UBCKNN duyệt (có thể cần rating) | Trung–cao |
| TPDN **riêng lẻ** | DN (NĐT chuyên nghiệp) | NĐ 65/2022, 08/2023 | Cao (chiếm phần lớn thị trường) |
| TP ngân hàng (vốn cấp 2) | NHTM | NHNN | Thấp–trung (tăng CAR) |

- **Thứ cấp**: từ 7/2023 có **hệ thống giao dịch TPDN riêng lẻ tập trung trên HNX** → minh bạch & thanh khoản cải thiện. Trước đó gần như OTC, mờ thông tin.
- Dữ liệu thị trường: **VBMA** (Hiệp hội Thị trường Trái phiếu VN), HNX, FiinPro/FiinRatings.

### 6.2 Phân tích tín dụng TRÁI PHIẾU DOANH NGHIỆP BĐS (rủi ro đặc trưng VN — thay cho 城投债)

BĐS là nhóm phát hành TPDN lớn nhất và là tâm điểm khủng hoảng 2022.
```
Khung 4 trục đánh giá tổ chức phát hành BĐS:
  1. Dòng tiền & đáo hạn:  tiền & tương đương / nợ ngắn hạn; lịch đáo hạn trái phiếu dồn dập?
  2. Chất lượng dự án:     pháp lý dự án (sổ đỏ/giấy phép), tỷ lệ hấp thụ, hàng tồn kho
  3. Đòn bẩy & bảo đảm:    nợ vay/VCSH; TSĐB là DỰ ÁN/CỔ PHẦN tương lai (khó định giá, khó phát mãi)
  4. Quản trị & minh bạch:  bên liên quan chằng chịt, "đảo nợ", chất lượng kiểm toán

Cờ đỏ (red lines):
  - Tiền/nợ ngắn hạn < 0,3  → căng thanh khoản
  - EBITDA/lãi vay (ICR) < 1 → trả lãi bằng vốn vay mới
  - Phát hành liên tục chỉ để "đảo nợ" (vay mới trả cũ) → vòng xoáy Ponzi
  - TSĐB là cổ phiếu chính tổ chức phát hành / dự án chưa đủ pháp lý
  - "3 không" (không rating – không TSĐB – không bảo lãnh)
```

### 6.3 Phân tích vỡ nợ & tỷ lệ thu hồi
```
Loại vỡ nợ ở VN:
  - Thanh khoản: tài sản còn nhưng dòng tiền đứt (đa số DN BĐS 2022–2023)
  - Kỹ thuật: kích hoạt điều khoản (chậm trả lãi/gốc) → giãn hoãn theo NĐ 08/2023
  - Gian lận: thao túng, dùng pháp nhân "ma" huy động (Vạn Thịnh Phát/SCB)

Tín hiệu cảnh báo sớm:
  Tài chính: phải thu/tổng tài sản tăng bất thường; tiền bị hạn chế cao; bên liên quan lớn
  Thị trường: giá cổ phiếu tổ chức phát hành lao dốc; spread bật mạnh; chậm trả lãi trái phiếu
  Khác: chậm công bố BCTC; kiểm toán ngoại trừ/từ chối; lãnh đạo bị điều tra

Tỷ lệ thu hồi (tham khảo VN, bất định cao):
  TSĐB = dự án/đất pháp lý tốt → có thể thu hồi qua hoán đổi tài sản (NĐ 08) nhưng kéo dài
  "3 không" / dự án vướng pháp lý → thu hồi thấp, thời gian rất dài
```

---

## VII. Liên kết skill khác

| Skill | Bổ trợ |
|------|------|
| `convertible-bond` | Phần quyền chọn chuyển đổi; skill này lo định giá trái phiếu thuần & rủi ro tín dụng |
| `macro-analysis` | Môi trường lãi suất NHNN & chu kỳ tín dụng làm đầu vào |
| `financial-statement` | Chia sẻ khung đọc BCTC (đòn bẩy, ICR, dòng tiền) — qua vnstock KBS |
| `risk-analysis` | Rủi ro tín dụng danh mục (VaR/CVaR) |

## VIII. Nguồn dữ liệu (VN)

| Việc cần | Nguồn |
|------|------|
| Đường cong lợi suất TPCP, kết quả đấu thầu | **HNX**, **VBMA** (nguồn ngoài) |
| Thông tin/giá TPDN (thứ cấp) | **Hệ thống TPDN riêng lẻ HNX** (từ 2023), FiinPro/FiinRatings, VBMA |
| Cơ bản tổ chức phát hành (đòn bẩy, ICR, dòng tiền, Altman) | **vnstock KBS** (`income`/`balancesheet`/`cashflow`) |
| Vốn hóa & biến động vốn chủ (Merton) | **DataPro** (giá `.VN`) + vnstock |
| Xếp hạng tín nhiệm (nếu có) | FiinRatings, Saigon Ratings/S&I (nguồn ngoài) |
| Lãi suất điều hành NHNN, vĩ mô | skill `macro-analysis` |

Khi thiếu dữ liệu trực tiếp: nêu hạn chế, ước lượng PD bằng mô hình + BCTC, KHÔNG bịa rating/số liệu.

## IX. Tra cứu nhanh

```
YTM xấp xỉ:  [C + (F−P)/n] / [(F+P)/2]
ΔP/P ≈ −MD·Δy + 0,5·CX·(Δy)²
DV01 = MD × P × 0,0001 × mệnh giá nắm giữ
Credit spread = YTM trái phiếu − YTM TPCP cùng kỳ hạn
Z: >2,99 An toàn | 1,81–2,99 Xám | <1,81 Nguy hiểm
DD→PD: DD>4 ⇒ rất thấp; DD 2–4 ⇒ thấp–trung; DD<1 ⇒ rất cao
```

## Phụ thuộc

```bash
pip install pandas numpy scipy vnstock
```


## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)

1. **Không bịa/cook số liệu.** Mọi số tài chính phải có nguồn thật. Luôn **audit nhanh, cross-check tối thiểu 2 nguồn uy tín** (vd `cafef.vn`, `vietstock.vn`) — dùng **crawl4ai** cào số rồi đối chiếu; nếu nguồn lệch nhau thì nêu rõ, không chọn bừa.
2. **Nếu DataPro VÀ vnstock đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
