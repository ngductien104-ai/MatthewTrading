---
name: convertible-bond
description: "Phân tích trái phiếu chuyển đổi (TPCĐ) tại VN — định giá 3 phần (giá trị trái phiếu thuần + giá trị chuyển đổi + quyền chọn), điều khoản chuyển đổi/chống pha loãng/mua lại, và tác động PHA LOÃNG lên cổ phiếu cơ sở. Lưu ý: VN không có thị trường TPCĐ niêm yết thanh khoản kiểu retail — chủ yếu phát hành riêng lẻ/offshore."
category: asset-class
---

# Phân tích trái phiếu chuyển đổi (Việt Nam)

## ⚠️ Thực tế thị trường VN (đọc TRƯỚC)

TPCĐ ở VN **khác hẳn** thị trường 可转债 Trung Quốc hay convertibles Mỹ:

1. **Không có thị trường TPCĐ niêm yết thanh khoản cho NĐT lẻ.** Phần lớn TPCĐ Việt Nam là **phát hành riêng lẻ** cho đối tác chiến lược / tổ chức / NĐT chuyên nghiệp, hoặc **phát hành offshore** (niêm yết Singapore — vd các thương vụ quốc tế của VIC, MSN, NVL, HPG...).
2. **KHÔNG áp dụng** các "trò chơi" retail của A股: chiến lược **song thấp (双低)**, xoay vòng TPCĐ T+0, đầu cơ điều khoản hạ giá chuyển đổi/mua lại bắt buộc/bán lại. Đừng bê khung đó vào VN.
3. **Trọng tâm phân tích ở VN** vì vậy là: (a) **định giá một lô TPCĐ cụ thể** từ bản cáo bạch/điều khoản, và (b) đánh giá **tác động pha loãng & tín hiệu** lên **cổ phiếu cơ sở** — phần này hữu ích cho analyst cổ phiếu hơn là trader trái phiếu.
4. Pháp lý phát hành: **Luật CK 2019, NĐ 155/2020** (chào bán ra công chúng/riêng lẻ), **NĐ 65/2022 & NĐ 08/2023** (trái phiếu DN riêng lẻ — NĐT chuyên nghiệp, xếp hạng tín nhiệm trong một số trường hợp). Xem thêm skill `credit-analysis`.

## Khái niệm cốt lõi

TPCĐ = trái phiếu mang đặc tính lai: **"sàn trái phiếu" (bảo vệ) + quyền chọn mua cổ phiếu**.

| Yếu tố | Giải thích |
|------|------|
| Mệnh giá (F) | TPCĐ trong nước thường 100.000đ (đại chúng) / 100 triệu đ (riêng lẻ, NĐT chuyên nghiệp); offshore tính theo USD |
| Lãi suất danh nghĩa | Thường thấp (có thể tăng dần - step-up); thấp hơn trái phiếu thường vì có quyền chọn |
| Giá chuyển đổi | Giá quy đổi sang cổ phiếu (kèm điều khoản **chống pha loãng** khi chia tách/thưởng/phát hành thêm) |
| Tỷ lệ chuyển đổi | = Mệnh giá / Giá chuyển đổi |
| Kỳ hạn | Thường 2–5 năm |
| Điều khoản mua lại (call) / bán lại (put) | Quyền của tổ chức phát hành / trái chủ theo điều kiện giá hoặc thời điểm |

```
Giá trị chuyển đổi = (Mệnh giá / Giá chuyển đổi) × Giá cổ phiếu cơ sở
                   = Tỷ lệ chuyển đổi × Giá cổ phiếu

Phần bù chuyển đổi (%) = (Giá TPCĐ − Giá trị chuyển đổi) / Giá trị chuyển đổi
Phần bù trái phiếu (%) = (Giá TPCĐ − Giá trị trái phiếu thuần) / Giá trị trái phiếu thuần
```

