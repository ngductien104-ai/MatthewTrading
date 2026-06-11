---
name: etf-analysis
description: "Phân tích ETF niêm yết tại VN (HOSE) — phân loại theo chỉ số bám, tracking error, chiết khấu/phụ trội so iNAV, thanh khoản, phí, cơ chế tạo/mua lại in-kind, chiến lược core–satellite, dòng tiền ETF ngoại làm chỉ báo. Nguồn: DataPro (giá ETF/chỉ số) + iNAV/holdings từ công ty QLQ."
category: asset-class
---

# Phân tích ETF (Việt Nam)

## Mục đích

ETF niêm yết là công cụ cốt lõi cho đầu tư thụ động & phân bổ tài sản tại VN. Skill này phủ phân tích sản phẩm ETF nội, phương pháp chọn ETF, ứng dụng chiến lược và đặc thù thị trường VN.

> Để sàng lọc quỹ mở chủ động, đánh giá nhà điều hành, xây danh mục FOF → xem skill `fund-analysis`. Skill này tập trung vào **ETF niêm yết** (đi sâu tracking error / chiết khấu–phụ trội / thanh khoản / cơ chế tạo lập).

## ⚠️ Đặc thù ETF Việt Nam (đọc TRƯỚC)

1. **Giao dịch trên HOSE như cổ phiếu**: T+2, biên độ ±7%, có giá thị trường khớp lệnh và có **iNAV** (NAV ước tính trong phiên). Khác hẳn quỹ mở (giao dịch tại NAV phiên định kỳ).
2. **Cơ chế tạo/mua lại in-kind qua AP**: chỉ **thành viên lập quỹ (AP — thường là CTCK)** mới tạo/mua lại ETF bằng cách hoán đổi **rổ cổ phiếu cơ cấu (PCF)** theo **lô đơn vị (creation unit)** rất lớn (hàng trăm nghìn–1 triệu CCQ). **NĐT cá nhân chỉ giao dịch thứ cấp trên sàn**, không tự arbitrage được.
3. **ETF VNDIAMOND = cửa tiếp cận cổ phiếu hết room ngoại**: rổ VNDIAMOND gồm cổ phiếu kịch/gần kịch trần sở hữu nước ngoài (FPT, MWG, ngân hàng...). NĐT nước ngoài mua **FUEVFVND/FUEMAVND** để gián tiếp nắm cổ phiếu đã hết room → cầu ngoại đẩy ETF thường **phụ trội (premium)**.
4. **KHÔNG có ở VN** (đừng áp khung nước ngoài): QDII, LOF, quỹ phân cấp, **ETF đòn bẩy/nghịch đảo**, ETF vàng/hàng hóa. Bỏ toàn bộ phần "衰减/leverage decay".
5. **ETF NGOẠI đầu tư vào VN** là chỉ báo dòng tiền nước ngoài: **Fubon FTSE Vietnam (Đài Loan)**, **VanEck Vietnam (VNM)**, **Xtrackers FTSE Vietnam (XFVT)** — phát hành/mua lại của các quỹ này tạo lực mua/bán thực trên HOSE (xem mục Dòng tiền ETF ngoại).
6. **Phí**: quản lý ~0,65–0,8%/năm + giám sát/lưu ký; thuế bán **0,1%** trên giá trị (như cổ phiếu).

## Phân loại ETF nội (theo chỉ số bám)

| ETF (mã) | Chỉ số bám | Đặc điểm |
|------|------|------|
| **E1VFVN30** (DCVFM), FUEKIV30, FUEMAV30 | VN30 | Large-cap bluechip; E1VFVN30 thanh khoản tốt nhất, là ETF gốc của thị trường |
| **FUEVFVND** (DCVFM), FUEMAVND, FUEBFVND | VNDIAMOND | Cổ phiếu hết room ngoại; cầu nước ngoài mạnh, hay phụ trội |
| **FUESSVFL** (SSIAM) | VNFINLEAD | Ngân hàng – tài chính dẫn dắt (ETF "ngành" hiếm hoi ở VN) |
| **FUEVN100** (SSIAM) | VN100 | Large + mid, rộng hơn VN30 |
| **FUEDCMID** (DCVFM) | VNMIDCAP | Vốn hóa trung bình |
| FUEKIVFS, FUESSVN50... | VNFINSELECT, VN50... | Rổ chuyên biệt, thanh khoản mỏng hơn |

> VN gần như **chỉ có ETF nhóm vốn hóa + 1–2 ETF chủ đề** (tài chính, kim cương). Không có hệ ETF ngành đầy đủ → **xoay ngành bằng ETF rất hạn chế** (chủ yếu phải dùng cổ phiếu đơn lẻ).

## Chỉ tiêu cốt lõi

