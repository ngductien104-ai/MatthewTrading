"""Tự phân loại ngành → chọn bộ phương pháp định giá phù hợp (thị trường VN).

Đọc phân loại THẬT từ vnstock ``Company.overview()`` (``is_bank`` + ``sector`` +
``icb_code_lv2``) rồi trả về bộ phương pháp định giá nên dùng cho ngành đó, theo
bản đồ ngành trong SKILL.md.

Dùng:
    python classify_valuation.py VCB
    python classify_valuation.py FPT HPG VHM SSI      # nhiều mã
hoặc import:
    from classify_valuation import classify_valuation
    rec = classify_valuation("VCB")    # -> dict

Lưu ý: ICB không tách được BĐS nhà ở vs BĐS khu công nghiệp (cùng 8600/Real
Estate) và không gắn cờ "holding/đa ngành" → các trường hợp này script nêu cảnh
báo để người phân tích tự quyết (xem ``notes``).
"""

from __future__ import annotations

import contextlib
import io
import sys
from typing import Dict, Optional

# Khóa chính = giá trị ``sector`` (tiếng Anh) do vnstock VCI trả về (đã xác minh).
# Mỗi ngành: phương pháp chính / kiểm chứng chéo / tránh / động lực giá trị.
SECTOR_METHODS: Dict[str, Dict[str, object]] = {
    "Banks": {
        "primary": ["RIM", "PB-ROE"], "crosscheck": ["DDM"], "avoid": ["DCF/FCFF", "EV/EBITDA"],
        "drivers": "ROE, NIM, NPL/LLR, CASA, CAR (TT41), tăng trưởng tín dụng",
    },
    "Financial Services": {  # chứng khoán + dịch vụ tài chính khác
        "primary": ["P/B", "SOTP (môi giới + margin + tự doanh)"], "crosscheck": ["RIM"],
        "avoid": ["DCF", "EV/EBITDA"],
        "drivers": "ROE chuẩn hóa, dư nợ margin, phụ thuộc tự doanh (FVTPL) — LN biến động mạnh",
    },
    "Insurance": {
        "primary": ["PB-ROE", "Embedded Value (nhân thọ)"], "crosscheck": ["P/E"], "avoid": ["DCF"],
        "drivers": "LN đầu tư + kỹ thuật (combined ratio)",
    },
    "Real Estate": {
        "primary": ["RNAV"], "crosscheck": ["P/B (cẩn trọng)", "presales"],
        "avoid": ["P/E (LN giật cục theo bàn giao)", "EV/EBITDA"],
        "drivers": "Quỹ đất, pháp lý dự án, presales (người mua trả tiền trước), đòn bẩy",
    },
    "Basic Resources": {  # thép, vật liệu cơ bản — chu kỳ
        "primary": ["EV/EBITDA", "P/B", "P/E chuẩn hóa giữa chu kỳ"], "crosscheck": ["ROIC vs WACC"],
        "avoid": ["P/E hiện tại (bẫy đỉnh chu kỳ)"],
        "drivers": "Công suất, biên (giá bán − giá nguyên liệu), chu kỳ hàng hóa",
    },
    "Construction & Materials": {
        "primary": ["P/E điều chỉnh backlog", "EV/EBIT"], "crosscheck": ["P/B"],
        "avoid": ["EV/EBITDA thuần"],
        "drivers": "Backlog hợp đồng, vòng quay vốn lưu động, rủi ro phải thu (VLXD chu kỳ: + EV/EBITDA)",
    },
    "Food & Beverage": {
        "primary": ["DCF", "P/E"], "crosscheck": ["EV/EBITDA", "DDM"], "avoid": [],
        "drivers": "Thương hiệu, biên gộp, tăng trưởng sản lượng (nông/thủy sản: dùng LN chuẩn hóa, lưu ý chu kỳ hàng hóa + tỷ giá XK)",
    },
    "Retail": {
        "primary": ["EV/EBITDA", "P/E"], "crosscheck": ["EV/Sales (tăng trưởng)"], "avoid": [],
        "drivers": "LFL sales, store economics, vòng quay tồn kho",
    },
    "Technology": {
        "primary": ["DCF", "P/E", "PEG"], "crosscheck": ["EV/EBITDA", "EV/Sales (SaaS)"], "avoid": [],
        "drivers": "Tăng trưởng, biên, backlog dịch vụ",
    },
    "Utilities": {
        "primary": ["DCF", "DDM"], "crosscheck": ["EV/EBITDA"], "avoid": [],
        "drivers": "Dòng tiền ổn định/điều tiết, cổ tức, hợp đồng PPA (phân phối khí/xăng dầu: + chu kỳ giá hàng hóa)",
    },
    "Industrial Goods & Services": {  # công nghiệp, logistics, cảng
        "primary": ["DCF (FCFF)", "EV/EBITDA"], "crosscheck": ["P/E", "ROIC vs WACC"], "avoid": [],
        "drivers": "ROIC vs WACC, công suất; logistics/cảng: sản lượng thông qua",
    },
    "Health Care": {
        "primary": ["DCF", "P/E"], "crosscheck": ["EV/EBITDA"], "avoid": [],
        "drivers": "Danh mục sản phẩm, kênh ETC/OTC",
    },
    "Oil & Gas": {
        "primary": ["EV/EBITDA", "EV/trữ lượng"], "crosscheck": ["DCF", "NAV"], "avoid": ["P/E"],
        "drivers": "Giá dầu, trữ lượng (1P/2P), sản lượng",
    },
    "Telecommunications": {
        "primary": ["DCF", "EV/EBITDA"], "crosscheck": ["DDM"], "avoid": [],
        "drivers": "ARPU, thuê bao, capex hạ tầng",
    },
}

