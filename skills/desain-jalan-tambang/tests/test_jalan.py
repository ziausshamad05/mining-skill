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
              "koridor.obj", "gambar_perencanaan_jalan.pdf", "laporan_perencanaan_jalan.pdf", "laporan_perencanaan_jalan.docx", "laporan_perencanaan_jalan.md", "volume.csv"):
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


def test_tipe_saluran_tanggul_dan_lembar(tmp_path):
    cfg = hr.load_config(os.path.join(HERE, "..", "templates", "contoh_jalan_saluran_tanggul.json"))
    cfg["geoteknik"]["n_monte_carlo"] = 100
    s = hr.run(cfg, str(tmp_path))
    # template dua sisi: tiap penampang punya saluran & tanggul di kedua sisi
    assert s["tanggul_tinggi_m"] >= 1.5 - 1e-9
    # panjang lembar plan-profile mengikuti kertas & skala: A3 @1:2000 -> > 400 m per lembar, jumlah lembar konsisten
    pp = [d for d in s["daftar_lembar"] if d["judul"].startswith("Plan & profile")]
    assert len(pp) >= 2
    assert any(d["judul"].startswith("Penampang jalan tipikal") for d in s["daftar_lembar"])
    assert any(d["judul"].startswith("Tabel volume") for d in s["daftar_lembar"])
    tv = s["tabel_volume"]
    assert abs(tv[-1]["kum_timbunan"] - s["volume_timbunan_m3"]) < 1e-3 * max(1, s["volume_timbunan_m3"])
    # lereng timbunan 1H:1V ditandai bila FK < syarat (bukan disebut aman)
    lt = [c for c in s["pemeriksaan"] if c["item"].startswith("Lereng timbunan")]
    assert lt and lt[0]["status"] in ("MEMENUHI", "TIDAK MEMENUHI")


def test_skala_mengubah_panjang_lembar(tmp_path):
    import sheets_jalan as sj
    cfg = hr.load_config(None, hr.DEMO_CFG)
    sh = sj.Sheet(cfg, "", 0, [0], "A3")
    L2000 = (sh.draw_w - 34) * 2000 / 1000
    L1000 = (sh.draw_w - 34) * 1000 / 1000
    assert abs(L2000 - 2 * L1000) < 1e-9
    sh1 = sj.Sheet(cfg, "", 0, [0], "A1")
    assert sh1.draw_w > 2 * sh.draw_w * 0.9
