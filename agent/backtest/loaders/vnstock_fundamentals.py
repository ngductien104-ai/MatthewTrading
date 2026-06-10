"""vnstock fundamental-statement provider with point-in-time safeguards.

Pairs with the DataPro price loader: DataPro gives OHLCV / foreign flow, vnstock
gives the financial statements. Exposes the same small provider contract as
``tushare_fundamentals`` so the shared
``enrich_price_frames_with_fundamentals`` merge can attach PIT-safe statement
columns to a VN price frame.

Point-in-time model
-------------------
vnstock does **not** return a filing/announcement date, so we synthesise one: a
period's figures only become visible ``DISCLOSURE_LAG_DAYS`` after the period
end (Vietnam-listed firms must publish audited annual reports within 90 days).
Each row's ``ann_date`` = period_end + lag, and ``merge_asof`` then attaches a
period only to bars on/after that date — no lookahead.

Limitations (community tier)
----------------------------
* Only the most recent ~4 annual periods are returned, so early bars in a long
  backtest may have NaN fundamentals.
* Field names are vnstock ``item_id`` keys (e.g. ``net_sales``, ``gross_profit``,
  ``total_assets``). Ratios (P/E, ROE) are intentionally not exposed here — the
  community ``ratio()`` endpoint returns an unreliable period layout; use the
  ``valuation-model`` skill for ratio analysis instead.
"""

from __future__ import annotations

import contextlib
import io
import os
import re
from typing import Iterable

import pandas as pd

# Reuse the schema/error vocabulary so the two providers stay interchangeable.
from backtest.loaders.tushare_fundamentals import (
    DataProviderError,
    TableSchema,
    UnknownTableError,
)

# Days after period end before a report is treated as public (audited annual
# reports are due within 90 days for VN-listed companies).
DISCLOSURE_LAG_DAYS = 90

# Logical table name -> vnstock Finance method.
_TABLE_METHODS = {
    "income": "income_statement",
    "balancesheet": "balance_sheet",
    "cashflow": "cash_flow",
    "ratio": "ratio",
}

# Data source per table. Statements use VCI (item_id đã kiểm thử PIT). Ratios use
# KBS — nguồn KBS trả chỉ số SẠCH theo đặc thù ngành (roe/pe_ratio/pb_ratio/
# net_margin/ev_ebitda/beta..., ngân hàng có net_interest_margin_nim); VCI ratio()
# trả layout kỳ lỗi nên không dùng cho chỉ số.
_TABLE_SOURCES = {"ratio": "kbs"}

_SCHEMAS = {
    table: TableSchema(
        name=table,
        api_name=method,
        point_in_time_column="ann_date",
        columns=(),
    )
    for table, method in _TABLE_METHODS.items()
}

# Khớp cả "2024" (VCI statements) lẫn "2024-Năm" (KBS ratio) — bắt 4 số năm đầu.
_YEAR_RE = re.compile(r"^(\d{4})")


class VNStockFundamentalProvider:
    """Provider over vnstock annual financial statements (VCI source)."""

    def __init__(self, source: str = "VCI", period: str = "year") -> None:
        self.source = source
        self.period = period
        self._finance_cls = self._import_finance()

    @staticmethod
    def _import_finance():
        """Import vnstock's Finance, swallowing its stdout banner.

        The banner would otherwise corrupt the runner's JSON stdout envelope.
        """
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                from vnstock import Finance              # API mới (v3.4.0+)
            except Exception:  # noqa: BLE001 - tương thích ngược bản cũ
                from vnstock.api.financial import Finance
        return Finance

    def list_tables(self) -> list[str]:
        """Return supported statement tables in stable order."""
        return sorted(_SCHEMAS)

    def describe_table(self, table: str) -> TableSchema:
        """Return schema metadata for a supported table."""
        try:
            return _SCHEMAS[table]
        except KeyError as exc:
            raise UnknownTableError(f"Unsupported vnstock fundamental table: {table}") from exc

    def query_fundamentals(
        self,
        table: str,
        codes: Iterable[str],
        *,
        as_of: str | pd.Timestamp,
        periods: Iterable[str] | None = None,
        fields: Iterable[str] | None = None,
    ) -> pd.DataFrame:
        """Return a long PIT frame: ts_code, end_date, ann_date + requested fields."""
        schema = self.describe_table(table)
        method_name = schema.api_name
        field_list = list(fields or [])
        requested_periods = {str(p) for p in (periods or [])}
        as_of_ts = pd.Timestamp(as_of).normalize() if as_of else None

        records: list[dict] = []
        for original in codes:
            symbol = self._bare(original)
            try:
                statement = self._fetch_statement(symbol, table, method_name)
            except Exception as exc:  # noqa: BLE001 - one bad symbol must not abort
                print(f"[WARN] vnstock {table} for {symbol} failed: {exc}")
                continue
            if statement is None or statement.empty or "item_id" not in statement.columns:
                continue

            year_cols = [c for c in statement.columns if _YEAR_RE.match(str(c))]
            by_id = statement.set_index("item_id")
            seen_years: set[str] = set()
            for col in year_cols:
                year_str = _YEAR_RE.match(str(col)).group(1)
                if year_str in seen_years:  # KBS có thể lặp cột năm — lấy lần đầu
                    continue
                seen_years.add(year_str)
                if requested_periods and year_str not in requested_periods:
                    continue
                ann_date = pd.Timestamp(f"{year_str}-12-31") + pd.Timedelta(days=DISCLOSURE_LAG_DAYS)
                if as_of_ts is not None and ann_date > as_of_ts:
                    continue  # not yet disclosed as-of the backtest cut-off
                row: dict = {
                    "ts_code": original,
                    "end_date": year_str,
                    "ann_date": ann_date,
                }
                for field in field_list:
                    row[field] = self._value(by_id, field, col)
                records.append(row)

        if not records:
            return pd.DataFrame(columns=["ts_code", "end_date", "ann_date", *field_list])

        result = pd.DataFrame.from_records(records)
        return result.sort_values(["ts_code", "end_date"]).reset_index(drop=True)

    # ── internals ──

    def _fetch_statement(self, symbol: str, table: str, method_name: str) -> pd.DataFrame | None:
        """Call the vnstock Finance method for one symbol (stdout suppressed).

        Ratios use the KBS source (clean industry-aware metrics); statements use
        the configured source (VCI).
        """
        source = _TABLE_SOURCES.get(table, self.source)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            finance = self._finance_cls(symbol=symbol, source=source)
            method = getattr(finance, method_name, None)
            if method is None:
                raise DataProviderError(f"vnstock Finance has no method: {method_name}")
            if table == "ratio":
                return method(period=self.period)  # KBS ratio: item_id sẵn, không cần lang
            return method(period=self.period, lang="en")

    @staticmethod
    def _value(by_id: pd.DataFrame, field: str, year):
        """Look up one item_id's value for a year column; NaN when absent."""
        if field not in by_id.index:
            return float("nan")
        cell = by_id.loc[field, year]
        if isinstance(cell, pd.Series):  # duplicate item_id rows: take the first
            cell = cell.iloc[0]
        return pd.to_numeric(cell, errors="coerce")

    @staticmethod
    def _bare(symbol: str) -> str:
        """Upper-case ticker without a trailing ``.VN`` suffix."""
        s = str(symbol).strip().upper()
        return s[:-3] if s.endswith(".VN") else s
