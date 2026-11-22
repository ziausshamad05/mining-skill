import json, math, os, sys, filecmp
import numpy as np
HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import haul_road as hr  # noqa: E402
import cad_export as cx  # noqa: E402


def test_cad_export_identik_antar_skill():
    a = os.path.join(HERE, "..", "scripts", "cad_export.py")
    b = os.path.join(HERE, "..", "..", "desain-pit-geoteknik", "scripts", "cad_export.py")
    assert filecmp.cmp(a, b, shallow=False)


def test_lebar_dan_tanggul_kepmen():
    cfg = hr.load_config()
    g = hr.geometri(cfg)
    assert math.isclose(g["W_lurus"], 3.5 * cfg["unit_terbesar"]["lebar_m"])
    assert g["tanggul_tinggi"] >= 0.75 * cfg["unit_terbesar"]["diameter_roda_m"] - 1e-9
    cfg["jumlah_jalur"] = 1
    assert hr.geometri(cfg)["W_lurus"] >= 2.0 * cfg["unit_terbesar"]["lebar_m"]


def test_alinyemen_tikungan():
    al = hr.HAlignment([[0, 0], [100, 0], [100, 100]], [30])
    c = al.curves[0]
    assert math.isclose(c["delta_deg"], 90, abs_tol=1e-6)
    assert math.isclose(c["L"], 30 * math.pi / 2, rel_tol=1e-6)
    assert math.isclose(al.length, 70 + 70 + 30 * math.pi / 2, rel_tol=1e-6)
    p, t, k, _ = al.at(al.sta_end)
    assert np.allclose(p, [100, 100])


def test_demo_lengkap(tmp_path):
    cfg = hr.load_config(None, hr.DEMO_CFG)
    s = hr.run(cfg, str(tmp_path))
    assert s["grade_maks_pct"] <= 12 + 1e-6
    assert s["lolos_semua"]
    for f in ("jalan.xml", "jalan_plan.dxf", "jalan_3d.dxf", "jalan_profil.dxf", "jalan_penampang.dxf",
              "koridor.obj", "lembar_gambar.pdf", "laporan.md", "volume.csv"):
        assert (tmp_path / f).stat().st_size > 0
    pts, tris = cx.read_landxml_surface(str(tmp_path / "jalan.xml"), "FG_Koridor_Jalan")
    assert len(pts) > 100 and len(tris) > 100
    import ezdxf
    assert len(ezdxf.readfile(str(tmp_path / "jalan_3d.dxf")).audit().errors) == 0


def test_grade_terlalu_curam_ditandai(tmp_path):
    cfg = hr.load_config(None, hr.DEMO_CFG)
    cfg["profil"] = {"mode": "manual", "pvi": [[0, 60], [500, 140], [968.8, 150]]}
    s = hr.run(cfg, str(tmp_path))
    g = [c for c in s["pemeriksaan"] if c["item"].startswith("Kemiringan memanjang")][0]
    assert g["status"] == "TIDAK MEMENUHI"
