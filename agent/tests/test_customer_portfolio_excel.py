"""Tests for privacy-safe customer portfolio Excel lookup."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

from src.customer_portfolio.excel_repository import ExcelPortfolioRepository
from src.customer_portfolio.cli import main as cli_main
from src.tools.redaction import redact_payload
from src.tools.swarm_tool import _strip_lookup_tokens


ACCOUNT = "enc-account-very-secret"
CUSTOMER = "enc-customer-secret"


def _write_export(path: Path, headers: list[str], rows: list[list[object]]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    workbook.save(path)


def _database(tmp_path: Path) -> Path:
    root = tmp_path / "Database"
    root.mkdir()
    _write_export(
        root / "Portfolio_total_06082026.xlsx",
        ["Tài khoản", "Tên khách hàng", "Mã chứng khoán", "Chứng khoán giao dịch", "Giá thị trường", "Giá trị thị trường", "Giá vốn", "Giá trị vốn", "Lãi lỗ", "% lãi lỗ"],
        [[ACCOUNT, CUSTOMER, "FPT", 100, 100_000, 10_000_000, 90_000, 9_000_000, 1_000_000, 11.11]],
    )
    _write_export(
        root / "NAV_endperiod_total_06082026.xlsx",
        ["Tài khoản", "Tên khách hàng", "Tổng tiền mặt cơ sở cuối kỳ", "Giá trị chứng khoán cơ sở cuối kỳ", "Dư nợ cho vay cơ sở cuối kỳ", "NAV cuối kỳ"],
        [[ACCOUNT, CUSTOMER, 2_000_000, 10_000_000, 1_000_000, 11_000_000]],
    )
    _write_export(
        root / "Daily_report_total_06082026_06082026.xlsx",
        ["Tài khoản", "Tên khách hàng", "AUM cuối kỳ", "NAV cuối kỳ", "Dư nợ cho vay cuối kỳ", "Dư nợ quá hạn cuối kỳ"],
        [[ACCOUNT, CUSTOMER, 12_000_000, 11_000_000, 1_000_000, 0]],
    )
    _write_export(
        root / "TOI_total_06082026_06082026.xlsx",
        ["Tài khoản", "Tên khách hàng", "Tổng TOI"],
        [[ACCOUNT, CUSTOMER, 50_000]],
    )
    return root


def test_lookup_builds_snapshot_without_identity(tmp_path: Path) -> None:
    snapshot = ExcelPortfolioRepository(_database(tmp_path)).lookup(
        account_token=ACCOUNT, customer_token=CUSTOMER
    )

    rendered = str(snapshot)
    assert ACCOUNT not in rendered
    assert CUSTOMER not in rendered
    assert snapshot["nav"] == 11_000_000
    assert snapshot["margin_debt"] == 1_000_000
    assert snapshot["positions"][0]["symbol"] == "FPT"
    assert snapshot["positions"][0]["weight_of_nav"] == 10_000_000 / 11_000_000


def test_latest_snapshot_selected_and_lock_file_ignored(tmp_path: Path) -> None:
    root = _database(tmp_path)
    (root / "~$Portfolio_total_07082026.xls").write_bytes(b"lock")
    snapshot = ExcelPortfolioRepository(root).lookup(account_token=ACCOUNT)
    assert snapshot["as_of"] == "2026-08-06"


def test_lookup_tokens_are_redacted() -> None:
    assert redact_payload({
        "account_lookup_token": ACCOUNT,
        "customer_lookup_token": CUSTOMER,
        "account_ref": "safe-opaque-ref",
    }) == {
        "account_lookup_token": "[redacted]",
        "customer_lookup_token": "[redacted]",
        "account_ref": "safe-opaque-ref",
    }


def test_lookup_tokens_are_removed_from_persisted_prompt() -> None:
    prompt = f"Run risk committee for customer {CUSTOMER}, account {ACCOUNT}"
    sanitized = _strip_lookup_tokens(prompt, CUSTOMER, ACCOUNT)
    assert CUSTOMER not in sanitized
    assert ACCOUNT not in sanitized
    assert sanitized.count("[encrypted lookup supplied securely]") == 2


def test_cli_outputs_deidentified_snapshot(tmp_path: Path, capsys) -> None:
    rc = cli_main([
        "--database", str(_database(tmp_path)),
        "--customer-token", CUSTOMER,
        "--account-token", ACCOUNT,
    ])
    output = capsys.readouterr().out
    assert rc == 0
    assert '"status": "ok"' in output
    assert ACCOUNT not in output
    assert CUSTOMER not in output
    assert '"symbol": "FPT"' in output
