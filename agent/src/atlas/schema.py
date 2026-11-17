"""Validate the frontmatter of Atlas notes against KIEN_TRUC.md.

Run from ``agent/``:  python -m src.atlas.schema
Exit code 1 when any error is found; warnings do not fail the run.
"""
from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

import yaml

ATLAS_DIR = Path(__file__).resolve().parents[3] / "Obsidian" / "MatthewObsidian" / "25_Atlas"

RELATION_FIELDS = ("mua_tu", "ban_cho", "doi_thu_cung", "doi_thu_tren", "doi_thu_duoi")
_GICS_ROW = re.compile(r"^\|\s*(\d{6})\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", re.M)
_ISO2 = re.compile(r"^[A-Z]{2}$")


def read_frontmatter(path: Path) -> dict | None:
    """Return the YAML frontmatter of a note, or None when it has none."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    data = yaml.safe_load(parts[1])
    return data if isinstance(data, dict) else None


def gics_codes(atlas_dir: Path = ATLAS_DIR) -> dict[str, str]:
    """Map 6-digit GICS industry code -> Vietnamese name, read from GICS.md."""
    text = (atlas_dir / "_HeThong" / "GICS.md").read_text(encoding="utf-8")
    return {code: vn for code, _en, vn in _GICS_ROW.findall(text)}


def load_notes(atlas_dir: Path = ATLAS_DIR) -> list[tuple[Path, dict]]:
    """Every typed note (one carrying ``loai_ghi_chu``) outside _HeThong."""
    notes = []
    for path in sorted(atlas_dir.rglob("*.md")):
        if "_HeThong" in path.parts:
            continue
        fm = read_frontmatter(path)
        if fm and fm.get("loai_ghi_chu"):
            notes.append((path, fm))
    return notes


def _is_date(value) -> bool:
    if isinstance(value, date):
        return True
    try:
        date.fromisoformat(str(value))
        return True
    except ValueError:
        return False


def _filled_list(value) -> bool:
    return isinstance(value, list) and len(value) > 0


def check(atlas_dir: Path = ATLAS_DIR) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for the whole Atlas."""
    errors: list[str] = []
    warnings: list[str] = []
    codes = gics_codes(atlas_dir)
    notes = load_notes(atlas_dir)
    industries = {str(fm.get("gics")): fm for _, fm in notes if fm["loai_ghi_chu"] == "nganh"}
    companies = {p.stem for p, fm in notes if fm["loai_ghi_chu"] == "doanh_nghiep"}

    for path, fm in notes:
        name = path.relative_to(atlas_dir).as_posix()
        kind = fm["loai_ghi_chu"]

        def err(msg: str) -> None:
            errors.append(f"{name}: {msg}")

        def require(*fields: str) -> None:
            for field in fields:
                if fm.get(field) in (None, "", []):
                    err(f"thiếu `{field}`")

        def dates() -> None:
            for field in ("cap_nhat", "han_xem_lai"):
                if fm.get(field) is not None and not _is_date(fm[field]):
                    err(f"`{field}` không phải ngày YYYY-MM-DD")

        if kind == "nganh":
            require("ten", "gics", "cap_do", "mat_xich", "quoc_gia_chu_chot", "cap_nhat", "han_xem_lai")
            dates()
            if fm.get("gics") is not None and str(fm["gics"]) not in codes:
                err(f"mã GICS {fm['gics']} không có trong GICS.md")
            if fm.get("cap_do") not in (None, "L1", "L2"):
                err("`cap_do` của ngành phải là L1 hoặc L2")
            for country in fm.get("quoc_gia_chu_chot") or []:
                if not _ISO2.match(str(country)):
                    err(f"mã quốc gia `{country}` không phải ISO alpha-2")
            if fm.get("quy_mo_thi_truong") is not None:
                require("nam_quy_mo", "don_vi_tien")
                if not _filled_list(fm.get("nguon")):
                    err("có `quy_mo_thi_truong` nhưng `nguon` rỗng")

        elif kind == "doanh_nghiep":
            require("ten", "quoc_gia", "loai", "nganh_gics", "mat_xich", "cap_do", "cap_nhat", "han_xem_lai")
            dates()
            if fm.get("quoc_gia") and not _ISO2.match(str(fm["quoc_gia"])):
                err(f"mã quốc gia `{fm['quoc_gia']}` không phải ISO alpha-2")
            if fm.get("loai") not in (None, "dai_chung", "tu_nhan", "nha_nuoc"):
                err("`loai` phải là dai_chung / tu_nhan / nha_nuoc")
            if fm.get("cap_do") not in (None, "L1", "L2", "L3"):
                err("`cap_do` phải là L1 / L2 / L3")
            gics = str(fm.get("nganh_gics")) if fm.get("nganh_gics") is not None else None
            if gics and gics not in codes:
                err(f"mã GICS {gics} không có trong GICS.md")
            elif gics and gics not in industries:
                warnings.append(f"{name}: ngành {gics} chưa có ghi chú _MOC")
            elif gics:
                allowed = industries[gics].get("mat_xich") or []
                for link in fm.get("mat_xich") or []:
                    if link not in allowed:
                        err(f"mắt xích `{link}` không có trong `mat_xich` của ngành {gics}")
            if fm.get("doanh_thu") is not None or fm.get("von_hoa") is not None:
                require("nam_tai_chinh", "don_vi_tien")
                if not _filled_list(fm.get("nguon")):
                    err("có số tài chính nhưng `nguon` rỗng")
            for field in RELATION_FIELDS:
                for target in fm.get(field) or []:
                    if target not in companies:
                        warnings.append(f"{name}: `{field}` trỏ tới `{target}` — cần tạo thẻ")

        elif kind == "nguon":
            require("ten", "to_chuc", "loai_tai_lieu", "nam")

        else:
            err(f"`loai_ghi_chu: {kind}` không hợp lệ")

    return errors, warnings


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    errors, warnings = check()
    for line in warnings:
        print(f"CẢNH BÁO  {line}")
    for line in errors:
        print(f"LỖI       {line}")
    print(f"{len(load_notes())} ghi chú · {len(errors)} lỗi · {len(warnings)} cảnh báo")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
