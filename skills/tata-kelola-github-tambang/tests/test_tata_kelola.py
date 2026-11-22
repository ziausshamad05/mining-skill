import json
import math
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import anonimisasi  # noqa: E402
import buat_data_sintetis  # noqa: E402
import etl_telemetri  # noqa: E402
import format_tambang  # noqa: E402
import guard_data_sensitif as guard  # noqa: E402
import qaqc_assay  # noqa: E402


def test_qaqc_mendeteksi_batch_rusak(tmp_path):
    f = tmp_path / "a.csv"
    buat_data_sintetis.assay(batch_rusak=3).to_csv(f, index=False)
    r = qaqc_assay.jalankan(str(f), str(ROOT / "config/qaqc.yml"), str(tmp_path / "out"))
    assert r["status"] == "GAGAL" and r["batch_gagal"] == ["B003"]
    assert (tmp_path / "out/laporan_qaqc.md").exists() and (tmp_path / "out/ringkasan_pr.md").exists()


def test_qaqc_lulus_tanpa_kerusakan(tmp_path):
    f = tmp_path / "a.csv"
    buat_data_sintetis.assay(batch_rusak=-1).to_csv(f, index=False)
    r = qaqc_assay.jalankan(str(f), str(ROOT / "config/qaqc.yml"), str(tmp_path / "out"))
    assert r["status"] == "LULUS", r


def test_hard():
    assert math.isclose(qaqc_assay.hard(pd.Series([1.0]), pd.Series([3.0]))[0], 0.5)


def test_guard_mendeteksi(tmp_path):
    bocor = tmp_path / "konfig.py"
    bocor.write_text('db = "postgresql://user:rahasia@10.0.0.1/geo"\napi_key = "abcd1234efgh"\n'  # guard:izinkan
                     'kontak = "0812345678901"\nnik = "7401015506900001"\n')  # guard:izinkan data uji palsu
    aman = tmp_path / "aman.py"
    aman.write_text('x = 1  # tidak ada data\nemail = "dev@ssu.co.id"\n')  # guard:izinkan
    t = guard.pindai([str(bocor), str(aman)], domain_perusahaan={"ssu.co.id"})
    jenis = " ".join(t)
    assert "conn_string" in jenis and "password_assign" in jenis and "nomor HP" in jenis and "NIK" in jenis
    assert not [x for x in t if "aman.py" in x]


def test_guard_assay_dan_bbox(tmp_path):
    f = tmp_path / "collar.csv"
    f.write_text("hole_id,x,y,z,Ni\nH1,410500,9510500,120,1.5\n")
    bbox = [410000, 9510000, 411000, 9511000]
    t = guard.pindai([str(f)], bbox=bbox)
    assert any("DATA MENTAH" in x for x in t) and any("WIUP" in x for x in t)
    d = tmp_path / "sintetis"
    d.mkdir()
    g = d / "collar.csv"
    g.write_text(f.read_text())
    assert guard.pindai([str(g)], bbox=bbox) == []