## Định giá 3 phần (universal — áp dụng được mọi TPCĐ)

### 1. Giá trị trái phiếu thuần (bond floor)

```python
def bond_floor(coupon_rates: list, face: float = 100,
               redemption: float = 100, ytm_straight: float = 0.10) -> float:
    """Giá trị trái phiếu thuần = chiết khấu dòng tiền coupon + giá mua lại đáo hạn.

    Args:
        coupon_rates: lãi suất từng năm còn lại (vd [0.05, 0.06, 0.07])
        face: mệnh giá
        redemption: giá hoàn trả khi đáo hạn (thường = mệnh giá, có thể + phụ trội)
        ytm_straight: lợi suất chiết khấu = lợi suất trái phiếu thường CÙNG rủi ro/kỳ hạn
                      (ở VN nhóm BĐS/đầu cơ có thể 12–15%+ → bond floor thấp)
    Returns:
        Giá trị trái phiếu thuần
    """
    pv = sum(c * face / (1 + ytm_straight) ** i for i, c in enumerate(coupon_rates, 1))
    pv += redemption / (1 + ytm_straight) ** len(coupon_rates)
    return pv
```
- Bond floor cao → bảo vệ tốt, ít dư địa giảm. **Đặc thù VN**: tổ chức phát hành (nhất là BĐS) rủi ro tín dụng cao → lợi suất chiết khấu lớn → **sàn trái phiếu thấp & kém tin cậy** (rủi ro vỡ nợ thực sự, không chỉ lý thuyết). Bond floor chỉ có ý nghĩa nếu trái chủ thực sự đòi được nợ.

### 2. Giá trị chuyển đổi (phần cổ phiếu)
```
Giá trị chuyển đổi = Tỷ lệ chuyển đổi × Giá cổ phiếu cơ sở (DataPro, mã .VN)
Yếu tố tác động: giá cổ phiếu (+), giá chuyển đổi (−, có điều chỉnh chống pha loãng).
```

### 3. Giá trị quyền chọn
```
Giá trị quyền chọn = Giá TPCĐ − max(Bond floor, Giá trị chuyển đổi)
Cao → thị trường định giá tiềm năng tăng của cổ phiếu / biến động lớn.
```

### Ma trận phân loại
| Giá trị chuyển đổi | Bond floor | Loại | Hàm ý |
|------|------|------|------|
| Cao (>> mệnh giá) | — | Thiên cổ phiếu | Đi theo cổ phiếu cơ sở; coi như nắm cổ phiếu có điều kiện |
| ≈ mệnh giá | — | Cân bằng | Lai cân bằng; nhạy cả hai phía |
| Thấp | Cao & ĐÁNG TIN | Thiên trái phiếu | Giữ ăn lãi, chờ cổ phiếu hồi |
| Thấp | Thấp / không tin được | **Khốn khó** | Rủi ro tín dụng/vỡ nợ — vùng nguy hiểm nhất ở VN |

## Phân tích tác động lên CỔ PHIẾU CƠ SỞ (phần hữu ích nhất cho VN)

```
Pha loãng tiềm năng khi chuyển đổi:
  Số CP phát hành thêm = Tổng mệnh giá TPCĐ / Giá chuyển đổi
  EPS pha loãng ≈ LNST / (CP hiện hữu + CP phát hành thêm khi chuyển đổi)

Tín hiệu từ việc phát hành TPCĐ:
  + Phát hành cho đối tác CHIẾN LƯỢC uy tín (ngoại/định chế lớn), giá chuyển đổi hợp lý,
    mục đích M&A/mở rộng dự án tốt → xác nhận giá trị, vốn rẻ.
  − Phát hành cho bên liên quan/mờ ám, giá chuyển đổi thấp, mục đích "đảo nợ"/bổ sung
    vốn lưu động chung chung → pha loãng + cờ đỏ thanh khoản tổ chức phát hành.

Điều khoản cần soi trong bản cáo bạch:
  - Giá & cơ chế điều chỉnh chống pha loãng (anti-dilution)
  - Lock-up của bên nhận chuyển đổi
  - Call/put, lãi suất step-up, tài sản đảm bảo & bảo lãnh
```

