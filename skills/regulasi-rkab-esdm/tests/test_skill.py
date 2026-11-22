"""Uji offline (tanpa jaringan): parser JDIH, pemecah Pasal, dan validator RKAB.
Jalankan: python3 -m pytest skills/regulasi-rkab-esdm/tests -q
"""
import json
import sys
from datetime import date
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

import jdih_fetch as jf  # noqa: E402
import rkab_validator as rv  # noqa: E402

FIX = HERE / "fixtures"


def test_bpk_detail_metadata_status_and_pdf():
    page = (FIX / "bpk_detail.html").read_text()
    reg = jf.parse_bpk_detail(page, "https://peraturan.bpk.go.id/Details/350283/permen-esdm-no-17-tahun-2025")
    assert reg.metadata["Nomor"] == "17"
    assert reg.metadata["Tahun"] == "2025"
    assert reg.metadata["Bentuk Singkat"] == "Permen ESDM"
    assert reg.metadata["Status"] == "Berlaku"
    assert reg.metadata["Tanggal Pengundangan"] == "03 Oktober 2025"
    assert reg.title.startswith("Peraturan Menteri Energi")
    assert "5 hari kerja" in reg.abstrak
    assert reg.status_peraturan["Diubah dengan"][0].startswith("Permen ESDM No. 6 Tahun 2026")
    assert len(reg.status_peraturan["Mencabut"]) == 2
    urls = [p["url"] for p in reg.pdf_links]
    assert "https://peraturan.bpk.go.id/Download/400001/Permen%20ESDM%20Nomor%2017%20Tahun%202025.pdf" in urls


def test_bpk_search_parse_dedup():
    page = """
    <a href="/Details/350283/permen-esdm-no-17-tahun-2025">Permen ESDM No. 17 Tahun 2025</a>
    <a href="/Details/350283/permen-esdm-no-17-tahun-2025">Peraturan Menteri ESDM Nomor 17 Tahun 2025 tentang RKAB</a>
    <a href="https://peraturan.bpk.go.id/Details/350280/permen-esdm-no-6-tahun-2026">Permen ESDM No. 6 Tahun 2026</a>
    <a href="/Search?p=2">2</a>"""
    res = jf.parse_bpk_search(page)
    assert [r["id"] for r in res] == ["350283", "350280"]
    assert "tentang RKAB" in res[0]["judul"]


def test_esdm_maintenance_detected():
    page = "<html><title>ESDM-MAINTENANCE</title><h3>SISTEM SEDANG DALAM PERBAIKAN</h3></html>"
    reg = jf.parse_esdm_page(page, "https://jdih.esdm.go.id/dokumen/view?id=2828")
    assert reg.warnings and "maintenance" in reg.warnings[0].lower()


def test_esdm_pdf_links():
    page = '<a href="/storage/document/Permen%20ESDM%20Nomor%2010%20Tahun%202023.pdf">Unduh</a>'
    reg = jf.parse_esdm_page(page, "https://jdih.esdm.go.id/dokumen/view?id=1")
    assert reg.pdf_links[0]["url"].startswith("https://jdih.esdm.go.id/storage/document/")


def test_guess_urls():
    g = jf.guess_urls("permen-esdm", "17", "2025")
    assert g["peraturan_go_id_pdf"] == "https://peraturan.go.id/files/permen-esdm-no-17-tahun-2025.pdf"
    assert "nomor=17" in g["bpk_search_nomor"] and "tahun=2025" in g["bpk_search_nomor"]


def _make_pdf(path: Path):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(str(path), pagesize=A4)
    y = 800
    for line in ["BAB II", "RENCANA KERJA DAN ANGGARAN BIAYA", "Pasal 5",
                 "(1) Persyaratan penyampaian RKAB meliputi:", "a. bukti pembayaran PNBP;",
                 "(2) bukti penempatan jaminan reklamasi.", "Pasal 34A",
                 "(1) Pemegang IUP dapat melakukan pencampuran batubara setelah persetujuan Menteri."]:
        c.drawString(72, y, line)
        y -= 18
    c.save()


def test_extract_and_split_pasal(tmp_path):
    pytest.importorskip("reportlab")
    pdf = tmp_path / "uji.pdf"
    _make_pdf(pdf)
    text = jf.pdf_to_text(pdf)
    pasal = jf.split_pasal(text)
    nomor = [p["pasal"] for p in pasal]
    assert nomor == ["5", "34A"]
    assert pasal[0]["bab"] == "II" and pasal[0]["jumlah_ayat"] == 2
    assert "pencampuran batubara" in pasal[1]["teks"]


def test_cli_extract_and_pasal(tmp_path, capsys):
    pytest.importorskip("reportlab")
    pdf = tmp_path / "uji.pdf"
    _make_pdf(pdf)
    assert jf.main(["extract", str(pdf)]) == 0
    capsys.readouterr()
    assert jf.main(["pasal", str(tmp_path / "uji.pasal.json"), "34a"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["hasil"][0]["pasal"] == "34A"


def test_download_rejects_non_pdf(monkeypatch, tmp_path):
    monkeypatch.setattr(jf, "http_get", lambda *a, **k: b"<html>maintenance</html>")
    with pytest.raises(jf.FetchError):
        jf.download_pdf("https://example.go.id/x.pdf", tmp_path)


def test_download_writes_manifest(monkeypatch, tmp_path):
    monkeypatch.setattr(jf, "http_get", lambda *a, **k: b"%PDF-1.4 isi")
    m = jf.download_pdf("https://peraturan.go.id/files/permen-esdm-no-17-tahun-2025.pdf", tmp_path, {"a": 1})
    assert Path(m["file"]).exists() and len(m["sha256"]) == 64
    assert json.loads(Path(m["file"]).with_suffix(".manifest.json").read_text())["metadata"] == {"a": 1}


def test_catalog_loads(capsys):
    assert jf.main(["catalog", "--topik", "blending"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["regulasi"][0]["kode"] == "permen-esdm-6-2026"


# ------------------------------------------------------------------ validator
def test_number_parsing():
    assert rv.num("1.500.000") == 1_500_000
    assert rv.num("50.000") == 50_000
    assert rv.num("1.234.567,89") == pytest.approx(1234567.89)
    assert rv.num("0.5") == 0.5
    assert rv.num("1,234,567.5") == pytest.approx(1234567.5)


def test_template_passes():
    d = rv.load(HERE.parent / "templates" / "rkab_ringkasan_template.csv")
    rp = rv.check(d, date(2026, 10, 10))
    assert rp.kritis == 0


def test_detects_violations():
    d = rv.load(HERE.parent / "templates" / "rkab_ringkasan_template.csv")
    d.update({"produksi_rencana_ton": "2.500.000", "pnbp_lunas": "tidak", "komoditas": "batubara",
              "dmo_persen_wajib": "25", "penjualan_domestik_ton": "300.000",
              "penjualan_ekspor_ton": "2.000.000", "biaya_ppm": "0", "matriks_ppm": "belum"})
    rp = rv.check(d, date(2026, 10, 10))
    temuan = " ".join(r["temuan"] for r in rp.rows if r["status"] == "KRITIS")
    assert "melebihi kapasitas persetujuan FS" in temuan
    assert "PNBP" in temuan
    assert "DMO" in temuan
    assert "Total biaya" in temuan  # PPM dinolkan -> total tidak seimbang
    assert "matriks_ppm" in temuan


def test_cli_exit_code(tmp_path):
    f = tmp_path / "r.json"
    f.write_text(json.dumps({"tahap": "eksplorasi", "pnbp_lunas": "tidak"}))
    assert rv.main([str(f), "--json"]) == 1
