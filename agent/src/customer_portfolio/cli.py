"""Claude/Codex-compatible CLI for privacy-safe local portfolio lookup."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from src.customer_portfolio.excel_repository import ExcelPortfolioRepository, PortfolioLookupError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Resolve masked/encrypted customer references to a de-identified portfolio snapshot."
    )
    parser.add_argument("--customer-token", default=os.getenv("CUSTOMER_LOOKUP_TOKEN", ""))
    parser.add_argument("--account-token", default=os.getenv("ACCOUNT_LOOKUP_TOKEN", ""))
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(os.getenv("CUSTOMER_EXCEL_DB_DIR", Path(__file__).resolve().parents[3] / "Database")),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.account_token:
        print(json.dumps({"status": "error", "error": "--account-token is required"}))
        return 2
    try:
        snapshot = ExcelPortfolioRepository(args.database).lookup(
            account_token=args.account_token,
            customer_token=args.customer_token or None,
        )
    except PortfolioLookupError as exc:
        # Lookup errors never contain the confidential token values.
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "snapshot": snapshot}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