## Mẫu output

```markdown
## Phân tích TPCĐ: [Tổ chức phát hành / mã .VN cơ sở] (minh họa)

### Điều khoản
| Mục | Giá trị |
|------|------|
| Mệnh giá / kỳ hạn | ... / ... năm |
| Lãi suất (step-up?) | ... |
| Giá chuyển đổi | ... (vs thị giá ...) |
| Tỷ lệ chuyển đổi | ... |
| Call/Put / TSĐB / bảo lãnh | ... |

### Định giá 3 phần
- Bond floor: ... (chiết khấu theo lợi suất rủi ro tổ chức phát hành ...% — ĐỘ TIN?)
- Giá trị chuyển đổi: ...
- Giá trị quyền chọn: ...
- Phân loại: thiên cổ phiếu / cân bằng / thiên trái phiếu / khốn khó

### Tác động cổ phiếu cơ sở
- Pha loãng tiềm năng: + ...% số CP → EPS pha loãng ...
- Tín hiệu phát hành: [xác nhận giá trị / pha loãng-đảo nợ]

### Nhận định
Trọng tâm rủi ro ở VN là TÍN DỤNG tổ chức phát hành, không phải "trò" điều khoản. ...

Lưu ý: Đây là nghiên cứu, không phải khuyến nghị đầu tư.
```

## Lưu ý quan trọng

1. **Rủi ro tín dụng là trọng tâm ở VN**, không phải đầu cơ điều khoản. Sau khủng hoảng TPDN 2022 (Tân Hoàng Minh, Vạn Thịnh Phát), nhiều lô trái phiếu DN (nhất là BĐS) **vỡ nợ/giãn hoãn** — "sàn trái phiếu" có thể không đòi được. Phân tích tín dụng tổ chức phát hành TRƯỚC (xem `credit-analysis`).
2. **Thanh khoản gần như không có** với TPCĐ riêng lẻ — không thể vào/ra như cổ phiếu; định giá mang tính nắm-đến-đáo-hạn/sự kiện chuyển đổi.
3. **Điều khoản từng lô rất khác nhau** (chống pha loãng, call/put, TSĐB) → phải đọc bản cáo bạch từng lô, không suy diễn chung.
4. **Đừng áp chiến lược song thấp/xoay vòng A股** — không tồn tại thị trường tương ứng ở VN.
5. **Góc nhìn cổ phiếu**: với analyst cổ phiếu, giá trị lớn nhất của skill này là lượng hóa **pha loãng** và đọc **tín hiệu** từ đợt phát hành TPCĐ của DN.

## Nguồn dữ liệu (VN)

| Việc cần | Nguồn |
|------|------|
| Điều khoản TPCĐ (giá/tỷ lệ chuyển đổi, lãi suất, call/put, TSĐB) | Bản cáo bạch / nghị quyết ĐHĐCĐ / công bố thông tin tổ chức phát hành (nguồn ngoài) |
| Giá cổ phiếu cơ sở (tính giá trị chuyển đổi) | **DataPro** (`source="datapro"`, mã `.VN`) |
| Cơ bản & sức khỏe tín dụng tổ chức phát hành | **vnstock KBS** (`income`/`balancesheet`/`cashflow`, đòn bẩy, ICR) + skill `credit-analysis` |
| Lịch sử tăng vốn / pha loãng | **vnstock** `Company.capital_history()` |
| Thông tin trái phiếu DN (thứ cấp) | Hệ thống giao dịch TPDN riêng lẻ tập trung HNX (từ 2023), FiinPro (nguồn ngoài) |

## Phụ thuộc

```bash
pip install pandas numpy vnstock
```
