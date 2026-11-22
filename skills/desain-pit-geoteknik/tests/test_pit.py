import os, sys
import numpy as np
HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import geotek as gt  # noqa: E402
import pit_design as pd_  # noqa: E402


def test_syarat_tabel1():
    s = gt.syarat("keseluruhan", "menengah")
    assert s["fk_statis"] == 1.3 and s["fk_dinamis"] == 1.05 and s["pof_maks"] == 0.10
    assert gt.syarat("tunggal", "tinggi")["fk_statis"] == 1.1


def test_bishop_wajar():
    # lereng homogen 20 m, 45 derajat, c/(gamma H)=0.05, phi=30 -> FK ~1.1-1.5 (grafik Hoek-Bray)
    xz, info = gt.profil_lereng(20, 45, 0, 1)
    fs, _ = gt.cari_fk_min(xz, gt.Material.tunggal(20, 20, 30), info=info)
    assert 1.0 < fs < 1.6
    fs2, _ = gt.cari_fk_min(xz, gt.Material.tunggal(20, 20, 30), kh=0.15, info=info)
    assert fs2 < fs


def test_ultimate_pit_kecil():
    dims = (10.0, 10.0, 10.0)
    xs = np.arange(5, 100, 10.0)
    X, Y, Z = np.meshgrid(xs, xs, np.arange(5, 50, 10.0), indexing="ij")
    bm = dict(x=X.ravel(), y=Y.ravel(), z=Z.ravel())
    val = -np.ones(X.size) * 10
    idx = np.argmin((bm["x"] - 45) ** 2 + (bm["y"] - 45) ** 2 + (bm["z"] - 15) ** 2)
    val[idx] = 1000.0
    mined, info = pd_.ultimate_pit(bm, dims, val, 45.0)
    assert mined[idx]
    # blok di atasnya ikut tertambang (preseden)
    above = (bm["x"] == bm["x"][idx]) & (bm["y"] == bm["y"][idx]) & (bm["z"] > bm["z"][idx])
    assert mined[above].all()
    val[idx] = 5.0
    mined2, _ = pd_.ultimate_pit(bm, dims, val, 45.0)
    assert not mined2.any()


def test_demo(tmp_path):
    cfg = pd_.load_config(None, pd_.DEMO_CFG)
    cfg["geoteknik"]["n_monte_carlo"] = 150
    s = pd_.run(cfg, str(tmp_path))
    d = s["cadangan"]["desain"]
    assert d["bijih_ton"] > 1e6 and 0 < d["nisbah_kupas"] < 20
    for f in ("pit.xml", "pit_plan.dxf", "pit_3d.dxf", "pit_final.obj", "lembar_gambar.pdf", "block_model_hasil.csv"):
        assert (tmp_path / f).stat().st_size > 0
    geo = {c["item"]: c["status"] for c in s["pemeriksaan"] if c["item"].startswith("Lereng")}
    assert all(v == "MEMENUHI" for v in geo.values())
