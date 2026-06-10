"""Signal engine lọc cổ phiếu theo yếu tố cơ bản.

Lọc giá trị bằng ROE / biên LN / P-B, các mã đạt điều kiện được long đều trọng số.
Ưu tiên thị trường Việt Nam: dùng BCTC vnstock gắn qua ``fundamental_fields``
(cột tiền tố ``income_`` / ``balancesheet_``) + giá DataPro, tự tính tỷ số.
Vẫn tương thích A-share (tushare ``extra_fields``) và US/HK (cột pe/pb/roe).
"""

from typing import Dict, List, Optional

import numpy as np
import pandas as pd


class SignalEngine:
    """Signal engine lọc yếu tố cơ bản.

    Lọc cổ phiếu giá trị qua ROE + (tuỳ chọn) P/B + biên ròng, các mã đạt
    điều kiện chia đều trọng số.

    Attributes:
        roe_min: Sàn ROE (%).
        pb_max: Trần P/B (chỉ áp khi có ``shares_map``).
        pe_max: Trần P/E (chỉ áp khi có ``shares_map``).
        margin_min: Sàn biên ròng (%).
        shares_map: ``{mã: issue_share}`` số CP lưu hành — cần cho P/B, P/E.
    """

    def __init__(
        self,
        roe_min: float = 8.0,
        pb_max: float = 3.0,
        pe_max: float = 20.0,
        margin_min: float = 0.0,
        revenue_min: float = 0.0,
        equity_min: float = 0.0,
        shares_map: Optional[Dict[str, float]] = None,
    ):
        """Khởi tạo engine lọc cơ bản.

        Args:
            roe_min: Sàn ROE (%) (loại DN sinh lời thấp).
            pb_max: Trần P/B (áp khi có số CP lưu hành).
            pe_max: Trần P/E (áp khi có số CP lưu hành).
            margin_min: Sàn biên ròng (%) (tuỳ chọn).
            revenue_min: Sàn doanh thu thuần (đơn vị đồng theo BCTC vnstock).
            equity_min: Sàn vốn chủ sở hữu (đồng).
            shares_map: ``{mã: issue_share}``; thiếu thì bỏ qua lọc P/B, P/E.
        """
        self.roe_min = roe_min
        self.pb_max = pb_max
        self.pe_max = pe_max
        self.margin_min = margin_min
        self.revenue_min = revenue_min
        self.equity_min = equity_min
        self.shares_map = shares_map or {}

    def _passes_statement_filter(self, code: str, row: pd.Series) -> Optional[bool]:
        """Quyết định lọc theo BCTC, hoặc None khi không có dữ liệu BCTC.

        Ưu tiên cột vnstock (VN); lùi về cột tushare (A-share) để tương thích.
        """
        # --- Việt Nam (vnstock) ---
        revenue = _first_number(row, ["income_net_sales"])
        profit = _first_number(
            row, ["income_net_profit_loss_after_tax", "income_attributable_to_parent_company"]
        )
        equity = _first_number(row, ["balancesheet_owners_equity"])

        # --- A-share (tushare) — tương thích ngược ---
        if pd.isna(revenue):
            revenue = _first_number(row, ["income_total_revenue", "income_revenue"])
        if pd.isna(profit):
            profit = _first_number(row, ["income_n_income"])
        if pd.isna(equity):
            equity = _first_number(row, ["balancesheet_total_hldr_eqy_exc_min_int"])

        if all(pd.isna(v) for v in (revenue, profit, equity)):
            return None  # không có dữ liệu BCTC ở dòng này
        if pd.isna(profit) or pd.isna(equity) or equity <= 0:
            return False

        roe = profit / equity * 100.0
        if not (profit > 0 and equity > self.equity_min and roe >= self.roe_min):
            return False

        # Doanh thu: ngân hàng có thể rỗng net_sales → chỉ áp khi có
        if not pd.isna(revenue):
            if revenue < self.revenue_min:
                return False
            if self.margin_min > 0 and revenue > 0 and (profit / revenue * 100.0) < self.margin_min:
                return False

        # P/B (cần số CP lưu hành + giá). close DataPro tính bằng NGHÌN đồng.
        shares = self.shares_map.get(code)
        close = row.get("close", np.nan)
        if shares and pd.notna(close):
            market_cap = float(close) * 1000.0 * float(shares)
            pb = market_cap / equity
            if not (0 < pb < self.pb_max):
                return False
            if profit > 0:
                pe = market_cap / profit
                if not (0 < pe < self.pe_max):
                    return False
        return True

    def generate(self, data_map: Dict[str, pd.DataFrame]) -> Dict[str, pd.Series]:
        """Lọc theo điều kiện cơ bản, long đều trọng số các mã đạt.

        Args:
            data_map: Mã → DataFrame (OHLCV + cột BCTC tiền tố, hoặc pe/pb/roe).

        Returns:
            Mã → Series tín hiệu (1/N khi được chọn, 0 khi không).
        """
        codes = list(data_map.keys())
        if not codes:
            return {}

        all_dates = sorted(set().union(*(df.index for df in data_map.values())))
        date_index = pd.DatetimeIndex(all_dates)
        signals: Dict[str, pd.Series] = {code: pd.Series(0.0, index=date_index) for code in codes}

        for dt in date_index:
            qualified: List[str] = []
            for code, df in data_map.items():
                if dt not in df.index:
                    continue
                row = df.loc[dt]

                statement_pass = self._passes_statement_filter(code, row)
                if statement_pass is not None:
                    if statement_pass:
                        qualified.append(code)
                    continue

                # Lùi về tỷ số có sẵn theo ngày (US/HK qua yfinance, hoặc tushare daily_basic)
                pe = row.get("pe", np.nan)
                pb = row.get("pb", np.nan)
                roe = row.get("roe", np.nan)
                if pd.isna(pe) or pd.isna(pb) or pd.isna(roe):
                    continue
                if 0 < pe <= self.pe_max and pb <= self.pb_max and roe >= self.roe_min:
                    qualified.append(code)

            if qualified:
                weight = 1.0 / len(qualified)
                for code in qualified:
                    signals[code].at[dt] = weight

        return {code: signals[code].reindex(df.index).fillna(0.0) for code, df in data_map.items()}


