---
name: sector-rotation
description: "Phân tích xoay vòng ngành thị trường VN — phân ngành ICB, chấm điểm sức khỏe ngành (prosperity), xếp hạng momentum, truyền dẫn chuỗi ngành, so sánh đa chiều định giá/lợi nhuận/dòng tiền (khối ngoại). Nguồn: vnstock (phân ngành + chỉ số) + DataPro (giá + dòng tiền ngoại)."
category: asset-class
---

# Phân tích xoay vòng ngành (Việt Nam)

## Tổng quan

Dựa trên hệ phân ngành **ICB** (vnstock dùng), phân tích xoay vòng ngành qua 4 chiều — sức khỏe ngành (prosperity), momentum, định giá, dòng tiền — để đưa khuyến nghị **tăng tỷ trọng / giảm tỷ trọng** ngành.

## Hệ phân ngành ICB (thị trường VN)

| Nhóm | Ngành (ICB) | Mã đại diện |
|------|------|---------|
| Thượng nguồn / chu kỳ | Thép & Vật liệu (Basic Resources), Hóa chất, Dầu khí | HPG, HSG, DGC, GAS, BSR |
| Sản xuất / công nghiệp | Hàng & DV công nghiệp, Logistics/Cảng, Xây dựng | GMD, VCG, HHV |
| Tiêu dùng | Thực phẩm & đồ uống, Bán lẻ | VNM, SAB, MWG, PNJ |
| Công nghệ | Công nghệ thông tin | FPT, CMG |
| Tài chính | Ngân hàng, Chứng khoán, Bảo hiểm | VCB, TCB, SSI, BVH |
| Bất động sản | Nhà ở, Khu công nghiệp | VHM, NLG, KBC, BCM |
| Tiện ích / phòng thủ | Điện, Nước, Khí, Dược | POW, REE, DHG |

> Lấy thành viên ngành: `Listing(source="VCI").symbols_by_industries()` → cột `icb_name`. Nhận diện ngân hàng nhanh: `Company.overview().is_bank` (xem `valuation-model/classify_valuation.py`).

### Thuộc tính chu kỳ ngành

| Loại | Ngành | Đặc điểm | Động lực |
|------|------|------|---------|
| Chu kỳ mạnh | Thép/Vật liệu, Hóa chất, Dầu khí | LN biến động lớn, bám vĩ mô | PMI, giá hàng hóa, đầu tư công, giá dầu |
| Phòng thủ | Thực phẩm&ĐU, Dược, Điện/Nước | LN ổn định, thủ thế | CPI, tiêu dùng thiết yếu, cổ tức |
| Tăng trưởng | Công nghệ, Bán lẻ | PE cao, tăng trưởng nhanh | Tăng trưởng DT, thị phần, sức mua |
| Tài chính | Ngân hàng/Chứng khoán/Bảo hiểm | Bám lãi suất & thanh khoản | Tăng trưởng tín dụng, lãi suất SBV, thanh khoản TT |
| Bất động sản | Nhà ở, KCN | Chu kỳ pháp lý & tín dụng | Lãi suất, chính sách gỡ vướng, FDI (KCN) |

## Khung chấm điểm sức khỏe ngành (prosperity)

### Các chiều (tối đa 100)

| Chiều | Trọng số | Chỉ tiêu | Quy tắc chấm |
|------|------|------|---------|
| Tăng trưởng LN | 30% | LN sau thuế YoY (rổ ngành) | >30%=30đ, 15-30%=22đ, 0-15%=15đ, <0%=5đ |
| Xu hướng LN | 20% | Số quý tăng tốc liên tiếp | tăng tốc ≥3 quý=20đ, 2 quý=14đ, giảm tốc=−5đ |
| Chỉ báo cảnh báo sớm | 20% | PMI/công suất/giá sản phẩm | cao + đi lên=20đ, cao + chững=12đ, thấp=5đ |
| Chính sách hỗ trợ | 15% | Lực chính sách ngành | rõ ràng tích cực=15đ, trung tính=8đ, siết=2đ |
| Định giá an toàn | 15% | PE phân vị lịch sử (rổ ngành) | <30% phân vị=15đ, 30-50%=10đ, >70%=3đ |

### Tín hiệu sức khỏe ngành

