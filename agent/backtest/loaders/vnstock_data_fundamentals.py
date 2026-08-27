"""vnstock_data (sponsor) fundamental-statement provider with PIT safeguards.

Sponsor-tier counterpart to ``vnstock_fundamentals``. Exposes the identical
provider contract — ``list_tables`` / ``describe_table`` / ``query_fundamentals``
— so ``enrich_price_frames_with_fundamentals`` can swap one for the other, and
so existing backtest configs keep asking for the same logical field names.

Why this exists next to the free provider
-----------------------------------------
The free KBS feed returns a wide frame whose ``item_id`` keys are auto-generated
from Vietnamese VAS labels, which forces two ugly workarounds: section headers
arrive as data rows carrying NaN, and ``item_id`` collides (``revenue`` appears
once gross and once net). ``vnstock_data`` instead returns a tidy long frame —
``period, id, name, order, level, unit, value`` — whose ``id`` is a **stable
English code** (``IS_NET_REVENUE``, ``BS_TOTAL_ASSETS``, ``RT_VALUE_PE``) and is
**unique within a period**, verified across income / balance / cashflow / ratio
for HPG. So no header-skipping and no last-non-null tie-breaking here.

Three further gains over the free tier:

* **8 annual periods** instead of ~4, and **34 quarters** back to 2018-Q1, so
  long backtests stop running out of fundamentals.
* **``ratio()`` is current.** The community ratio endpoint returns a stale
  layout (2018-era figures); the sponsor one returns live P/E, P/B, ROE, and
  margins, which is why ``ratio`` is a first-class table here.
* **Bank / securities schemas** are auto-detected (``com_type``), so a bank
  returns ``IS_NET_INTEREST_INCOME`` rather than an empty industrial template.

Point-in-time model
-------------------
The feed still carries no filing date, so one is synthesised: a period only
becomes visible ``_DISCLOSURE_LAG_DAYS[period_kind]`` after period end, and
``merge_asof`` then attaches it only to bars on/after that date — no lookahead.
Annual uses 90 days (audited annual reports are due within 90); quarterly uses
45, which clears the 30-day consolidated-filing deadline with a buffer.

Known data traps (verified by value on HPG 2025, not inferred from labels)
--------------------------------------------------------------------------
* ``RT_PRT_*`` / ``RT_BANK_*`` ratios are **fractions** even though ``unit``
  says ``%`` (ROE 0.1269 = 12.69%), and the cost ratios (``RT_BANK_COF``,
  ``CIR``, ``NPL_COVERAGE``, ``PROVISION_TO_LOANS``) additionally arrive
  sign-flipped. This provider now corrects both on the way out, using the one
  shared spec in :mod:`vndata.normalize`, so **ratio fields are returned in
  percent** — ``ratio_roe`` is ``12.69``, not ``0.1269``. A stored ``0.0`` is
  the "not applicable" sentinel and comes back as ``NaN``.
* ``RT_VALUE_MARKET_CAP`` is in **đồng**, not the ``tỷ VNĐ`` its unit claims
  (HPG 2.153e14 = 215,297 tỷ ✓ against 7.675bn shares × ~28,050đ).
* ``RT_VALUE_EQUITY`` is corrupt (HPG returns 0.209). Read equity from
  ``BS_EQUITY`` instead — that one reconciles: 126,679 + 131,220 = 257,899 tỷ.
* Occasional line-level gaps remain (HPG 2025 ``CF_NET_CASH_FLOWS_FROM_
  FINANCING_ACTIVITIES`` is NaN). NaN is passed through as NaN — never zeroed.
* ``IS_MINORITY_INTEREST`` **loses its minus sign when the minority share is a
  loss**. Checked across HPG/NLG/PET/VRE 2018-2025: every positive-minority year
  reconciles exactly, while HPG 2022/2023/2024 (minority negative) comes back
  unsigned. So never sum ``attributable_to_parent_company + minority_interest``
  blind — derive the residual instead:
  ``minority = net_profit_loss_after_tax - attributable_to_parent_company``,
  and treat a sign disagreement as the API's, not the statement's.
"""

