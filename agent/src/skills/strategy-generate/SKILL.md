---
name: strategy-generate
description: "Tạo, chỉnh sửa và tối ưu chiến lược giao dịch định lượng cho TTCK VN (cổ phiếu .VN, VN-Index/VN30), sau đó backtest và đánh giá kết quả. Vẫn hỗ trợ đa thị trường (A-share, Mỹ, HK, crypto) qua cùng một engine."
category: strategy
---
# Sinh chiến lược giao dịch (Việt Nam)

## Quy trình

1. **Bóc tách yêu cầu**: hiểu ý định người dùng, trích mã cổ phiếu, khoảng thời gian và logic chiến lược, rồi ghi `config.json`
2. **Thiết kế chiến lược**: suy nghĩ qua 5 câu hỏi dữ liệu / tín hiệu / quản lý vị thế / backtest / kiểm định
3. **Viết code**: viết `code/signal_engine.py` (theo đúng hợp đồng `SignalEngine`)
4. **Kiểm tra cú pháp**: `bash("python -c \"import ast; ast.parse(open('code/signal_engine.py').read()); print('OK')\"")`
5. **Chạy backtest**: gọi công cụ `backtest` (đã tích hợp sẵn trong engine; KHÔNG cần viết `run_backtest.py`)
6. **Đánh giá kết quả**: đọc `artifacts/metrics.csv` và chấm theo tiêu chí đánh giá
7. **Sửa lặp**: nếu kết quả kém, sửa bằng `edit_file` → chạy lại `backtest` → đánh giá lại

**Bạn chỉ cần viết `signal_engine.py` và `config.json`. Công cụ `backtest` tự lo nạp dữ liệu và chạy backtest.**

## Bóc tách yêu cầu

Trích các thông tin sau từ mô tả của người dùng:
- **Mã cổ phiếu**: chuẩn hóa theo quy tắc bên dưới (mã VN gắn hậu tố `.VN`)
- **Khoảng thời gian**: nếu người dùng không nêu ngày, mặc định **lùi 10 năm tính từ hôm nay** (ví dụ hôm nay `2026-06-15` → `start_date=2016-06-15`, `end_date=2026-06-15`)
- **Logic chiến lược**: điều kiện vào / ra lệnh và tham số chỉ báo

**Thiếu thông tin then chốt thì PHẢI hỏi lại, không đoán bừa:**
- Không nêu mã → hỏi muốn backtest mã nào (gợi ý vài mã phổ biến: VCB, HPG, FPT, VNINDEX…)
- Mô tả chiến lược mơ hồ (ví dụ "giúp tôi xây một chiến lược") → đưa 2–3 hướng để người dùng chọn
- Trộn nhiều thị trường nhưng không nói rõ → xác nhận nguồn dữ liệu

**Ghi `config.json` trước, viết code sau.** `config.json` phải nằm ở thư mục gốc của `run_dir`.

## Thiết kế chiến lược

Trước khi viết code, suy nghĩ qua 5 câu hỏi:

1. **Nhu cầu dữ liệu**: cần trường gì (chỉ OHLCV cơ bản, hay trường định giá theo ngày như `pe/pb/roe`, hay trường BCTC như `income_net_sales` / `balancesheet_total_assets`?), tần suất (theo ngày), và thị trường nào (quyết định nguồn dữ liệu)
2. **Logic tín hiệu**: điều kiện vào lệnh? Điều kiện thoát? Chiều (long / short / long-short)? Có bộ lọc không (thanh khoản, xác nhận xu hướng…)?
3. **Quản lý vị thế**: phân bổ đều hay tăng/giảm dần? Kiểm soát rủi ro (cắt lỗ, vị thế tối đa)? Với chiến lược danh mục, sau khi chọn top N mã thì mỗi mã có tỷ trọng = 1/N
4. **Tham số backtest**: khoảng thời gian, vốn ban đầu (mặc định 1.000.000), phí giao dịch (mặc định 0,1%)
5. **Danh mục kiểm định**: nhất quán tín hiệu (không có tín hiệu NaN), kiểm tra vị thế (đã chuẩn hóa để tránh đòn bẩy ngoài ý muốn), và đủ artifacts đầu ra

Không cần xuất tài liệu thiết kế dạng JSON. Hãy thể hiện các quyết định thiết kế này trực tiếp trong code.

## Hợp đồng `SignalEngine`