def _first_number(row: pd.Series, columns: List[str]) -> float:
    """Trả về số đầu tiên tìm thấy trong row, nếu không có thì NaN."""
    for column in columns:
        value = row.get(column, np.nan)
        if pd.notna(value):
            return float(value)
    return np.nan


if __name__ == "__main__":
    # Demo: mô phỏng lọc cơ bản bằng cột BCTC vnstock (đơn vị đồng)
    np.random.seed(42)
    dates = pd.bdate_range("2024-01-01", "2024-12-31")

    def _mock(profit, equity, revenue, close):
        n = len(dates)
        return pd.DataFrame({
            "close": np.full(n, close),
            "volume": np.random.uniform(1e6, 1e7, n),
            "income_net_sales": np.full(n, revenue),
            "income_net_profit_loss_after_tax": np.full(n, profit),
            "balancesheet_owners_equity": np.full(n, equity),
        }, index=dates)

    data_map = {
        "FPT.VN": _mock(profit=9_000e9, equity=35_000e9, revenue=62_000e9, close=120.0),  # ROE ~25,7% → đạt
        "HPG.VN": _mock(profit=12_000e9, equity=110_000e9, revenue=140_000e9, close=27.0),  # ROE ~10,9% → đạt
        "XYZ.VN": _mock(profit=100e9, equity=20_000e9, revenue=5_000e9, close=15.0),        # ROE ~0,5% → loại
    }

    engine = SignalEngine(roe_min=8.0)
    signals = engine.generate(data_map)
    for code in data_map:
        sig = signals[code]
        print(f"{code}: {int((sig > 0).sum())}/{len(sig)} phiên trong danh mục")
