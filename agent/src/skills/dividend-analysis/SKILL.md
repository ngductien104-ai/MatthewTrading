---
name: dividend-analysis
description: "Phân tích cổ tức cổ phiếu VN cho chiến lược thu nhập/tăng trưởng cổ tức — chất lượng & tính bền của cổ tức, độ bao phủ, cơ chế ngày GDKHQ, phân biệt cổ tức tiền mặt vs cổ phiếu, bẫy lợi suất. Nguồn: vnstock (events/ratio/BCTC) + DataPro (giá)."
category: analysis
---

# Phân tích cổ tức (Việt Nam)

## Mục đích

Dùng khi người dùng hỏi về cổ phiếu cổ tức, danh mục thu nhập, tăng trưởng cổ tức, lọc lợi suất cao, độ an toàn chi trả, ngày GDKHQ, hay cổ tức có bền không. Mục tiêu: **tách lợi suất bền vững khỏi bẫy lợi suất**.

Đừng dừng ở con số lợi suất bề mặt. Câu trả lời tốt giải thích cổ tức được tài trợ bằng gì, nền tảng kinh doanh ổn định ra sao, ban lãnh đạo còn dư địa trả không, và định giá ảnh hưởng thế nào tới tổng lợi nhuận.

## ⚠️ Đặc thù cổ tức Việt Nam (đọc TRƯỚC)

1. **Cổ tức công bố theo % MỆNH GIÁ (10.000đ), KHÔNG phải theo giá.** "Cổ tức 30%" = **30% × 10.000 = 3.000đ/cp**. Lợi suất thực = DPS / giá thị trường. Đây là nhầm lẫn phổ biến nhất.
2. **Hai loại — phải phân biệt:**
   - **Cổ tức TIỀN MẶT** (cash): thu nhập thật.
   - **Cổ tức bằng CỔ PHIẾU / cổ phiếu thưởng** (stock dividend/bonus): phát hành thêm CP → **pha loãng**, giá điều chỉnh giảm ngày GDKHQ → KHÔNG phải thu nhập, gần giống chia tách. Đừng tính vào lợi suất tiền mặt.
3. **Thuế TNCN**: cổ tức tiền mặt bị khấu trừ **5% tại nguồn**; cổ tức bằng cổ phiếu chịu thuế 5% **khi bán**.
4. **Ngày quan trọng**: **GDKHQ** (giao dịch không hưởng quyền — giá tham chiếu tự điều chỉnh giảm) → **ngày đăng ký cuối cùng** (T+2 sau GDKHQ) → **ngày thanh toán**.
5. **Ngân hàng**: chính sách cổ tức bị **NHNN ràng buộc/chấp thuận**; nhiều giai đoạn NHNN yêu cầu trả cổ tức bằng CỔ PHIẾU để giữ vốn (tăng CAR) → đừng kỳ vọng cổ tức tiền mặt cao ở ngân hàng đang cần tăng vốn.

## Câu hỏi cốt lõi

1. Lợi suất tiền mặt hiện tại bao nhiêu, có bình thường so với chính DN/ngành không?
2. Cổ tức có được bao phủ bởi LN, dòng tiền HĐKD (CFO) và dòng tiền tự do (FCF) không?
3. Bảng cân đối có đủ khỏe để vượt chu kỳ đi xuống không?
4. Ban lãnh đạo đã tăng/giữ/cắt/ngừng cổ tức qua các chu kỳ ra sao? (có hay chuyển sang trả cổ phiếu?)
5. Định giá còn dư địa tổng lợi nhuận sau thuế 5% và giả định tái đầu tư không?

## Chỉ tiêu then chốt

| Chỉ tiêu | Công thức | Tín hiệu khỏe | Cảnh báo |
|--------|---------|----------------|----------------|
| Lợi suất cổ tức (tiền mặt) | DPS tiền mặt năm / giá | Trên trung vị ngành + bao phủ ổn định | Cao bất thường vs lịch sử/ngành |
| Tỷ lệ chi trả từ LN | Cổ tức / LN sau thuế (DPS/EPS) | 30-70% (phi tài chính trưởng thành) | >90%, hoặc LN âm |
| Chi trả từ FCF | Cổ tức / FCF | <70% xuyên chu kỳ | Cổ tức > FCF ≥2 năm |
| Bao phủ bằng CFO | CFO / cổ tức đã trả | >1,5x | <1,0x |
| CAGR cổ tức | Tăng trưởng DPS 3/5/10 năm | Dương và thấp hơn tăng EPS/FCF | Tăng nhờ vay nợ |
| Nợ ròng / EBITDA | | Đòn bẩy phù hợp ngành | Đòn bẩy tăng trong khi cổ tức tăng |