```python
class SignalEngine:
    def generate(self, data_map: Dict[str, pd.DataFrame]) -> Dict[str, pd.Series]:
        """
        Args:
            data_map: mã -> DataFrame (cột: open, high, low, close, volume, DatetimeIndex)
                     Nếu khai báo config.extra_fields, sẽ có thêm các cột định giá theo ngày
                     (pe, pb, roe... — chỉ A-share/tushare hỗ trợ).
                     Nếu khai báo config.fundamental_fields, sẽ có thêm các cột BCTC an toàn
                     theo thời điểm (PIT) như income_net_sales, income_gross_profit,
                     balancesheet_total_assets (mã VN dùng key VAS của vnstock).
        Returns:
            mã -> Series tín hiệu, miền giá trị [-1.0, 1.0]
            1.0 = long toàn bộ, 0.5 = nửa vị thế, 0.0 = đứng ngoài, -1.0 = short toàn bộ
            Chiến lược danh mục: các mã được chọn chia đều tỷ trọng (vd top 10 -> mỗi mã 0.1)
            Tín hiệu số nguyên kiểu cũ {-1, 0, 1} vẫn tương thích (hiểu là -100% / 0% / 100%)
        """
```

**Ràng buộc cứng:**
- Index của `Series` tín hiệu phải khớp chính xác với index của `DataFrame` đầu vào
- Khai báo đầy đủ import (`numpy`, `pandas`…)
- Không hardcode ngày hay mã cổ phiếu (đọc từ `config.json`)
- Không có khối `if __name__ == "__main__"`
- Thuần pandas / numpy, không dùng thư viện sinh tín hiệu bên ngoài
- Xuất code Python thuần, không bọc trong khối Markdown

## Danh mục kiểm tra chất lượng

Tự kiểm tra sau khi viết `signal_engine.py`:
- [ ] Đủ import (`numpy`, `pandas`, `typing`…)
- [ ] Không có biến chưa định nghĩa
- [ ] Logic tín hiệu nhất quán với mô tả chiến lược
- [ ] Xử lý biên: dữ liệu rỗng hoặc chưa đủ lịch sử trước cửa sổ lookback → dùng `fillna(0)` hoặc bỏ qua
- [ ] Chiến lược danh mục: chọn N mã thì mỗi mã tỷ trọng = 1/N (vd top 10 → mỗi mã 0.1), mã không chọn = 0
- [ ] Giá trị tín hiệu nằm trong `[-1.0, 1.0]`

## Chuẩn hóa mã

- **Cổ phiếu/chỉ số Việt Nam**: chữ in hoa + số, gắn hậu tố `.VN`, ví dụ `VCB.VN`, `HPG.VN`, `FPT.VN`, chỉ số `VNINDEX.VN` / `VN30.VN`
  - Người dùng thường viết mã trần (`VCB`); `config.json` nên dùng `"VCB.VN"`. Hậu tố `.VN` là thứ định tuyến mã sang engine VN và sẽ bị cắt bỏ trước khi gọi API
- Mã A-share 6 số → tự gắn hậu tố: bắt đầu bằng `600/601/603` → `.SH`, còn lại → `.SZ`
- Cổ phiếu Mỹ: chữ in hoa + `.US`, ví dụ `AAPL.US`
- Cổ phiếu Hong Kong: số + `.HK`, ví dụ `700.HK`
- Crypto: dạng `BTC-USDT` (cặp spot OKX, **dùng gạch nối `-`, không dùng `/`**)
  - Người dùng có thể viết `BTC/USDT`, nhưng `config.json` phải dùng `"BTC-USDT"`

## Nhận diện thị trường và nguồn dữ liệu

| Mẫu mã | Thị trường | source | Trường mở rộng |
|------|------|--------|----------|
| `^[A-Z0-9]{2,9}\.VN$` | **Cổ phiếu VN** | datapro → vnstock | `fundamental_fields`: income/balancesheet/cashflow (key VAS của vnstock). KHÔNG dùng `extra_fields` |
| `^\d{6}\.(SZ\|SH\|BJ)$` | A-share Trung Quốc | tushare | `extra_fields`: pe, pb, pe_ttm, ps_ttm, dv_ttm, total_mv, circ_mv, roe; `fundamental_fields`: income/balancesheet/cashflow/fina_indicator |
| `^[A-Z]+\.US$` | Cổ phiếu Mỹ | yfinance | - |
| `^\d{3,5}\.HK$` | Cổ phiếu Hong Kong | yfinance | - |
| `^[A-Z]+-USDT$` | Crypto | okx | - |

**Định tuyến nguồn VN**: mã `.VN` đi vào chuỗi fallback `vn_equity` = `datapro` → `vnstock`.
- **datapro** (ưu tiên): bars VN đầy đủ nhất (OHLCV điều chỉnh + khối ngoại + giá tham chiếu `REF_PX`), nhưng cần app DataPro desktop chạy ở `localhost:6789`
- **vnstock** (fallback, không cần cài đặt): lấy bars qua internet, không phụ thuộc desktop. Không có `REF_PX` nên `pre_close` được suy ra từ giá đóng cửa phiên trước (chuẩn proxy giá tham chiếu HOSE/HNX, để engine VN vẫn áp xấp xỉ biên ±7/10/15%)
- Đặt `source: "auto"` để engine tự chọn; hoặc ép `"datapro"` / `"vnstock"`