```
Đi LÊN (tăng tỷ trọng):
1. PMI sản xuất VN >50 và cải thiện 2 tháng liên tiếp
2. Đơn hàng/doanh thu DN đầu ngành tăng tốc YoY
3. Giá sản phẩm đi lên (chu kỳ tăng giá)
4. Công suất >80% và đang tăng
5. Chính sách xúc tác (đầu tư công, nới room tín dụng, gỡ vướng BĐS, ưu đãi)

Đi XUỐNG (giảm tỷ trọng):
1. PMI <50 hai tháng liên tiếp
2. Số ngày tồn kho tăng (hàng ứ)
3. Giá sản phẩm giảm
4. Dư cung (công suất <60%)
5. Chính sách siết (thuế/môi trường/tín dụng)
```

## Xếp hạng momentum ngành

### Momentum giá

```python
def sector_momentum(sector_returns: pd.DataFrame, lookback: int = 60, skip: int = 5) -> pd.Series:
    """Xếp hạng momentum ngành.

    Args:
        sector_returns: lợi suất ngày theo ngành, columns = tên ngành (rổ .VN)
        lookback: cửa sổ nhìn lại (phiên)
        skip: bỏ N phiên gần nhất (tránh đảo chiều ngắn hạn)
    """
    cum_return = (1 + sector_returns).rolling(lookback).apply(lambda x: x[:-skip].prod() - 1)
    return cum_return.iloc[-1].rank(ascending=False)
```

### Momentum lợi nhuận

```
Momentum LN = (ROE YoY quý này) − (ROE YoY quý trước)
> 0 = LN tăng tốc (tăng tỷ trọng) · < 0 = giảm tốc (giảm tỷ trọng)
```

### Xếp hạng tổng hợp

```
Điểm = 0,4 × hạng momentum giá + 0,3 × hạng momentum LN + 0,3 × hạng dòng tiền ngoại
→ Top 5 tăng tỷ trọng, Bottom 5 giảm tỷ trọng
```

## Truyền dẫn chuỗi ngành (thượng → hạ nguồn)

```
Đầu tư công: giải ngân hạ tầng → nhà thầu xây dựng (VCG/HHV/C4G/LCG) → đá/nhựa đường/thép
Thép:        quặng-than (nhập) → thép (HPG/HSG/NKG) → BĐS/xây dựng/xuất khẩu HRC
Điện:        than/khí/thủy điện → phát điện (POW/NT2/REE/PC1) → tiêu thụ (El Niño/La Niña tác động thủy điện)
Xuất khẩu:   nguyên liệu → sản xuất (dệt may TNG/MSH; thủy sản VHC/ANV; gỗ) → đơn hàng Mỹ/EU + tỷ giá USD/VND
BĐS:         tín dụng/pháp lý → phát triển dự án → bán hàng (presales) → vật liệu (thép, xi măng HT1/BCC), nội thất
Ngân hàng:   tăng trưởng tín dụng → NIM → LN ngân hàng (dẫn dắt thanh khoản toàn thị trường)
```

### Quy luật truyền dẫn

| Quy luật | Diễn giải | Hàm ý đầu tư |
|------|------|---------|
| Cầu kéo từ dưới lên | Cầu hạ nguồn → đơn hàng trung nguồn → nguyên liệu thượng nguồn | Điểm đảo cầu nhìn hạ nguồn động trước |
| Chi phí đẩy từ trên xuống | Thượng nguồn tăng giá → chi phí trung nguồn → hạ nguồn tăng giá bán | Tăng giá lợi thượng nguồn, hại trung nguồn |
| Chu kỳ tồn kho | Chủ động tích → bị động tích → chủ động xả → bị động xả | "Bị động xả" là điểm mua |
| Dẫn/trễ | Thượng nguồn dẫn trung nguồn ~1-2 quý, trung dẫn hạ ~1-2 quý | Bố trí trước mắt xích kế tiếp |

## Khung so sánh ngành

### So sánh định giá (rổ ngành — vnstock KBS `ratio`)

| Chỉ tiêu | Dùng | Lưu ý |
|------|------|---------|
| PE (`pe_ratio`) | Định giá theo LN | Cổ phiếu chu kỳ PE méo (PE thấp = đỉnh) |
| PB (`pb_ratio`) | Định giá theo tài sản | Ngân hàng/BĐS/chu kỳ dùng PB hợp lý hơn |
| PE phân vị 5 năm | Vị trí định giá | Đối chiếu lịch sử |
| Tỷ suất cổ tức (`dividend_yield`) | Lợi suất | Cổ tức cao = phòng thủ |

### So sánh lợi nhuận

| Chỉ tiêu (KBS ratio) | Ý nghĩa |
|------|------|
| `roe` | Khả năng sinh lời |
| ΔROE | Xu hướng lợi nhuận |
| `gross_margin` | Cục diện cạnh tranh |
| tăng trưởng `net_revenue`/LN | Tăng trưởng |
| CFO/LN ròng | Chất lượng lợi nhuận |

