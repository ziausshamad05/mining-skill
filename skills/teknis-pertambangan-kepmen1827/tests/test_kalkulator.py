import os, sys
HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import kalkulator_teknis as k  # noqa: E402


def st(d, prefix):
    return [c["status"] for c in d["cek"] if c["item"].startswith(prefix)][0]


def test_sump():
    d = k.main(["sump", "--luas-ha", "35", "--hujan-mm", "120", "--volume-sump", "10000"])
    assert st(d, "Kapasitas sump") == "TIDAK MEMENUHI"
    assert abs(d["kapasitas_sump_perlu_m3"] - 1.25 * d["volume_air_tambang_m3"]) < 1e-6


def test_alat_dan_ledakan():
    d = k.main(["alat", "--bucket-m3", "5.2", "--truk-ton", "40", "--jarak-m", "2500"])
    assert 3 <= d["jumlah_pemuatan"] <= 5
    d = k.main(["ledakan", "--diameter-mm", "115", "--tinggi-jenjang", "8", "--radius-manusia-m", "300"])
    assert st(d, "Jarak aman") == "TIDAK MEMENUHI"


def test_pemberaian_disposal():
    assert k.main(["pemberaian", "--ucs-mpa", "60"])["rekomendasi"] == "peledakan"
    d = k.main(["disposal", "--lebar-dasar", "300", "--panjang-dasar", "300", "--lereng-HV", "1.5"])
    assert st(d, "Lereng tunggal") == "TIDAK MEMENUHI"
