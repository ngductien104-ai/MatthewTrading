"""Where the Atlas stands and what to learn next.

Run from ``agent/``:  python -m src.atlas.status
"""
from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

from src.atlas.schema import ATLAS_DIR, check, gics_codes, load_notes

_QUEUE_ROW = re.compile(
    r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(cho|dang|xong)\s*\|\s*([^|]*?)\s*\|",
    re.M,
)


def queue(atlas_dir: Path = ATLAS_DIR) -> list[dict]:
    """Rows of the priority table in HANG_DOI.md, in order."""
    text = (atlas_dir / "_HeThong" / "HANG_DOI.md").read_text(encoding="utf-8")
    keys = ("tt", "loai", "ten", "cap_dich", "trang_thai", "ghi_chu")
    return [dict(zip(keys, row)) for row in _QUEUE_ROW.findall(text)]


def coverage(atlas_dir: Path = ATLAS_DIR) -> dict[str, str]:
    """GICS industry code -> depth level reached (only industries that have a note)."""
    return {
        str(fm["gics"]): str(fm.get("cap_do"))
        for _, fm in load_notes(atlas_dir)
        if fm["loai_ghi_chu"] == "nganh" and fm.get("gics") is not None
    }


def next_item(atlas_dir: Path = ATLAS_DIR) -> str:
    """The next thing to learn: first open queue row, else next GICS industry."""
    for row in queue(atlas_dir):
        if row["trang_thai"] != "xong":
            return f"[{row['trang_thai']}] {row['loai']} · {row['ten']} · {row['cap_dich']} — {row['ghi_chu']}"
    codes, done = gics_codes(atlas_dir), coverage(atlas_dir)
    for level, reached in (("L1", ("L1", "L2")), ("L2", ("L2",))):
        for code, name in codes.items():
            if done.get(code) not in reached:
                return f"[GICS] nganh · {code} {name} · {level}"
    return "Hết hàng đợi — chuyển sang bảo trì theo han_xem_lai."


def overdue(atlas_dir: Path = ATLAS_DIR, today: date | None = None) -> list[str]:
    """Notes whose ``han_xem_lai`` has passed."""
    today = today or date.today()
    late = []
    for path, fm in load_notes(atlas_dir):
        due = fm.get("han_xem_lai")
        if due is None:
            continue
        due = due if isinstance(due, date) else date.fromisoformat(str(due))
        if due < today:
            late.append(f"{path.stem} (hạn {due.isoformat()})")
    return late


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    notes = load_notes()
    codes, done = gics_codes(), coverage()
    companies = [fm for _, fm in notes if fm["loai_ghi_chu"] == "doanh_nghiep"]
    by_level = {lv: sum(1 for fm in companies if fm.get("cap_do") == lv) for lv in ("L1", "L2", "L3")}
    errors, warnings = check()
    late = overdue()

    print("ATLAS — trạng thái")
    print(f"  Ngành: {len(done)}/{len(codes)} có thẻ · L2: {sum(1 for v in done.values() if v == 'L2')}")
    print(f"  Doanh nghiệp: {len(companies)} thẻ (L1 {by_level['L1']} · L2 {by_level['L2']} · L3 {by_level['L3']})")
    print(f"  Nguồn đã đọc: {sum(1 for _, fm in notes if fm['loai_ghi_chu'] == 'nguon')}")
    print(f"  Schema: {len(errors)} lỗi · {len(warnings)} cảnh báo")
    print(f"  Quá hạn xem lại: {len(late)}" + (" — " + ", ".join(late[:10]) if late else ""))
    print(f"  KẾ TIẾP: {next_item()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