> Theo ngành: ngân hàng/CK/bảo hiểm — coi cổ tức trong ràng buộc vốn (CAR/an toàn vốn); BĐS — cổ tức giật cục, hay trả cổ phiếu; tiện ích/KCN/dầu khí — trả tiền mặt cao & ổn định.

## Quy trình phân tích

### Bước 1: Chuẩn hóa cổ tức

- Tách **cổ tức tiền mặt** khỏi **cổ tức cổ phiếu/cổ phiếu thưởng** (chỉ tiền mặt mới là thu nhập).
- Tách cổ tức thường xuyên khỏi cổ tức đặc biệt/bất thường.
- Xác định tần suất (1 lần/năm, theo đợt, tạm ứng + còn lại).
- Quy DPS theo % mệnh giá ra đồng: `DPS = ty_le_phan_tram × 10000`.

```python
dps_tien_mat = ty_le_co_tuc_tien_mat * 10000      # % mệnh giá → đồng
loi_suat = dps_tien_mat / gia_thi_truong
```

### Bước 2: Kiểm tra độ bao phủ

```python
payout_LN = co_tuc_da_tra / loi_nhuan_sau_thue
payout_FCF = co_tuc_da_tra / fcf
bao_phu_CFO = cfo / co_tuc_da_tra
```

- **Tốt**: LN, CFO, FCF đều phủ cổ tức qua nhiều năm.
- **Theo dõi**: LN phủ nhưng FCF không (giai đoạn capex lớn).
- **Tránh**: trả cổ tức khi cả LN và FCF âm, trừ khi có lý do một lần rõ ràng + bảng CĐKT mạnh.

### Bước 3: Chất lượng tăng trưởng cổ tức

```python
dividend_cagr = (dps_cuoi / dps_dau) ** (1/so_nam) - 1
eps_cagr = (eps_cuoi / eps_dau) ** (1/so_nam) - 1
```

- CAGR cổ tức < CAGR EPS/FCF → còn dư địa tăng.
- CAGR cổ tức > EPS/FCF → tỷ lệ chi trả đang phình (rủi ro).
- Cổ tức đi ngang trong khi FCF tăng → dư địa ẩn / ban lãnh đạo thận trọng.

### Bước 4: Độ linh hoạt bảng cân đối

| Khoản | Vì sao quan trọng |
|------|----------------|
| Tiền & tương đương tiền | Đệm ngắn hạn |
| Nợ ròng / EBITDA | Gánh nặng nợ so với LN hoạt động |
| Khả năng trả lãi (ICR) | Trả nợ trước khi trả cổ đông |
| Lịch đáo hạn nợ | Rủi ro tái cấp vốn khi lãi suất cao |

### Bước 5: Tách lợi suất khỏi tổng lợi nhuận

Cổ phiếu cổ tức vẫn thua nếu lợi suất đến từ giá rơi. Luôn gắn thu nhập với định giá & tăng trưởng.

```python
tong_loi_nhuan_ky_vong = loi_suat_co_tuc + tang_truong_eps_ky_vong + tai_dinh_gia
```
Đây là khung kịch bản, không phải cam kết.

## Checklist bẫy lợi suất (yield trap)

Cảnh báo khi nhiều điều sau đúng:

- Lợi suất > 2x trung vị 5 năm của DN hoặc trung vị ngành.
- Tỷ lệ chi trả > 90%, hoặc payout FCF > 100%.
- Doanh thu/EPS/FCF giảm ≥2 năm.
- Nợ ròng/EBITDA tăng trong khi ICR giảm.
- DN vừa phát hành cổ phiếu/vay nợ trong khi vẫn duy trì cổ tức.
- Giá đã rơi TRƯỚC khi lợi suất trở nên hấp dẫn.
- Lịch sử có cắt/ngừng cổ tức, hoặc liên tục **chuyển từ trả tiền mặt sang trả cổ phiếu** (che giấu thiếu tiền).
- Ngành chịu áp lực cấu trúc/pháp lý/chu kỳ hàng hóa đi xuống.