**Quy tắc chọn `extra_fields`**: chỉ A-share (`tushare`) hỗ trợ trường định giá theo ngày (pe/pb/roe). Với mã VN, Mỹ, HK, crypto → để `null`.

**Quy tắc chọn `fundamental_fields`**: dùng cho bộ lọc trước theo BCTC.
- **Mã VN**: provider vnstock lấy `income` / `balancesheet` / `cashflow` rồi merge vào bars theo `merge_asof` (an toàn PIT — chỉ gắn số liệu kỳ sau ngày công bố; mặc định trễ 90 ngày theo quy định BCTC kiểm toán năm). Cột đầu ra gắn tiền tố bảng, ví dụ `income_net_sales`, `income_gross_profit`, `balancesheet_total_assets`. **Lưu ý**: tier community vnstock chỉ trả ~4 kỳ năm gần nhất → bars sớm trong backtest dài có thể NaN. Chỉ số (P/E, ROE) KHÔNG phơi ra ở đây vì endpoint `ratio()` cộng đồng có bố cục kỳ không đáng tin → muốn phân tích chỉ số hãy dùng skill `valuation-model`
- **A-share**: provider tushare lấy `income` / `balancesheet` / `cashflow` / `fina_indicator`, cột tiền tố `income_total_revenue`, `fina_indicator_roe`…

## Định dạng `config.json`

```json
{
  "source": "auto",
  "codes": ["VCB.VN"],
  "start_date": "2016-06-15",
  "end_date": "2026-06-15",
  "interval": "1D",
  "initial_cash": 1000000,
  "commission": 0.001,
  "extra_fields": null,
  "fundamental_fields": null,
  "optimizer": null,
  "optimizer_params": {},
  "engine": "daily",
  "validation": null
}
```

- `source`: `"auto"` (khuyến nghị, tự chọn theo định dạng mã) / `"datapro"` / `"vnstock"` / `"tushare"` / `"yfinance"` / `"okx"` / `"akshare"` / `"ccxt"`
  - `"auto"` hỗ trợ trộn mã đa thị trường. Ví dụ `["VCB.VN", "BTC-USDT"]` sẽ tự định tuyến sang `datapro` và `okx`
  - Mã phái sinh (vd `"IF2406.CFFEX"`, `"ESZ4"`) và cặp ngoại hối (vd `"EUR/USD"`) cũng tự định tuyến
- `interval`: khung nến, mặc định `"1D"`. Hỗ trợ: `"1m"` / `"5m"` / `"15m"` / `"30m"` / `"1H"` / `"4H"` / `"1D"`
  - Hệ số quy năm cho backtest phút được suy tự động từ `source` (252 phiên cho cổ phiếu VN/A-share, 365 ngày lịch cho crypto)
  - Backtest phút rất nặng dữ liệu. Khuyến nghị giới hạn: tối đa 30 ngày với `1m`, hoặc 1 năm với `1H`
- `extra_fields`: chỉ A-share dùng được giá trị như `["pe", "pb", "roe"]`; mã VN và thị trường khác để `null`
- `fundamental_fields`: tùy chọn, lọc trước theo BCTC. Mã VN dùng `{"income": ["net_sales", "gross_profit"], "balancesheet": ["total_assets"]}`; để `null` nếu chiến lược không cần
- `optimizer`: tùy chọn, một trong `"equal_volatility"` / `"risk_parity"` / `"mean_variance"` / `"max_diversification"` / `null` (mặc định phân bổ đều)
- `optimizer_params`: tham số optimizer, vd `{"lookback": 60}`. `mean_variance` còn nhận `{"risk_free": 0.0}`
- `engine`: engine backtest, mặc định `"daily"`. Chiến lược quyền chọn dùng `"options"` (cần `OptionsSignalEngine`)
- `initial_cash`: mặc định 1.000.000
- `commission`: mặc định 0,1%
- `validation`: tùy chọn, kiểm định thống kê sau khi backtest xong. Bỏ qua thì không chạy. Ví dụ:
  ```json
  "validation": {
    "monte_carlo": {"n_simulations": 1000},
    "bootstrap": {"n_bootstrap": 1000, "confidence": 0.95},
    "walk_forward": {"n_windows": 5}
  }
  ```
  - `monte_carlo`: kiểm định hoán vị — xáo trộn thứ tự lệnh để tính p-value (Sharpe có vượt ngẫu nhiên một cách có ý nghĩa không?)
  - `bootstrap`: lấy mẫu lại lợi suất ngày để tính khoảng tin cậy 95% của Sharpe
  - `walk_forward`: chia đường vốn thành N cửa sổ, kiểm tra tính nhất quán hiệu suất
  - Mỗi khóa là tùy chọn — chỉ thêm phần kiểm định bạn muốn
  - Có thể chạy độc lập trên kết quả cũ: `python -m backtest.validation <run_dir>`