### So sánh dòng tiền (đặc thù VN)

| Chỉ báo | Nguồn | Tín hiệu |
|------|------|------|
| **Khối ngoại mua/bán ròng** | **DataPro** (`FRN_BUY_VOL/FRN_SELL_VOL`) tổng hợp theo ngành | Khẩu vị ngoại, dẫn dắt 1-3 tháng *(lưu ý regime: nhiều giai đoạn ngoại bán ròng)* |
| Dư nợ ký quỹ (margin) | HOSE/CTCK công bố | Dòng tiền đòn bẩy |
| Tự doanh CTCK | HOSE | Tín hiệu tổ chức |
| ETF (E1VFVN30, Diamond FUEVFVND, Finlead, Fubon/VanEck) | Quỹ | Phân bổ tổ chức/ngoại |

## Mẫu output

```markdown
## Phân tích xoay vòng ngành

### Xếp hạng sức khỏe Top 10
| Hạng | Ngành | Điểm | Thay đổi | Logic cốt lõi |
|------|------|------|------|---------|
| 1 | Ngân hàng | 82 | ↑+6 | Tín dụng tăng tốc, NIM tạo đáy |
| 2 | Thép | 78 | ↑+5 | Đầu tư công + xuất khẩu HRC |

### Khuyến nghị phân bổ
| Phân bổ | Ngành | Tỷ trọng | Logic |
|------|------|---------|---------|
| Tăng tỷ trọng | Ngân hàng, Thép, Đầu tư công | 10-15% mỗi | Sức khỏe lên + chính sách |
| Trung lập | Tiêu dùng, Dược | 5-8% mỗi | Phòng thủ, định giá hợp lý |
| Giảm tỷ trọng | BĐS nhà ở | 0-3% | Pháp lý/tín dụng chờ cải thiện |

### Cơ hội chuỗi ngành
- **Đầu tư công**: giải ngân → nhà thầu (trung nguồn) → thép/đá (thượng nguồn)

### Rủi ro
- ...
```

## Lưu ý

1. **Bẫy định giá cổ phiếu chu kỳ**: PE thấp có thể là đỉnh lợi nhuận (thép 2021-2022 PE rất thấp tại đỉnh) → dùng PB an toàn hơn.
2. **Trọng số chính sách rất lớn**: xoay vòng ngành VN bị dẫn dắt mạnh bởi chính sách (đầu tư công, nới room tín dụng, gỡ vướng BĐS, quy hoạch điện VIII) — điểm đảo chính sách > điểm đảo cơ bản.
3. **Nhiễu đầu cơ theo sóng**: sóng chủ đề ngắn hạn bóp méo momentum ngành — phân biệt "sóng" vs "sức khỏe thật".
4. **Dòng tiền ngoại dẫn dắt NHƯNG tùy regime**: nhiều giai đoạn ngoại bán ròng kéo dài → đọc dòng tiền ngoại theo bối cảnh, không máy móc.
5. **ETF ngành VN hạn chế**: ít ETF đơn ngành như TQ → phân bổ ngành chủ yếu bằng RỔ CỔ PHIẾU đầu ngành.
6. **Tần suất**: xoay vòng không nên quá dày — đảo danh mục theo tháng/quý.
7. **Độ trễ dữ liệu**: BCTC trễ ~1-3 tháng; dữ liệu tần suất cao (PMI/giá hàng hóa/dòng tiền ngoại) kịp thời hơn.

## Nguồn dữ liệu

- **Phân ngành + thành viên → vnstock** `Listing(source="VCI").symbols_by_industries()` (`icb_name`); `Company.overview().is_bank/sector/icb_code_lv2`.
- **Chỉ số ngành (PE/PB/ROE/biên/tăng trưởng) → vnstock KBS `ratio`** tổng hợp theo rổ thành viên.
- **Momentum giá ngành → DataPro** (`source="datapro"`, mã `.VN`): lợi suất rổ ngành.
- **Dòng tiền khối ngoại theo ngành → DataPro** (`FRN_BUY_VOL/FRN_SELL_VOL` cộng dồn theo ngành) — lợi thế: có sẵn theo ngày.
- **Vĩ mô (PMI VN, tăng trưởng tín dụng, lãi suất SBV, đầu tư công, FDI, giá hàng hóa) → firecrawl/`web-reader`**: GSO, SBV, S&P Global Vietnam PMI.
