"""Loader hướng B — đọc file nhập tay FB/Zalo (tin_hieu_fb_zalo.md) → list item theo ITEM_SCHEMA.

Dùng cho social-media-intelligence (mục 2.5). Nhóm FB/Zalo kín không cào hợp lệ được →
analyst nhập tay sự kiện lớn vào template, loader này nạp vào pipeline buzz/đội lái.

Chạy:  $HOME/.venv/Scripts/python.exe nhap_tay_loader.py tin_hieu_fb_zalo.md
"""
from __future__ import annotations
import hashlib
import re
import sys
from datetime import datetime
from pathlib import Path

_MA_RE = re.compile(r"\b([A-Z]{3})\b")
_STOP_MA = {"VND", "USD", "GDP", "CPI", "FED", "ROE", "ROA", "EPS", "NĐT", "CTY", "ACE"}
_KEYS = {"nguon", "nhom", "thoi_gian", "ma", "huong_ho", "do_nong", "nghi_lai", "ghi_chu"}


def _trich_ma(text: str) -> list[str]:
    return sorted({m for m in _MA_RE.findall(text or "") if m not in _STOP_MA})


def _parse_thoi_gian(s: str) -> str:
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).isoformat()
        except ValueError:
            continue
    return s  # giữ nguyên nếu không parse được; báo người dùng kiểm tay


def _hash(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]


def doc_tin_hieu(path: str | Path) -> list[dict]:
    raw = Path(path).read_text(encoding="utf-8")
    # Bỏ dòng chú thích (#), nhưng GIỮ nguyên phần noi_dung (dán nguyên văn có thể chứa #).
    items: list[dict] = []
    for block in raw.split("=== TÍN HIỆU ==="):
        if "=== HẾT ===" not in block:
            continue
        body = block.split("=== HẾT ===")[0]
        fields: dict[str, str] = {}
        noi_dung_lines: list[str] = []
        in_noi_dung = False
        for line in body.splitlines():
            if in_noi_dung:
                noi_dung_lines.append(line)
                continue
            stripped = line.strip()
            if stripped.startswith("#") or not stripped:
                continue
            if stripped.startswith("noi_dung:"):
                in_noi_dung = True
                rest = stripped[len("noi_dung:"):].strip()
                if rest:
                    noi_dung_lines.append(rest)
                continue
            if ":" in stripped:
                key, val = stripped.split(":", 1)
                key = key.strip().lower()
                if key in _KEYS:
                    fields[key] = val.split("#")[0].strip()  # cắt chú thích cuối dòng
        noi_dung = "\n".join(noi_dung_lines).strip()
        if not fields.get("nguon") and not noi_dung:
            continue  # khối rỗng

        ma_field = [m.strip().upper() for m in (fields.get("ma", "")).replace(";", ",").split(",") if m.strip()]
        ma_nhac_den = sorted(set(ma_field) | set(_trich_ma(noi_dung)))
        nguon = (fields.get("nguon") or "facebook").lower()
        nhom = fields.get("nhom", "")

        items.append({
            "nguon": nguon,                          # facebook | zalo
            "loai": "group",
            "id": _hash(nguon, nhom, fields.get("thoi_gian", ""), noi_dung[:40]),
            "thoi_gian": _parse_thoi_gian(fields.get("thoi_gian", "")),
            "tac_gia": {
                "id": _hash(nguon, nhom),            # ẩn danh: chỉ định danh theo NHÓM, không theo người
                "ten": f"[nhóm] {nhom}",
                "tuoi_tk_ngay": None,
                "so_bai": None,
                "uy_tin": "thanh_vien",
            },
            "noi_dung": noi_dung,
            "ma_nhac_den": ma_nhac_den,
            "tuong_tac": {"like": None, "reply": None, "view": None, "share": None},
            "huong_ho": (fields.get("huong_ho") or "trung_lap").lower(),
            "do_nong": (fields.get("do_nong") or "trung").lower(),     # cao|trung|thap (đầu vào buzz)
            "ghi_chu": fields.get("ghi_chu", ""),
            "sentiment": None,                        # điền sau (SKILL mục 4)
            "co_dau_hieu_lai": (fields.get("nghi_lai", "").lower() == "co"),  # gợi ý từ analyst (mục 5)
        })
    return items


if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else "tin_hieu_fb_zalo.md"
    out = doc_tin_hieu(Path(__file__).with_name(p) if not Path(p).is_absolute() else p)
    import json
    print(f"Đã nạp {len(out)} tín hiệu:")
    print(json.dumps(out, ensure_ascii=False, indent=2))