from __future__ import annotations

import contextlib
import io
import os
import re
from typing import Iterable

import pandas as pd

# Reuse the schema/error vocabulary so the providers stay interchangeable.
from backtest.loaders.tushare_fundamentals import (
    DataProviderError,
    TableSchema,
    UnknownTableError,
)

# Days after period end before a report is treated as public.
_DISCLOSURE_LAG_DAYS = {"year": 90, "quarter": 45}

# Logical table name -> Unified UI ``Fundamental.equity`` method.
_TABLE_METHODS = {
    "income": "income_statement",
    "balancesheet": "balance_sheet",
    "cashflow": "cash_flow",
    "ratio": "ratio",
}

# Logical field name -> vnstock_data ``id``. Keys mirror the free provider's
# vocabulary so a config written against ``vnstock`` runs unchanged here. Any
# field missing from this map is looked up as a raw ``id``, which is how the
# remaining ~100 detail lines per statement stay reachable.
_FIELD_ALIASES = {
    # ── Kết quả kinh doanh ──
    "revenue": "IS_REVENUE",                         # doanh thu gộp
    "net_sales": "IS_NET_REVENUE",                   # doanh thu THUẦN
    "cost_of_sales": "IS_COST_OF_GOODS_SOLD",
    "gross_profit": "IS_GROSS_PROFIT",
    "financial_income": "IS_FINANCIAL_INCOME",
    "financial_expenses": "IS_FINANCIAL_EXPENSES",
    "interest_expenses": "IS_INTEREST_EXPENSES",
    "selling_expenses": "IS_SELLING_EXPENSES",
    "general_and_admin_expenses": "IS_GENERAL_AND_ADMINISTRATIVE_EXPENSES",
    "operating_profit": "IS_OPERATING_PROFIT",
    "profit_before_tax": "IS_PROFIT_BEFORE_TAX",
    "income_tax": "IS_CORPORATE_INCOME_TAX_EXPENSES",
    "net_profit_loss_after_tax": "IS_NET_PROFIT_AFTER_TAX",
    "minority_interest": "IS_MINORITY_INTEREST",
    "attributable_to_parent_company": "IS_PROFIT_AFTER_TAX_FOR_SHAREHOLDERS_OF_PARENT_COMPANY",
    # ── Cân đối kế toán ──
    "total_assets": "BS_TOTAL_ASSETS",
    "current_assets": "BS_SHORT_TERM_ASSETS",
    "long_term_assets": "BS_LONG_TERM_ASSETS",
    "cash_and_cash_equivalents": "BS_CASH_AND_PRECIOUS_METALS",
    "short_term_investments": "BS_SHORT_TERM_INVESTMENTS",
    "accounts_receivable": "BS_SHORT_TERM_RECEIVABLES",
    "inventories_net": "BS_INVENTORIES",             # tồn kho THUẦN (đã trừ dự phòng)
    "liabilities": "BS_TOTAL_LIABILITIES",
    "current_liabilities": "BS_SHORT_TERM_LIABILITIES",
    "long_term_liabilities": "BS_LONG_TERM_LIABILITIES",
    "short_term_borrowings": "BS_SHORT_TERM_BORROWINGS",
    "long_term_borrowings": "BS_LONG_TERM_BORROWINGS",
    "owners_equity": "BS_EQUITY",                    # KHÔNG dùng RT_VALUE_EQUITY (hỏng)
    "goodwill": "BS_GOODWILL",
    "construction_in_progress": "BS_CONSTRUCTION_IN_PROGRESS",
    # ── Lưu chuyển tiền tệ ──
    "net_cash_inflows_outflows_from_operating_activities": "CF_NET_CASH_FLOWS_FROM_OPERATING_ACTIVITIES",
    "net_cash_inflows_outflows_from_investing_activities": "CF_NET_CASH_FLOWS_FROM_INVESTING_ACTIVITIES",
    "net_cash_inflows_outflows_from_financing_activities": "CF_NET_CASH_FLOWS_FROM_FINANCING_ACTIVITIES",
    "depreciation_and_amortisation": "CF_DEPRECIATION_AND_AMORTISATION",
    # ── Chỉ số (sponsor-only: bản community trả số 2018 lỗi thời) ──
    "pe": "RT_VALUE_PE",
    "pb": "RT_VALUE_PB",
    "ps": "RT_VALUE_PS",
    "ev_ebitda": "RT_VALUE_EV_EBITDA",
    "dividend_yield": "RT_VALUE_DIVIDEND_YIELD",
    "market_cap": "RT_VALUE_MARKET_CAP",             # đơn vị ĐỒNG, không phải tỷ
    "outstanding_shares": "RT_VALUE_OUTSTANDING_SHARES",
    "ebit": "RT_VALUE_EBIT",
    "ebitda": "RT_VALUE_EBITDA",
    "roe": "RT_PRT_ROE",                             # phân số, không phải %
    "roa": "RT_PRT_ROA",
    "roic": "RT_PRT_ROIC",
    "gross_margin": "RT_PRT_GROSS_MARGIN",
    "net_margin": "RT_PRT_NET_MARGIN",
}