def test_guard_izinkan(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("hubungi 081234567890 guard:izinkan nomor hotline publik\n")
    assert guard.pindai([str(f)]) == []


def test_anonimisasi_menjaga_jarak():
    df = pd.DataFrame({"hole_id": ["A", "B", "C"], "x": [410000.0, 410100.0, 410000.0],
                       "y": [9510000.0, 9510000.0, 9510050.0], "z": [100.0, 90.0, 95.0], "Ni": [1.2, 1.5, 0.9],
                       "driller": ["Budi", "Andi", "Siti"]})
    k = b"kunci-uji-0123456789"
    o = anonimisasi.anonimkan(df, k, ["x", "y", "z"], ["hole_id"], ["Ni"], hapus=["driller"],
                              desimal_koord=4, pusat=(410000, 9510000))
    d0 = math.dist((df.x[0], df.y[0]), (df.x[1], df.y[1]))
    d1 = math.dist((o.x[0], o.y[0]), (o.x[1], o.y[1]))
    assert abs(d0 - d1) < 1e-2
    assert "driller" not in o and o.hole_id[0].startswith("H-") and o.hole_id[0] != "A"
    assert (o.x != df.x).all()
    o2 = anonimisasi.anonimkan(df, k, ["x", "y", "z"], ["hole_id"], desimal_koord=4, pusat=(410000, 9510000))
    assert o.hole_id.tolist() == o2.hole_id.tolist()  # deterministik


def test_etl_kpi_dan_pseudonim(tmp_path):
    f = tmp_path / "fms.csv"
    df = pd.DataFrame({"unit_id": ["DT1"] * 3, "operator_id": ["EMP1"] * 3,
                       "waktu_mulai": ["2026-11-01 07:00", "2026-11-01 15:00", "2026-11-01 17:00"],
                       "waktu_selesai": ["2026-11-01 15:00", "2026-11-01 17:00", "2026-11-01 21:00"],
                       "status": ["WORKING", "STANDBY", "BREAKDOWN"], "nama_operator": ["Budi"] * 3})
    df.to_csv(f, index=False)
    r = etl_telemetri.jalankan(str(f), str(tmp_path / "o"), salt=b"salt-uji")
    k = pd.read_csv(tmp_path / "o/kpi_unit.csv").iloc[0]
    # W=8, S=2, R=4 (2 jam R di shift siang s.d. 19.00 + 2 jam di shift malam)
    assert (k.jam_W, k.jam_S, k.jam_R) == (8, 2, 4)
    assert math.isclose(k.MA, round(8 / 12, 4)) and math.isclose(k.PA, round(10 / 14, 4))
    assert math.isclose(k.UA, 0.8) and math.isclose(k.EU, round(8 / 14, 4))
    j = pd.read_csv(tmp_path / "o/fakta_jam_status.csv")
    assert set(j["shift"]) == {"SIANG", "MALAM"}
    assert j.operator_ps.str.startswith("OP-").all() and "EMP1" not in (tmp_path / "o/fakta_jam_status.csv").read_text()
    assert "Budi" not in (tmp_path / "o/fakta_jam_status.csv").read_text()
    assert r["unit_di_bawah_ambang"]["PA"] == ["DT1"]


def test_etl_wajib_salt(tmp_path):
    f = tmp_path / "fms.csv"
    buat_data_sintetis.fms().to_csv(f, index=False)
    with pytest.raises(SystemExit):
        etl_telemetri.jalankan(str(f), str(tmp_path / "o"), salt=None)


def test_surpac_str_bolak_balik(tmp_path):
    seg = [{"string": 1, "titik": [(410000.0, 9510000.0, 100.0), (410010.0, 9510005.0, 100.0)], "d": "crest"},
           {"string": 2, "titik": [(410001.5, 9510001.25, 95.0)]}]
    f = format_tambang.tulis_str(tmp_path / "a.str", seg)
    lines = f.read_text().splitlines()
    assert lines[1].startswith("0, 0.000") and lines[-1] == "0, 0.000, 0.000, 0.000, END"
    assert lines[2] == "1, 9510000.000, 410000.000, 100.000, crest"   # Y sebelum X
    df = format_tambang.baca_str(f)
    assert len(df) == 3 and df.string.tolist() == [1, 1, 2] and df.x.iloc[2] == 410001.5


def test_json_ruleset_valid():
    for p in (ROOT / "templates/rulesets").glob("*.json"):
        d = json.loads(p.read_text())
        assert d["enforcement"] == "active" and d["rules"]


def test_yaml_templat_valid():
    yaml = pytest.importorskip("yaml")
    files = list((ROOT / "templates/.github").rglob("*.yml")) + [ROOT / "templates/.pre-commit-config.yaml"]
    for p in files:
        assert yaml.safe_load(p.read_text()), p


def test_cli_qaqc_exit_code(tmp_path):
    r = subprocess.run([sys.executable, str(ROOT / "scripts/qaqc_assay.py"), "--data",
                        str(ROOT / "data/sintetis/assay_qaqc.csv"), "--config", str(ROOT / "config/qaqc.yml"),
                        "--out", str(tmp_path / "o")], capture_output=True, text=True)
    assert r.returncode == 1