### Tracking error (sai số bám)
Chỉ tiêu quan trọng nhất đo năng lực sao chép chỉ số.
```
TE annualized = std(LN ngày ETF − LN ngày chỉ số) × √252
```
- ETF nội thường **0,5–2%/năm** (cao hơn ETF Mỹ) do: phí giám sát/quản lý, độ trễ xử lý cổ tức, biến động sở hữu nước ngoài ở cổ phiếu hết room, lực mua/bán của AP, cổ phiếu bị hạn chế giao dịch.
- < 1% là tốt với ETF VN30; rổ chuyên biệt (VNDIAMOND/VNFINLEAD) thường lệch lớn hơn.

### Chiết khấu / phụ trội (so iNAV)
```
% phụ trội = (giá thị trường − iNAV) / iNAV × 100
```
- **Phụ trội** (giá > iNAV): AP tạo thêm CCQ (mua rổ cổ phiếu → đổi lấy ETF → bán) → phụ trội thu hẹp.
- **Chiết khấu** (giá < iNAV): AP mua lại (mua ETF → đổi lấy rổ cổ phiếu → bán) → chiết khấu thu hẹp.
- **Phụ trội kéo dài ở VNDIAMOND**: cầu nước ngoài lớn nhưng cổ phiếu trong rổ đã hết room → AP khó tạo thêm CCQ (không mua được cổ phiếu) → cơ chế thu hẹp phụ trội **bị nghẽn** → phụ trội có thể duy trì lâu. **Mua ETF VNDIAMOND khi phụ trội cao là rủi ro** (iNAV về mà phụ trội thu hẹp = lỗ kép).

### Thanh khoản
| Chỉ tiêu | Ý nghĩa | Tham chiếu |
|------|------|------|
| GTGD bình quân ngày | Mức độ dễ vào/ra | Càng cao càng tốt; E1VFVN30 cao nhất |
| Spread mua–bán | Chi phí giao dịch tức thời | Hẹp → tốt |
| Độ sâu sổ lệnh | Sức chịu lệnh lớn | Lệnh lớn nên chia nhỏ nhiều phiên |

### Phí & quy mô
- Phí quản lý ~0,65–0,8% + giám sát/lưu ký. Chênh phí tích lũy nhiều năm là đáng kể (xem helper bên dưới).
- AUM lớn → rủi ro đóng quỹ thấp, tạo lập sôi động; AUM teo dần là cờ cảnh báo.

## Chọn ETF (khung so sánh)

Khi nhiều ETF bám cùng một chỉ số (vd VN30 có E1VFVN30/FUEKIV30/FUEMAV30):
```
Bước 1: Quy mô     → loại sản phẩm AUM quá nhỏ (rủi ro đóng quỹ, thanh khoản kém)
Bước 2: Phí        → cùng điều kiện chọn phí thấp nhất
Bước 3: Tracking error → so 1 năm & 3 năm
Bước 4: Thanh khoản → GTGD bình quân, spread
Bước 5: Công ty QLQ → năng lực vận hành chỉ số hóa, chất lượng AP
```

```python
import numpy as np, pandas as pd

def tracking_error(etf_close: pd.Series, index_close: pd.Series) -> float:
    """TE annualized (%) giữa ETF và chỉ số bám. Hai series index theo ngày."""
    df = pd.concat([etf_close, index_close], axis=1).dropna()
    diff = df.iloc[:, 0].pct_change() - df.iloc[:, 1].pct_change()
    return round(diff.std() * np.sqrt(252) * 100, 4)

def premium_discount(market_price: float, inav: float) -> dict:
    """% phụ trội/chiết khấu so iNAV + cảnh báo."""
    pct = (market_price - inav) / inav * 100
    sig = "PHU_TROI" if pct > 0.3 else "CHIET_KHAU" if pct < -0.3 else "BINH_THUONG"
    return {"premium_pct": round(pct, 4), "signal": sig}

def fee_drag(annual_return: float, years: int, fees: list[float]) -> dict:
    """Bào mòn lợi nhuận dài hạn theo các mức phí (số thập phân, vd 0.007)."""
    base = (1 + annual_return) ** years
    out = {}
    for f in fees:
        end = (1 + annual_return - f) ** years
        out[f"{f*100:.2f}%"] = {"terminal": round(end, 4),
                                "drag_pct": round((base - end) / base * 100, 2)}
    return out
```

## Ứng dụng chiến lược

### Core–satellite
```
Lõi (70–80%): ETF VN30 (E1VFVN30) → beta thị trường, phí thấp, nắm dài
Vệ tinh (20–30%): VNDIAMOND (tiếp cận cổ phiếu hết room) / VNFINLEAD (đặt cược nhóm NH–tài chính)
Tái cân bằng: định kỳ quý hoặc khi lệch mục tiêu > 5%; ưu tiên dùng tiền mới bù lớp thiếu
```

