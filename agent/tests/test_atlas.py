import json
from datetime import date

from src.atlas import build, schema, status

SHAPES = {"TW": {"name": "Taiwan", "label": [121.0, 23.7],
                 "rings": [[[120.0, 22.0], [122.0, 22.0], [121.0, 25.0], [120.0, 22.0]]]}}

GICS = """
| Mã | Ngành (EN) | Ngành (VN) |
|---|---|---|
| 453010 | Semiconductors & Semiconductor Equipment | Bán dẫn |
| 151040 | Metals & Mining | Kim loại |
"""

QUEUE = """
| TT | Loại | Tên | Cấp đích | Trạng thái | Ghi chú |
|---|---|---|---|---|---|
| 1 | nganh | 453010 Bán dẫn | L1 | xong | |
| 2 | dn | TSMC | L3 | cho | 20-F |
"""

INDUSTRY = """---
loai_ghi_chu: nganh
ten: Bán dẫn
gics: 453010
cap_do: L1
mat_xich: [thiet_ke, duc]
quoc_gia_chu_chot: [US, TW]
cap_nhat: 2026-11-16
han_xem_lai: 2027-05-16
nguon: []
---
"""

COMPANY = """---
loai_ghi_chu: doanh_nghiep
ten: TSMC
quoc_gia: TW
loai: dai_chung
nganh_gics: 453010
mat_xich: [duc]
doanh_thu: 90000
don_vi_tien: USD
nam_tai_chinh: 2025
ban_cho: [Nvidia]
cap_do: L2
cap_nhat: 2026-11-16
han_xem_lai: 2026-01-01
nguon: [TSMC_20-F_2025]
---
"""


def make_atlas(tmp_path, company=COMPANY):
    (tmp_path / "_HeThong").mkdir(parents=True)
    (tmp_path / "_HeThong" / "GICS.md").write_text(GICS, encoding="utf-8")
    (tmp_path / "_HeThong" / "HANG_DOI.md").write_text(QUEUE, encoding="utf-8")
    (tmp_path / "Nganh" / "453010_BanDan").mkdir(parents=True)
    (tmp_path / "Nganh" / "453010_BanDan" / "BanDan_MOC.md").write_text(INDUSTRY, encoding="utf-8")
    (tmp_path / "DoanhNghiep").mkdir()
    (tmp_path / "DoanhNghiep" / "TSMC.md").write_text(company, encoding="utf-8")
    return tmp_path


def test_valid_atlas_has_no_errors_and_flags_missing_card(tmp_path):
    errors, warnings = schema.check(make_atlas(tmp_path))
    assert errors == []
    assert len(warnings) == 1 and "Nvidia" in warnings[0]


def test_figure_without_source_is_an_error(tmp_path):
    errors, _ = schema.check(make_atlas(tmp_path, COMPANY.replace("nguon: [TSMC_20-F_2025]", "nguon: []")))
    assert any("nguon" in e for e in errors)


def test_unknown_chain_link_country_and_gics_are_errors(tmp_path):
    bad = (COMPANY.replace("mat_xich: [duc]", "mat_xich: [dong_goi]")
           .replace("quoc_gia: TW", "quoc_gia: Taiwan"))
    errors, _ = schema.check(make_atlas(tmp_path, bad))
    assert any("dong_goi" in e for e in errors)
    assert any("ISO" in e for e in errors)


def test_unknown_gics_code_is_an_error(tmp_path):
    errors, _ = schema.check(make_atlas(tmp_path, COMPANY.replace("453010", "999999")))
    assert any("999999" in e for e in errors)


def test_status_next_item_coverage_and_overdue(tmp_path):
    atlas = make_atlas(tmp_path)
    assert "TSMC" in status.next_item(atlas)
    assert status.coverage(atlas) == {"453010": "L1"}
    assert status.overdue(atlas, today=date(2026, 11, 16)) == ["TSMC (hạn 2026-01-01)"]


def test_status_falls_back_to_gics_order_when_queue_is_done(tmp_path):
    atlas = make_atlas(tmp_path)
    queue_file = atlas / "_HeThong" / "HANG_DOI.md"
    queue_file.write_text(queue_file.read_text(encoding="utf-8").replace("| cho |", "| xong |"), encoding="utf-8")
    assert "151040" in status.next_item(atlas)


def test_build_writes_map_and_canvas_from_frontmatter(tmp_path, monkeypatch):
    atlas = make_atlas(tmp_path / "vault" / "25_Atlas")
    monkeypatch.setattr(build, "VAULT_DIR", atlas.parent)
    written = {p.name: p for p in build.build(atlas, SHAPES)}
    assert set(written) == {"atlas.json", "BanDo_BanDan.html", "ChuoiGiaTri.canvas"}

    page = written["BanDo_BanDan.html"].read_text(encoding="utf-8")
    assert "<script" not in page                      # must work with JavaScript off
    assert 'id="c-TW"' in page and 'for="c-TW"' in page
    assert "TSMC" in page and "90.000 triệu USD" in page

    canvas = json.loads(written["ChuoiGiaTri.canvas"].read_text(encoding="utf-8"))
    files = [n["file"] for n in canvas["nodes"] if n["type"] == "file"]
    assert files == ["25_Atlas/DoanhNghiep/TSMC.md"]
    assert [n["label"] for n in canvas["nodes"] if n["type"] == "group"] == ["1. thiet ke", "2. duc"]