## Tiêu chí đánh giá

### Cổng cứng (sai bất kỳ điều nào → `passed=false`)

1. `artifacts/metrics.csv` tồn tại và không rỗng
2. `artifacts/equity.csv` tồn tại và không rỗng
3. `exit_code == 0` (backtest thoát bình thường)
4. Cột `equity` trong `equity.csv` không có giá trị `NaN`
5. `trade_count > 0` (không có lệnh nào = lỗi tín hiệu)

### Quy tắc chấm điểm

- Backtest thành công + đủ artifacts + ít nhất 1 lệnh → `score ≥ 60` → **passed**
- Lợi nhuận thấp / Sharpe thấp đơn thuần KHÔNG được kéo điểm xuống dưới 60; chỉ là gợi ý tối ưu
- `score ≥ 60` = `passed=true`

### Phân loại lỗi (trừ điểm)

1. **Không có lệnh** (`trade_count=0`): lỗi logic tín hiệu, điều kiện có thể quá chặt
2. **Lệnh đầu quá muộn** (lệnh đầu > 2 năm sau ngày bắt đầu): lỗi lọc dữ liệu hoặc cửa sổ lookback quá dài
3. **Hiệu suất sử dụng vốn < 50%**: lỗi quản lý vị thế, danh mục đứng ngoài phần lớn thời gian
4. **Còn vị thế mở khi kết thúc**: lỗi thời điểm tín hiệu thoát

### Định dạng `action_items`

Nếu cần cải thiện sau đánh giá, ghi `action_items`:
- Định dạng: `"Đổi X từ A thành B"` hoặc `"Thêm logic X trong signal_engine.py"`
- Phải cụ thể đến giá trị tham số, tên file, tên hàm
- Tối thiểu 2 mục
- Ví dụ:
  - `"Đổi MA ngắn từ 5 lên 10 ngày để giảm tín hiệu nhiễu (whipsaw)"`
  - `"Thêm cắt lỗ: buộc đóng khi lỗ vượt 5%"`
  - `"Thêm bộ lọc thanh khoản trong signal_engine.py: chỉ kích hoạt mua khi khối lượng cao"`

## Lưu ý đặc thù TTCK VN

- **Biên độ trần/sàn**: HOSE ±7%, HNX ±10%, UPCoM ±15%. Engine VN dùng giá tham chiếu (`REF_PX` từ datapro, hoặc `pre_close` proxy từ vnstock) để áp biên — lệnh khớp ở giá kịch biên có thể bị chặn. Chiến lược bám sát đỉnh/đáy trong phiên cần lưu ý
- **T+ thanh toán**: cổ phiếu VN không bán được ngay trong ngày mua (chu kỳ T+2/T+2.5). Backtest theo ngày xấp xỉ chấp nhận được, nhưng chiến lược tần suất cao cần cẩn trọng giả định khớp lệnh
- **Thanh khoản**: nhiều mã vốn hóa nhỏ thanh khoản mỏng; nên thêm bộ lọc khối lượng để tránh tín hiệu trên mã khó khớp

## Chiến lược đa thị trường

Khi người dùng yêu cầu backtest với các mã thuộc **thị trường khác nhau** (vd `["VCB.VN", "BTC-USDT"]`):
- Đặt `source: "auto"` trong `config.json`
- `CompositeEngine` tự lo căn lịch giao dịch, dùng chung vốn, và áp luật riêng từng thị trường
- Dùng tỷ trọng điều chỉnh theo biến động để tài sản biến động mạnh (crypto) không lấn át ngân sách rủi ro
- Xem skill [cross-market-strategy](../cross-market-strategy/SKILL.md) để biết tham số từng thị trường, cách điều chỉnh biến động và code mẫu

## Tệp đi kèm

- [examples.md](examples.md) — chuỗi lời gọi mẫu


## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)

1. **Không bịa/cook số liệu.** Mọi số tài chính phải có nguồn thật. Luôn **audit nhanh, cross-check tối thiểu 2 nguồn uy tín** (vd `cafef.vn`, `vietstock.vn`) — dùng **crawl4ai** cào số rồi đối chiếu; nếu nguồn lệch nhau thì nêu rõ, không chọn bừa.
2. **Nếu DataPro VÀ vnstock đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