## Các chiến lược

### Tăng trưởng cổ tức
Ưu tiên lợi suất vừa phải, CAGR cổ tức mạnh, tỷ lệ chi trả thấp, chất lượng DN bền → cho người muốn lãi kép + ít rủi ro cắt.

### Lợi suất cao chất lượng
Ưu tiên lợi suất NHƯNG yêu cầu bao phủ bằng tiền, bảng CĐKT vững, chuẩn chi trả theo ngành → cho người cần thu nhập hiện tại; phải bàn rủi ro cắt. Ứng viên VN điển hình: **tiện ích/điện (POW, NT2, REE), KCN (IDC, BCM), dầu khí (GAS, PVS), bảo hiểm**.

### Bắt cổ tức (dividend capture)
Mua trước GDKHQ chỉ để hưởng cổ tức **KHÔNG phải tiền miễn phí**: giá tham chiếu **tự điều chỉnh giảm** đúng ngày GDKHQ, cộng **thuế 5%** + phí + trượt giá → thường xóa hết phần cổ tức gộp. Chỉ dùng như phân tích rủi ro sự kiện.

## Nguồn dữ liệu

| Việc cần | Nguồn |
|------|------|
| **Lịch sử/lịch cổ tức, ngày GDKHQ, tỷ lệ, loại (tiền/cổ phiếu)** | **vnstock `Company.events()`** → lọc `category=="DIVIDEND"`; xem `event_title_vi` (phân biệt tiền vs cổ phiếu), `exright_date` (GDKHQ), `record_date`, `exercise_ratio`, `value_per_share`, `payout_date` |
| Lợi suất cổ tức | vnstock KBS `ratio` (`dividend_yield`); `Company.overview()` (`dividend_per_share_tsr`) |
| Cổ tức đã trả (bao phủ) | BCTC LCTT — phần tài chính (CFF), vnstock KBS `cashflow` |
| LN/CFO/FCF cho bao phủ | vnstock KBS `income` (`net_profit_loss_after_tax`), `cashflow` (CFO), capex |
| Lịch sử tăng vốn / pha loãng (cổ tức CP) | vnstock `Company.capital_history()`; `issue_share` từ `Company.overview()` |
| Giá để tính lợi suất | **DataPro** (`source="datapro"`, mã `.VN`) |

Khi không có dữ liệu trực tiếp: nêu hạn chế và đưa khung phân tích, KHÔNG bịa số cổ tức.

## Mẫu output

```markdown
### Phân tích cổ tức: [Mã .VN / DN]

**Kết luận:** [bền vững / theo dõi / rủi ro bẫy lợi suất]

| Chỉ tiêu | Giá trị | Diễn giải |
|--------|-------|----------------|
| Lợi suất cổ tức tiền mặt | ... | (DPS = X% mệnh giá = Y đồng) |
| Tỷ lệ chi trả từ LN | ... | ... |
| Payout FCF | ... | ... |
| Tăng trưởng cổ tức | ... | (tiền mặt vs cổ phiếu) |
| Bảng cân đối | ... | ... |

**Điều giữ vững cổ tức:** ...
**Điều có thể phá vỡ cổ tức:** ...
**Kịch bản:** Cơ sở / Xấu / Tốt

**Lưu ý:** Đây là nghiên cứu, không phải khuyến nghị giao dịch.
```

## Sai lầm thường gặp

- Coi lợi suất cao là định giá rẻ mà không hỏi vì sao giá rơi.
- **Nhầm % cổ tức là % trên giá** (thực ra trên mệnh giá 10.000đ).
- **Gộp cổ tức cổ phiếu vào lợi suất tiền mặt** (cổ phiếu = pha loãng, không phải thu nhập).
- Bỏ qua **thuế TNCN 5%** và điều chỉnh giá ngày GDKHQ khi tính "bắt cổ tức".
- So tỷ lệ chi trả ngân hàng (bị NHNN ràng buộc) với DN sản xuất thông thường.
- Khuyến nghị cổ phiếu cổ tức mà không bàn tổng lợi nhuận & rủi ro cắt cổ tức.