# Lùi về theo mã ICB cấp 2 khi ``sector`` thiếu/không khớp.
ICB_LV2_TO_SECTOR: Dict[str, str] = {
    "8300": "Banks", "8500": "Insurance", "8600": "Real Estate", "8700": "Financial Services",
    "1700": "Basic Resources", "2300": "Construction & Materials",
    "2700": "Industrial Goods & Services", "3500": "Food & Beverage", "4500": "Health Care",
    "5300": "Retail", "7500": "Utilities", "9500": "Technology",
    "0500": "Oil & Gas", "0530": "Oil & Gas", "6500": "Telecommunications",
}


def _overview(symbol: str, source: str):
    """Lấy 1 dòng overview của mã (đã chặn banner vnstock khỏi stdout)."""
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        from vnstock.api.company import Company
        ov = Company(symbol=symbol.upper().replace(".VN", ""), source=source).overview()
    return ov.iloc[0]


def _as_bool(value) -> bool:
    return str(value).strip().lower() in {"true", "1", "1.0", "yes"}


def classify_valuation(symbol: str, source: str = "VCI") -> Dict[str, object]:
    """Phân loại ngành 1 mã và trả bộ phương pháp định giá nên dùng.

    Returns:
        dict gồm symbol, is_bank, sector, icb_code_lv2, methods{primary/crosscheck/
        avoid/drivers}, notes (cảnh báo cần xét tay).
    """
    row = _overview(symbol, source)
    is_bank = _as_bool(row.get("is_bank"))
    sector = str(row.get("sector") or "").strip()
    icb_lv2 = str(row.get("icb_code_lv2") or "").strip().replace(".0", "")

    # 1) is_bank là tín hiệu chắc chắn nhất.
    resolved = "Banks" if is_bank else sector
    # 2) sector không khớp bảng → lùi về mã ICB cấp 2.
    if resolved not in SECTOR_METHODS:
        resolved = ICB_LV2_TO_SECTOR.get(icb_lv2, resolved)

    methods = SECTOR_METHODS.get(resolved)
    notes = []
    if methods is None:
        methods = {
            "primary": ["DCF", "bội số tương đối (P/E, EV/EBITDA)"], "crosscheck": [], "avoid": [],
            "drivers": "Chưa map được ngành — phân loại tay theo mô tả hoạt động.",
        }
        notes.append(f"⚠️ Không map được ngành (sector={sector!r}, icb_lv2={icb_lv2!r}) → dùng khung chung, kiểm tra tay.")

    # Cảnh báo các trường hợp ICB không phân biệt được.
    if resolved == "Real Estate":
        notes.append("BĐS: ICB không tách nhà ở vs KHU CÔNG NGHIỆP. Nếu là KCN → RNAV + DCF dòng cho thuê; cho thuê/TTTM → NAV theo cap rate.")
    if resolved in {"Real Estate", "Food & Beverage", "Industrial Goods & Services"}:
        notes.append("Nếu DN là HOLDING/đa ngành (nhiều mảng lớn) → chuyển sang SOTP, định giá từng mảng theo ngành của nó.")

    return {
        "symbol": symbol.upper(),
        "is_bank": is_bank,
        "sector": sector,
        "icb_code_lv2": icb_lv2,
        "resolved_sector": resolved,
        "methods": methods,
        "notes": notes,
    }


def _format(rec: Dict[str, object]) -> str:
    m = rec["methods"]
    lines = [
        f"📊 {rec['symbol']}  | ngành: {rec['sector']} (ICB {rec['icb_code_lv2']}) | is_bank={rec['is_bank']}",
        f"   → Áp khung: {rec['resolved_sector']}",
        f"   • Phương pháp CHÍNH   : {', '.join(m['primary']) or '-'}",
        f"   • Kiểm chứng chéo     : {', '.join(m['crosscheck']) or '-'}",
        f"   • TRÁNH               : {', '.join(m['avoid']) or '-'}",
        f"   • Động lực giá trị    : {m['drivers']}",
    ]
    for n in rec["notes"]:
        lines.append(f"   ⚠ {n}")
    return "\n".join(lines)


if __name__ == "__main__":
    symbols = sys.argv[1:] or ["VCB", "FPT", "VHM", "HPG", "SSI"]
    for s in symbols:
        try:
            print(_format(classify_valuation(s)))
        except Exception as exc:  # noqa: BLE001 - một mã lỗi không chặn các mã khác
            print(f"📊 {s}: lỗi phân loại — {type(exc).__name__}: {exc}")
        print()