def _correct(field_id: str, value: float) -> float:
    """Apply the one shared unit/sign correction to a raw ``vnstock_data`` value.

    The spec lives in :mod:`vndata.normalize` so the backtest provider and every
    analysis path agree on what ``ratio_roe`` means. Before this, the provider
    returned raw fractions while the screening skills compared them against
    percent thresholds, so ``ROE >= 8`` matched nothing.

    Ratios come back **in percent**; a stored ``0.0`` becomes ``NaN`` because it
    is the "not applicable" sentinel, not a measurement.
    """
    try:
        from vndata.normalize import (
            BROKEN_RATIO_IDS,
            RATIO_ABS_IDS,
            RATIO_ALREADY_PERCENT,
        )
    except Exception:  # noqa: BLE001 - provider must still work standalone
        return value

    if not isinstance(field_id, str) or not field_id.startswith("RT_"):
        return value
    if pd.isna(value):
        return value
    if field_id in BROKEN_RATIO_IDS:
        return float("nan")
    if value == 0.0:
        return float("nan")
    if field_id in RATIO_ABS_IDS:
        return abs(value) * 100.0
    if field_id.startswith(("RT_PRT_", "RT_BANK_")) and field_id not in RATIO_ALREADY_PERCENT:
        return value * 100.0
    return value


_SCHEMAS = {
    table: TableSchema(
        name=table,
        api_name=method,
        point_in_time_column="ann_date",
        columns=(),
    )
    for table, method in _TABLE_METHODS.items()
}

# ``2025`` (annual) or ``2026-Q2`` (quarterly).
_PERIOD_RE = re.compile(r"^(\d{4})(?:-Q([1-4]))?$")


