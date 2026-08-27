"""Unit / sign normalisation for ``vnstock_data`` fundamental tables.

Why this module exists
----------------------
The sponsored ``vnstock_data`` ratio table ships several fields whose declared
``unit`` column contradicts the value actually stored. Reading them literally
produces analysis that is wrong by three orders of magnitude, or that reports a
128% NPL coverage ratio as -1.28. Every trap below was verified against live
HPG (industrial) and TCB (bank) FY2025 data on 2026-08-27:

===========================  =============  =====================  ============
Field                        Declared unit  Stored value           Truth
===========================  =============  =====================  ============
RT_VALUE_MARKET_CAP          tỷ VNĐ         2.152968e+14 (HPG)     plain VND
RT_VALUE_EBIT / EBITDA       tỷ VNĐ         2.042762e+13 (HPG)     plain VND
RT_PRT_* / RT_BANK_*         %              0.1269 = ROE 12.69%    fraction
RT_VALUE_DIVIDEND_YIELD      %              2.2676 = 2.27%         already %
RT_BANK_COF/CIR/NPL_COVER..  %              -1.2805 (TCB)          sign lost
RT_VALUE_EQUITY              tỷ VNĐ         0.209 (HPG) / 0 (TCB)  broken
RT_BANK_NOII                 tỷ VNĐ         0.398 (TCB)            broken
RT_LEV_EQUITY_TO_ASSETS      lần            0.1505 (TCB)           ratio -> %
RT_LEV_EQUITY_TO_LIABILITIES lần            0.1772 (TCB)           ratio -> %
===========================  =============  =====================  ============

The two ``RT_LEV_EQUITY_TO_*`` fields are the odd case: the stored number is
*correct* and the ``lần`` label is *honest* — 0.1505 really is equity/assets as
a ratio, and it reconciles to the cent against the balance sheet for all eight
TCB years. They are converted anyway, because their sibling
``RT_BANK_EQUITY_TO_LOANS`` is served as a percent, and a wide table that puts
``0.15`` beside ``23.38`` for two ratios of the same shape invites a misread.
Genuine multiples — ``RT_LEV_DE``, ``RT_LEV_FINANCIAL_LEVERAGE``,
``RT_LQD_CR``, the ``RT_VALUE_P*`` block — keep ``lần``, because a debt/equity
of 0.97x is quoted as a multiple and always has been.

The ``RT_VALUE_P*`` valuation block carries a different hazard, and one this
module deliberately does **not** "fix". Its numbers disagree with a market cap
rebuilt from DataPro's year-end close for most historical years (TCB FY2023:
stored P/B 0.67 against 0.79 rebuilt; the stored market cap implies a 47,400đ
share price TCB never traded at that December). The stored *latest* year does
reconcile — TCB FY2025 P/B 1.39 against 1.35 rebuilt, P/E 9.37 against 9.58 —
and no reconstruction available here is trustworthy enough to overwrite the
history with, because DataPro's close is back-adjusted and understates older
market caps by the cash dividends paid since. So the values pass through
untouched and the row is stamped instead: quote the newest period, treat the
series as indicative, and rebuild from price x shares when a historical
multiple has to carry weight.

Two further conventions apply across the whole table:

* ``0.0`` in a ratio row means "not applicable to this company type" — banks
  report 0.0 for inventory turnover, industrials report 0.0 for NIM. It is not
  a measured zero, so it becomes ``NaN``.
* ``period`` arrives as an *unordered* pandas Categorical, which makes
  ``.max()`` raise. It is cast to ``str`` so ordinary sorting works.

``NaN`` is never filled with zero. A missing number stays missing.
"""

from __future__ import annotations

import pandas as pd

# Ratio ids whose stored number is meaningless. The value is dropped and the
# caller is pointed at the field that does carry the truth.
BROKEN_RATIO_IDS: dict[str, str] = {
    "RT_VALUE_EQUITY": "balance_sheet:BS_EQUITY",
    "RT_BANK_NOII": "income_statement:IS_TOTAL_OPERATING_INCOME - IS_NET_INTEREST_INCOME",
}

# Declared "%" but the number is already expressed in percent, so it must NOT
# be multiplied by 100 like its neighbours.
RATIO_ALREADY_PERCENT: frozenset[str] = frozenset({"RT_VALUE_DIVIDEND_YIELD"})

# Stored as a true ratio under a ``lần`` label, but conventionally read as a
# percent — and their siblings in the RT_BANK_* block already arrive as one.
# Only fields of that shape belong here, never a genuine multiple like D/E.
RATIO_QUOTED_IN_PERCENT: frozenset[str] = frozenset({
    "RT_LEV_EQUITY_TO_ASSETS",
    "RT_LEV_EQUITY_TO_LIABILITIES",
})

# Valuation multiples whose history does not reconcile against a market cap
# rebuilt from DataPro prices. The value is left alone; only a note is added.
RATIO_UNRELIABLE_HISTORY: frozenset[str] = frozenset({
    "RT_VALUE_PE",
    "RT_VALUE_PB",
    "RT_VALUE_PS",
    "RT_VALUE_P_CF",
})

# Cost/coverage ratios stored with a flipped sign (a cost is booked negative).
# Magnitude is the meaningful quantity.
RATIO_ABS_IDS: frozenset[str] = frozenset({
    "RT_BANK_COF",
    "RT_BANK_CIR",
    "RT_BANK_NPL_COVERAGE",
    "RT_BANK_PROVISION_TO_LOANS",
})

