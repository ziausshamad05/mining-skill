#!/usr/bin/env python3
"""
rkab_validator.py - Validasi konsistensi draf RKAB Minerba sebelum dikirim ke MinerbaOne.

Input : CSV/XLSX berformat "kunci,nilai" (lihat templates/rkab_ringkasan_template.csv),
        atau JSON {kunci: nilai}.
Output: tabel kepatuhan (Status | Temuan | Dasar Regulasi | Rekomendasi Perbaikan)
        dalam Markdown (default) atau JSON (--json).

Pemeriksaan:
  A. Prasyarat Pasal 5 Permen ESDM 17/2025 (sebagaimana diubah Permen ESDM 6/2026)
  B. Produksi vs kapasitas FS & dokumen lingkungan
  C. Neraca produksi - penjualan - stok
  D. Pemenuhan DMO (jika persentase DMO diisi)
  E. Keselarasan total biaya matriks keuangan vs jumlah anggaran matriks teknis
  F. Kelengkapan matriks (status "Sudah Diisi")
  G. Tenggat penyampaian (1 Okt - 15 Nov tahun sebelumnya)

Kode keluar: 0 = tidak ada temuan KRITIS, 1 = ada temuan KRITIS, 2 = input tidak valid.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path

P17 = "Permen ESDM 17/2025 jo. Permen ESDM 6/2026"
K341 = "Kepmen ESDM 341.K/MB.01/MEM.B/2025 (format & matriks RKAB)"

# Kunci anggaran teknis yang harus terjumlah ke biaya pada matriks keuangan.
BIAYA_TEKNIS = [
    "biaya_eksplorasi", "biaya_konstruksi", "biaya_penambangan", "biaya_pengolahan_pemurnian",
    "biaya_pengangkutan_penjualan", "biaya_k3_ko", "biaya_lingkungan_reklamasi",
    "biaya_pascatambang", "biaya_ppm", "biaya_tenaga_kerja", "biaya_umum_administrasi",
]
MATRIKS = [
    "matriks_eksplorasi_sdc", "matriks_konstruksi", "matriks_produksi_pengolahan",
    "matriks_pemasaran_penjualan", "matriks_k3_ko", "matriks_lingkungan_reklamasi",
    "matriks_ppm", "matriks_tenaga_kerja_tkdn", "matriks_keuangan",
]
TRUE = {"ya", "y", "yes", "true", "1", "ada", "lunas", "sudah", "valid", "berlaku", "sudah diisi"}
FALSE = {"tidak", "t", "no", "false", "0", "belum", "tidak ada", "kosong", "-", ""}


def load(path: Path) -> dict:
    if path.suffix.lower() == ".json":
        return {k.strip().lower(): v for k, v in json.loads(path.read_text()).items()}
    rows: list[list] = []
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        from openpyxl import load_workbook  # type: ignore
        ws = load_workbook(path, data_only=True).active
        rows = [[c for c in r] for r in ws.iter_rows(values_only=True)]
    else:
        with path.open(newline="", encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
    data = {}
    for r in rows:
        if not r or r[0] is None:
            continue
        k = str(r[0]).strip().lower()
        if not k or k.startswith("#") or k == "kunci":
            continue
        data[k] = r[1] if len(r) > 1 else None
    return data


def num(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(" ", "")
    if not s or s == "-":
        return None
    # dukung format Indonesia 1.234.567,89 dan format 1,234,567.89
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".") if s.count(",") == 1 and len(s.split(",")[1]) <= 2 else s.replace(",", "")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    elif s.count(".") == 1 and len(s.split(".")[1]) == 3 and s.split(".")[0].lstrip("-") not in ("", "0"):
        s = s.replace(".", "")  # "50.000" = lima puluh ribu (format Indonesia)
    try:
        return float(s)
    except ValueError:
        return None


def boolean(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in TRUE:
        return True
    if s in FALSE:
        return False
    return None


def fmt(x):
    return f"{x:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".") if x is not None else "-"


class Report:
    def __init__(self):
        self.rows = []

    def add(self, status, temuan, dasar, rekom):
        self.rows.append({"status": status, "temuan": temuan, "dasar_regulasi": dasar,
                          "rekomendasi": rekom})

    @property
    def kritis(self):
        return sum(r["status"] == "KRITIS" for r in self.rows)

    def markdown(self, d):
        nama = d.get("nama_perusahaan", "-")
        tahun = d.get("tahun_rkab", "-")
        out = [f"## Tinjauan Kepatuhan RKAB {tahun} - {nama}", "",
               f"Tahap: {d.get('tahap', '-')} | Komoditas: {d.get('komoditas', '-')} | "
               f"KRITIS: {self.kritis} | PERHATIAN: {sum(r['status']=='PERHATIAN' for r in self.rows)} | "
               f"OK: {sum(r['status']=='OK' for r in self.rows)}", "",
               "| No | Status | Temuan | Dasar Regulasi | Rekomendasi Perbaikan |",
               "|---|---|---|---|---|"]
        order = {"KRITIS": 0, "PERHATIAN": 1, "INFO": 2, "OK": 3}
        for i, r in enumerate(sorted(self.rows, key=lambda r: order.get(r["status"], 9)), 1):
            out.append(f"| {i} | {r['status']} | {r['temuan']} | {r['dasar_regulasi']} | {r['rekomendasi']} |")
        out += ["", "> Alat bantu internal, bukan keputusan evaluator. Cocokkan dengan teks Pasal terbaru "
                "(jalankan `jdih_fetch.py`) dan Kepmen 341.K/MB.01/MEM.B/2025."]
        return "\n".join(out)


def check(d: dict, today: date | None = None) -> Report:
    rp = Report()
    tahap = str(d.get("tahap", "operasi produksi")).lower()
    op = "operasi" in tahap or tahap in ("op", "produksi")
    komoditas = str(d.get("komoditas", "")).lower()

    # ---------------- A. Prasyarat
    prasyarat = [
        ("izin_aktif_oss", "Perizinan (IUP/IUPK) aktif & data administratif terintegrasi OSS/MinerbaOne",
         "Pasal 5 " + P17, "Perbarui data perizinan di OSS/MODI sebelum mengajukan."),
        ("pnbp_lunas", "Bukti pelunasan/pembayaran PNBP (iuran tetap, royalti) ke kas negara",
         "Pasal 5 " + P17, "Lunasi tunggakan PNBP dan unggah bukti setor (e-PNBP/SIMPONI)."),
        ("peta_digital", "Peta digital realisasi & rencana kegiatan (SHP/GIS)",
         "Pasal 5 " + P17, "Siapkan shapefile sesuai standar Ditjen Minerba, termasuk tumpang tindih kawasan hutan."),
        ("jamrek_ditempatkan", "Bukti penempatan Jaminan Reklamasi" +
         (" tahap OP untuk 1 tahun sebelum tahun permohonan" if op else " tahap eksplorasi"),
         "Pasal 5 " + P17, "Tempatkan Jamrek & unggah bukti; tanpa ini RKAB tidak disetujui."),
        ("ktt_disahkan", "Kepala Teknik Tambang (KTT) ditunjuk/disahkan",
         "Pasal 5 " + P17 + "; Permen ESDM 26/2018", "Ajukan pengesahan KTT (atau KTT sementara) sebelum submit."),
    ]
    if op:
        prasyarat += [
            ("laporan_sdc_cp", "Laporan estimasi sumber daya & cadangan oleh Competent Person "
             "(penanggung jawab internal utk batuan)", "Pasal 5 " + P17,
             "Mutakhirkan laporan SDC yang ditandatangani CPI/CP terdaftar."),
            ("fs_disetujui", "Persetujuan/pengesahan Studi Kelayakan", "Pasal 5 " + P17,
             "Ajukan revisi FS bila rencana produksi/lokasi berubah."),
            ("dokumen_lingkungan_berlaku", "Persetujuan Lingkungan (AMDAL/UKL-UPL) berlaku",
             "Pasal 5 " + P17 + "; PP 22/2021", "Perbarui adendum AMDAL bila kapasitas naik."),
        ]
    for key, label, dasar, rekom in prasyarat:
        v = boolean(d.get(key))
        if v is True:
            rp.add("OK", label + ": terpenuhi.", dasar, "-")
        elif v is False:
            rp.add("KRITIS", label + ": BELUM terpenuhi.", dasar, rekom)
        else:
            rp.add("PERHATIAN", label + ": data tidak diisi.", dasar, "Isi kolom `" + key + "` (ya/tidak).")

    hutan = boolean(d.get("dalam_kawasan_hutan"))
    if hutan:
        v = boolean(d.get("ppkh_ada"))
        rp.add("OK" if v else "KRITIS",
               "Wilayah dalam kawasan hutan; PPKH " + ("tersedia." if v else "belum tersedia."),
               "UU 41/1999; PP 23/2021; peta tumpang tindih kawasan hutan pada Pasal 5 " + P17,
               "-" if v else "Jangan rencanakan bukaan lahan di kawasan hutan tanpa PPKH.")

    kswp = boolean(d.get("kswp_valid"))
    if kswp is False:
        rp.add("PERHATIAN", "Status KSWP (kepatuhan pajak) tidak valid.",
               "Kebijakan kepatuhan pajak (dibahas Ditjen Minerba-Kemenkeu, Okt 2025; cek SE terbaru)",
               "Pulihkan status KSWP; berisiko menjadi syarat persetujuan.")

    # ---------------- B. Produksi vs FS
    prod = num(d.get("produksi_rencana_ton"))
    cap_fs = num(d.get("kapasitas_fs_ton"))
    cap_ling = num(d.get("kapasitas_dokumen_lingkungan_ton"))
    if op:
        if prod is None:
            rp.add("PERHATIAN", "Rencana produksi tidak diisi.", K341, "Isi `produksi_rencana_ton`.")
        for cap, nama in ((cap_fs, "persetujuan FS"), (cap_ling, "dokumen lingkungan")):
            if prod is None or cap is None:
                continue
            if prod > cap:
                rp.add("KRITIS", f"Produksi rencana {fmt(prod)} t melebihi kapasitas {nama} {fmt(cap)} t "
                       f"(+{(prod / cap - 1) * 100:.1f}%).", "Pasal 5 " + P17,
                       f"Turunkan produksi ≤ {fmt(cap)} t atau selesaikan revisi {nama} terlebih dahulu.")
            else:
                rp.add("OK", f"Produksi rencana {fmt(prod)} t ≤ kapasitas {nama} {fmt(cap)} t "
                       f"({prod / cap * 100:.1f}%).", "Pasal 5 " + P17, "-")
        if ("logam" in komoditas or "batubara" in komoditas or "nikel" in komoditas) and prod:
            rp.add("INFO", "Untuk mineral logam & batubara, rencana produksi juga dinilai terhadap kebutuhan "
                   "industri/pasar nasional.", "Pasal 5 ayat (4) " + P17,
                   "Lampirkan dasar kontrak/LOI pembeli & proyeksi pasar.")

    # ---------------- C. Neraca
    jual_dn = num(d.get("penjualan_domestik_ton")) or 0.0
    jual_ln = num(d.get("penjualan_ekspor_ton")) or 0.0
    stok_awal = num(d.get("stok_awal_ton")) or 0.0
    jual = jual_dn + jual_ln
    if op and prod is not None and jual:
        tersedia = prod + stok_awal
        if jual > tersedia * 1.0001:
            rp.add("KRITIS", f"Total penjualan {fmt(jual)} t > produksi + stok awal {fmt(tersedia)} t.",
                   K341 + " (matriks pemasaran)", "Selaraskan matriks penjualan dengan produksi & stok.")
        else:
            rp.add("OK", f"Neraca: penjualan {fmt(jual)} t ≤ produksi + stok {fmt(tersedia)} t; "
                   f"stok akhir proyeksi {fmt(tersedia - jual)} t.", K341, "-")

    # ---------------- D. DMO
    dmo_pct = num(d.get("dmo_persen_wajib"))
    if dmo_pct is not None and jual:
        basis = prod or jual
        real = jual_dn / basis * 100 if basis else 0
        ok = real + 1e-9 >= dmo_pct
        rp.add("OK" if ok else "KRITIS",
               f"DMO: penjualan domestik {real:.1f}% dari produksi (wajib {dmo_pct:.1f}%).",
               "Kepmen ESDM penetapan DMO yang berlaku (cek nomor terbaru via jdih_fetch.py)",
               "-" if ok else "Naikkan alokasi domestik / lampirkan kontrak DMO.")
    elif "batubara" in komoditas or "coal" in komoditas:
        rp.add("PERHATIAN", "Persentase DMO wajib tidak diisi (komoditas batubara).",
               "Kepmen ESDM penetapan DMO batubara yang berlaku",
               "Isi `dmo_persen_wajib` sesuai Kepmen DMO tahun berjalan.")

    # ---------------- E. Keuangan
    total_keu = num(d.get("total_biaya_matriks_keuangan"))
    parts = {k: num(d.get(k)) for k in BIAYA_TEKNIS if num(d.get(k)) is not None}
    if total_keu is not None and parts:
        s = sum(parts.values())
        tol = float(num(d.get("toleransi_selisih_persen")) or 0.5)
        selisih = total_keu - s
        pct = abs(selisih) / total_keu * 100 if total_keu else 100
        if pct > tol:
            rp.add("KRITIS", f"Total biaya matriks keuangan {fmt(total_keu)} ≠ jumlah anggaran teknis "
                   f"{fmt(s)} (selisih {fmt(selisih)}; {pct:.2f}%).", K341 + " (matriks keuangan)",
                   "Telusuri pos yang hilang/dobel; rinci: " + ", ".join(f"{k}={fmt(v)}" for k, v in parts.items()))
        else:
            rp.add("OK", f"Total biaya keuangan selaras dengan anggaran teknis (selisih {pct:.2f}% ≤ {tol}%).",
                   K341, "-")
        for k in ("biaya_lingkungan_reklamasi", "biaya_k3_ko", "biaya_ppm"):
            if op and k in BIAYA_TEKNIS and (parts.get(k) in (None, 0.0)):
                rp.add("PERHATIAN", f"Anggaran `{k}` nol/kosong pada tahap OP.", K341,
                       "Evaluator biasanya menolak RKAB OP tanpa anggaran lingkungan, K3, dan PPM.")
    elif total_keu is None:
        rp.add("PERHATIAN", "Total biaya matriks keuangan tidak diisi.", K341,
               "Isi `total_biaya_matriks_keuangan` dan pos biaya teknis.")

    # ---------------- F. Kelengkapan matriks
    kosong = [m for m in MATRIKS if m in d and boolean(d.get(m)) is not True]
    if kosong:
        rp.add("KRITIS", "Matriks belum berstatus 'Sudah Diisi': " + ", ".join(kosong) + ".", K341,
               "Lengkapi seluruh matriks di MinerbaOne sebelum tombol Kirim.")
    elif any(m in d for m in MATRIKS):
        rp.add("OK", "Seluruh matriks yang dicantumkan berstatus 'Sudah Diisi'.", K341, "-")

    # ---------------- G. Tenggat
    tahun = num(d.get("tahun_rkab"))
    today = today or date.today()
    if tahun:
        t = int(tahun)
        buka, tutup = date(t - 1, 10, 1), date(t - 1, 11, 15)
        if today < buka:
            rp.add("INFO", f"Jendela penyampaian RKAB {t}: {buka:%d-%m-%Y} s.d. {tutup:%d-%m-%Y} (belum dibuka).",
                   "Pasal 4 " + P17, "Siapkan dokumen; gunakan sisa waktu untuk melunasi prasyarat.")
        elif today <= tutup:
            sisa = (tutup - today).days
            rp.add("PERHATIAN" if sisa <= 10 else "INFO",
                   f"Jendela penyampaian RKAB {t} terbuka; sisa {sisa} hari (tutup {tutup:%d-%m-%Y}).",
                   "Pasal 4 " + P17, "Kirim lebih awal agar ada ruang untuk 3 siklus perbaikan.")
        else:
            rp.add("PERHATIAN", f"Tenggat 15 November {t - 1} untuk RKAB {t} telah lewat.",
                   "Pasal 4 " + P17 + "; SE Dirjen Minerba terkait",
                   "Periksa ketentuan keterlambatan/sanksi dan SE transisi terbaru.")
    return rp


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="CSV/XLSX/JSON ringkasan RKAB")
    ap.add_argument("--json", action="store_true", help="output JSON")
    ap.add_argument("--tanggal", help="tanggal acuan YYYY-MM-DD (default hari ini)")
    a = ap.parse_args(argv)
    try:
        d = load(Path(a.input))
    except Exception as e:
        print(f"[galat] tidak bisa membaca input: {e}", file=sys.stderr)
        return 2
    today = date.fromisoformat(a.tanggal) if a.tanggal else None
    rp = check(d, today)
    if a.json:
        print(json.dumps({"kritis": rp.kritis, "temuan": rp.rows}, ensure_ascii=False, indent=2))
    else:
        print(rp.markdown(d))
    return 1 if rp.kritis else 0


if __name__ == "__main__":
    sys.exit(main())