### Hạn chế cần nhớ (đặc thù VN)
- **Ít ETF ngành** → muốn xoay ngành phải dùng cổ phiếu/rổ tự dựng, không chỉ ETF.
- **Không có ETF trái phiếu/vàng/hàng hóa nội** đủ thanh khoản → phân bổ đa tài sản kiểu "all-weather" khó thực hiện thuần bằng ETF; kết hợp với **quỹ mở trái phiếu** (xem `fund-analysis`).
- **VNDIAMOND**: dùng để tiếp cận room ngoại NHƯNG luôn kiểm phụ trội trước khi mua.

## Dòng tiền ETF ngoại (chỉ báo tâm lý nước ngoài)

Phát hành/mua lại CCQ của ETF ngoại đầu tư VN tạo lực **mua/bán thực** trên HOSE:
- **Fubon FTSE Vietnam ETF** (Đài Loan) — quy mô lớn, dòng tiền ảnh hưởng mạnh nhóm VN30/bluechip.
- **VanEck Vietnam ETF (VNM)**, **Xtrackers FTSE Vietnam (XFVT)** — dòng vốn Âu–Mỹ.

Quy đổi tín hiệu: ETF ngoại **phát hành ròng** (số CCQ tăng) → mua ròng cổ phiếu VN trong rổ → lực đỡ; **mua lại ròng** → bán ra. Theo dõi số CCQ lưu hành & chiết khấu/phụ trội của các ETF này để đoán dòng vốn ngoại. (Dữ liệu từ website quỹ/nguồn quốc tế — DataPro không cấp.)

## Review chỉ số & cơ hội sự kiện

- HOSE **review định kỳ** các chỉ số (VN30 review tháng 1 & 7); thêm/loại cổ phiếu → ETF bám buộc cơ cấu lại danh mục.
- Trước/sau ngày hiệu lực: cổ phiếu **được thêm** thường được gom (ETF phải mua), cổ phiếu **bị loại** bị bán → cơ hội sự kiện ngắn hạn. Soi danh sách dự kiến thêm/loại trước ngày chốt.

## Lưu ý quan trọng

1. **Phụ trội VNDIAMOND**: cơ chế arbitrage nghẽn khi cổ phiếu hết room → phụ trội có thể neo cao lâu; mua đỉnh phụ trội rất rủi ro.
2. **Cá nhân không arbitrage được**: tạo/mua lại in-kind chỉ dành cho AP với creation unit lớn — cá nhân chỉ giao dịch thứ cấp, chịu spread + phụ trội.
3. **Tracking error rổ chuyên biệt cao**: VNDIAMOND/VNFINLEAD lệch chỉ số nhiều hơn VN30 — soi TE thực tế, đừng tin nhãn "bám sát".
4. **Thanh khoản phân hóa mạnh**: ngoài E1VFVN30/FUEVFVND, nhiều ETF GTGD rất mỏng → lệnh lớn tự gây trượt giá, chia nhỏ nhiều phiên.
5. **iNAV trễ/sai khi có cổ phiếu hạn chế giao dịch** trong rổ → tham chiếu chiết khấu/phụ trội kém tin cậy giai đoạn đó.
6. **Phí bào dài hạn**: chênh ~0,2%/năm tích lũy 10–20 năm tạo khác biệt rõ — cùng chỉ số thì phí là yếu tố phân định.

## Nguồn dữ liệu (VN)

| Việc cần | Nguồn |
|------|------|
| Giá ETF, GTGD, OHLCV (tính TE/thanh khoản) | **DataPro** (`source="datapro"`, mã `.VN`, vd `E1VFVN30.VN`, `FUEVFVND.VN`) |
| Giá chỉ số bám (VN30, VNDIAMOND, VNFINLEAD, VN100...) | **DataPro** (`VN30.VN`...) |
| **iNAV / NAV / danh mục rổ (PCF) / số CCQ lưu hành / phí** | **Website công ty QLQ** (DCVFM, SSIAM, KIM, Mirae, Bảo Việt) — vnstock `Fund()` (Fmarket) **không phủ ETF niêm yết** |
| Cơ bản cổ phiếu trong rổ (soi holdings) | **vnstock KBS** (`ratio`/`income`); ngành ICB qua `Listing.symbols_by_industries()` |
| Dòng tiền ETF ngoại (Fubon/VNM/XFVT) | Website quỹ / nguồn quốc tế (DataPro/vnstock không cấp) |

Khi không có iNAV/holdings trực tiếp: nêu hạn chế, đưa khung phân tích, KHÔNG bịa số NAV/phụ trội.

## Phụ thuộc

```bash
pip install pandas numpy scipy
```