# Declared unit for money columns in the ratio table. The stored number is
# plain VND despite the label.
_MONEY_UNIT = "tỷ VNĐ"

# Section-header rows carry no value.
_CATEGORY_PREFIX = "RT_CAT_"


def normalize_ratio(df: pd.DataFrame) -> pd.DataFrame:
    """Return *df* (a raw ``Fundamental().equity(x).ratio()`` frame) normalised.

    Adds three columns and leaves the originals untouched so a caller can
    always audit what was changed:

    * ``value`` — the corrected number.
    * ``unit`` — the unit ``value`` is actually expressed in
      (``%``, ``VND``, or the original label when nothing moved).
    * ``note`` — why the row was altered; empty when it was not.

    Section-header rows (``RT_CAT_*``) are dropped.

    Raises:
        ValueError: If *df* lacks the expected long-format columns.
    """
    required = {"period", "id", "unit", "value"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"not a vnstock_data ratio frame; missing columns: {sorted(missing)}")

    out = df.copy()
    out["period"] = out["period"].astype(str)
    out = out[~out["id"].astype(str).str.startswith(_CATEGORY_PREFIX)].copy()

    out = out.rename(columns={"value": "value_raw", "unit": "unit_raw"})
    # ``unit_raw`` and ``id`` arrive as Categoricals; assigning a new label to a
    # Categorical raises, so both are widened to plain strings first.
    out["unit_raw"] = out["unit_raw"].astype(str)
    out["id"] = out["id"].astype(str)
    out["value"] = pd.to_numeric(out["value_raw"], errors="coerce")
    out["unit"] = out["unit_raw"]
    out["note"] = ""

    ids = out["id"].astype(str)

    # 0.0 is the "not applicable" sentinel, not a measurement.
    not_applicable = out["value"] == 0.0
    out.loc[not_applicable, "note"] = "0.0 treated as not-applicable"
    out.loc[not_applicable, "value"] = float("nan")

    # Structurally broken fields.
    broken = ids.isin(BROKEN_RATIO_IDS)
    for bad_id, replacement in BROKEN_RATIO_IDS.items():
        mask = ids == bad_id
        out.loc[mask, "note"] = f"field is broken upstream; use {replacement}"
    out.loc[broken, "value"] = float("nan")

    # Fractions declared as percent.
    frac = (out["unit_raw"] == "%") & ~ids.isin(RATIO_ALREADY_PERCENT) & ~broken
    out.loc[frac, "value"] = out.loc[frac, "value"] * 100.0
    out.loc[frac & out["note"].eq(""), "note"] = "fraction scaled to percent"

    # Sign-flipped cost ratios.
    flip = ids.isin(RATIO_ABS_IDS) & ~broken
    out.loc[flip, "value"] = out.loc[flip, "value"].abs()
    out.loc[flip & out["note"].eq(""), "note"] = "sign dropped (cost stored negative)"

    # True ratios under a ``lần`` label that are read as percentages.
    as_pct = ids.isin(RATIO_QUOTED_IN_PERCENT) & ~broken
    out.loc[as_pct, "value"] = out.loc[as_pct, "value"] * 100.0
    out.loc[as_pct, "unit"] = "%"
    out.loc[as_pct & out["note"].eq(""), "note"] = "ratio scaled to percent for consistency"

    # Valuation multiples: value untouched, reader warned.
    shaky = ids.isin(RATIO_UNRELIABLE_HISTORY) & ~broken
    out.loc[shaky & out["note"].eq(""), "note"] = (
        "history does not reconcile against DataPro market cap; trust the latest period only"
    )

    # Money columns mislabelled as billions.
    money = (out["unit_raw"] == _MONEY_UNIT) & ~broken
    out.loc[money, "unit"] = "VND"
    out.loc[money & out["note"].eq(""), "note"] = "label says tỷ VNĐ; value is plain VND"

    return out.reset_index(drop=True)


def normalize_statement(df: pd.DataFrame) -> pd.DataFrame:
    """Return a raw income/balance/cash-flow frame with ``period`` made sortable.

    Statement values are already plain VND and are left alone — the only
    change is the Categorical ``period`` cast and dropping ``0.0`` for the
    diluted-EPS field, which is a not-reported sentinel rather than a zero.

    Raises:
        ValueError: If *df* lacks the expected long-format columns.
    """
    required = {"period", "id", "value"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"not a vnstock_data statement frame; missing columns: {sorted(missing)}")

    out = df.copy()
    out["period"] = out["period"].astype(str)
    out["value"] = pd.to_numeric(out["value"], errors="coerce")

    sentinel_zero = (out["id"].astype(str) == "IS_DILUTED_EARNINGS_PER_SHARE") & (out["value"] == 0.0)
    out.loc[sentinel_zero, "value"] = float("nan")
    return out.reset_index(drop=True)


def pivot(df: pd.DataFrame, value_col: str = "value") -> pd.DataFrame:
    """Pivot a normalised long frame to ``period`` rows x ``id`` columns.

    Periods sort ascending as strings, which is correct for both ``2025`` and
    ``2025-Q3`` labels.
    """
    wide = df.pivot_table(index="period", columns="id", values=value_col, aggfunc="last")
    return wide.sort_index()