class VNStockDataFundamentalProvider:
    """Provider over vnstock_data annual/quarterly statements and ratios."""

    def __init__(self, period: str = "year") -> None:
        """Args: period: ``year`` or ``quarter`` — the reporting frequency."""
        self.period = "quarter" if str(period).lower().startswith("q") else "year"
        self._fundamental_cls = self._import_fundamental()

    @staticmethod
    def _import_fundamental():
        """Import the Unified UI ``Fundamental``, swallowing its stdout banner.

        The banner would otherwise corrupt the runner's JSON stdout envelope.
        """
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            from vnstock_data import Fundamental
        return Fundamental

    def list_tables(self) -> list[str]:
        """Return supported statement tables in stable order."""
        return sorted(_SCHEMAS)

    def describe_table(self, table: str) -> TableSchema:
        """Return schema metadata for a supported table."""
        try:
            return _SCHEMAS[table]
        except KeyError as exc:
            raise UnknownTableError(f"Unsupported vnstock_data fundamental table: {table}") from exc

    def query_fundamentals(
        self,
        table: str,
        codes: Iterable[str],
        *,
        as_of: str | pd.Timestamp,
        periods: Iterable[str] | None = None,
        fields: Iterable[str] | None = None,
    ) -> pd.DataFrame:
        """Return a long PIT frame: ts_code, end_date, ann_date + requested fields.

        Args:
            table: One of ``income`` / ``balancesheet`` / ``cashflow`` / ``ratio``.
            codes: Symbols, bare or ``.VN``-suffixed.
            as_of: Backtest cut-off; periods disclosed after it are dropped.
            periods: Optional period filter (``"2025"`` or ``"2026-Q2"``).
            fields: Logical names (see ``_FIELD_ALIASES``) or raw ``id`` codes.
        """
        schema = self.describe_table(table)
        method_name = schema.api_name
        field_list = list(fields or [])
        requested_periods = {str(p) for p in (periods or [])}
        as_of_ts = pd.Timestamp(as_of).normalize() if as_of else None

        records: list[dict] = []
        for original in codes:
            symbol = self._bare(original)
            try:
                statement = self._fetch_statement(symbol, method_name)
            except Exception as exc:  # noqa: BLE001 - one bad symbol must not abort
                print(f"[WARN] vnstock_data {table} for {symbol} failed: {exc}")
                continue
            if statement is None or statement.empty or "id" not in statement.columns:
                continue

            # id is unique per period, so a single pivot replaces per-field lookups.
            # ``period`` arrives as a pandas Categorical; cast to str first so the
            # pivot keeps a plain index instead of reinstating every unused level.
            statement = statement.assign(period=statement["period"].astype(str))
            wide = statement.pivot_table(
                index="period", columns="id", values="value", aggfunc="last"
            )
            for period_label in wide.index:
                label = str(period_label)
                if requested_periods and label not in requested_periods:
                    continue
                ann_date = self._ann_date(label)
                if ann_date is None:
                    continue
                if as_of_ts is not None and ann_date > as_of_ts:
                    continue  # not yet disclosed as-of the backtest cut-off
                row: dict = {
                    "ts_code": original,
                    "end_date": label,
                    "ann_date": ann_date,
                }
                for field in field_list:
                    key = _FIELD_ALIASES.get(field, field)
                    value = wide.at[period_label, key] if key in wide.columns else float("nan")
                    row[field] = _correct(key, pd.to_numeric(value, errors="coerce"))
                records.append(row)

        if not records:
            return pd.DataFrame(columns=["ts_code", "end_date", "ann_date", *field_list])

        result = pd.DataFrame.from_records(records)
        return result.sort_values(["ts_code", "end_date"]).reset_index(drop=True)

    # ── internals ──

    def _fetch_statement(self, symbol: str, method_name: str) -> pd.DataFrame | None:
        """Call one Unified UI statement method for a symbol (stdout suppressed).

        ``com_type`` is left at its default so the library picks the industrial /
        bank / securities schema from the symbol itself.
        """
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            equity = self._fundamental_cls().equity(symbol)
            method = getattr(equity, method_name, None)
            if method is None:
                raise DataProviderError(f"vnstock_data Fundamental has no method: {method_name}")
            return method(period=self.period)

    def _ann_date(self, period_label: str) -> pd.Timestamp | None:
        """Synthesised disclosure date = period end + tier-appropriate lag."""
        match = _PERIOD_RE.match(period_label)
        if not match:
            return None
        year, quarter = match.group(1), match.group(2)
        if quarter:
            end_month = int(quarter) * 3
            period_end = pd.Timestamp(year=int(year), month=end_month, day=1) + pd.offsets.MonthEnd(0)
            lag = _DISCLOSURE_LAG_DAYS["quarter"]
        else:
            period_end = pd.Timestamp(f"{year}-12-31")
            lag = _DISCLOSURE_LAG_DAYS["year"]
        return period_end + pd.Timedelta(days=lag)

    @staticmethod
    def _bare(symbol: str) -> str:
        """Upper-case ticker without a trailing ``.VN`` suffix."""
        s = str(symbol).strip().upper()
        return s[:-3] if s.endswith(".VN") else s
