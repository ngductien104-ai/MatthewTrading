"""Strict Excel bridge: preserve unknowns and expose dates for each export."""
from __future__ import annotations

import math
import os
from pathlib import Path

from src.customer_portfolio.excel_repository import (
    ExcelPortfolioRepository, _latest_files, _read_rows, _matching_rows, _date_from_filename,
)


def optional_number(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        result = float(str(value).replace(",", "").replace(" ", ""))
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def read_portfolio(settings):
    if not settings.excel_directory or not os.getenv(settings.account_env):
        return {"status": "not_configured", "positions": []}
    account = os.environ[settings.account_env]
    customer = os.getenv(settings.customer_env) or None
    root = Path(settings.excel_directory)
    files = _latest_files(root)
    # Reuse the account resolution/fingerprint, but do not propagate its missing->0 coercion.
    existing = ExcelPortfolioRepository(root).lookup(account_token=account, customer_token=customer)
    nav_rows = _matching_rows(_read_rows(files["nav"]), account, customer)
    nav = optional_number(nav_rows[0].get("nav cuối kỳ")) if nav_rows else None
    positions = []
    for row in _matching_rows(_read_rows(files["portfolio"]), account, customer):
        value = optional_number(row.get("giá trị thị trường"))
        positions.append({"symbol": str(row.get("mã chứng khoán") or "").strip(),
                          "market_value": value,
                          "weight_of_nav": value / nav if value is not None and nav and nav > 0 else None})
    dates = {kind: _date_from_filename(path).date().isoformat() for kind, path in files.items()}
    return {"status": "available", "portfolio_ref": existing["portfolio_ref"], "nav": nav,
            "as_of": min(dates.values()), "source_dates": dates, "positions": positions,
            "limitations": (["Export dates differ"] if len(set(dates.values())) > 1 else [])
                            + (["NAV unavailable"] if nav is None else [])}
