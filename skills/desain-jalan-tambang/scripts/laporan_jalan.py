"""Laporan Perencanaan Jalan Tambang - format baku (PDF A4, DOCX, Markdown).

Susunan (mengikuti pola dokumen teknis yang disahkan KTT):
  Halaman judul, Lembar pengesahan, Daftar isi
  BAB 1 Pendahuluan (latar belakang, maksud & tujuan, lokasi & lingkup, dasar acuan)
  BAB 2 Data dan Asumsi (topografi, unit angkut terbesar, parameter desain, asumsi)
  BAB 3 Kriteria Desain (ketentuan Kepmen ESDM 1827 + praktik rekayasa)
  BAB 4 Hasil Perencanaan (alinyemen horizontal, vertikal, penampang, drainase, perkerasan, lereng, volume)
  BAB 5 Pemeriksaan Kepatuhan
  BAB 6 Kesimpulan dan Rekomendasi (termasuk pengendalian K3 & pemantauan)
  Lampiran: daftar gambar & daftar berkas digital
Model dokumen disusun sekali (list blok) lalu dirender ke tiga format.
"""
from __future__ import annotations

import datetime as _dt
import math
import os

import numpy as np

import cad_export as cx


def _n(v, d=2):
    """Format angka gaya Indonesia: 1.234,56"""
    s = f"{v:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


# ============================================================================ model dokumen
def susun(cfg, s, out):
    lb = cfg["lembar"]
    u = cfg["unit_terbesar"]
    kr = cfg["_kriteria"]
    g = s["geometri"]
    fig = _gambar_laporan(cfg, s, out)
    B = []
    add = B.append
    tgl = _dt.date.today().strftime("%d-%m-%Y")
    nomor = f"{lb['nomor_gambar']}-LAP"

    add(("judul", dict(judul="LAPORAN PERENCANAAN JALAN TAMBANG", sub=cfg["proyek"], perusahaan=cfg.get("perusahaan") or "-",
                       iup=lb.get("nomor_iup") or "-", lokasi=lb.get("lokasi") or "-", nomor=nomor, revisi=lb["revisi"], tanggal=tgl)))
    add(("pengesahan", lb.get("pengesahan") or []))
    add(("toc", None))

    add(("h1", "BAB 1  PENDAHULUAN"))
    add(("h2", "1.1  Latar Belakang"))
    add(("p", f"Jalan tambang {cfg['alinyemen'].get('nama', '')} direncanakan sebagai jalan angkut sepanjang {_n(s['panjang_m'])} m "
              f"(STA {cx.fmt_sta(s['sta_awal'])} s.d. {cx.fmt_sta(s['sta_akhir'])}). Perencanaan wajib memenuhi kaidah teknik pertambangan yang baik "
              "sebagaimana Keputusan Menteri ESDM Nomor 1827 K/30/MEM/2018, khususnya ketentuan jalan pertambangan (hal. 99-100) dan "
              "perencanaan pengangkutan (hal. 66-67)."))
    add(("h2", "1.2  Maksud dan Tujuan"))
    add(("ul", ["Menetapkan geometri jalan (alinyemen horizontal, vertikal, dan penampang melintang) yang aman bagi unit angkut terbesar.",
                "Menghitung volume pekerjaan tanah (galian, timbunan, perkerasan).",
                "Memeriksa kepatuhan terhadap Kepmen ESDM 1827 K/30/MEM/2018 dan praktik rekayasa yang diakui.",
                "Menyiapkan gambar rencana dan data digital (LandXML/DXF) untuk pelaksanaan dan pengesahan KTT."]))
    add(("h2", "1.3  Lokasi dan Lingkup"))
    add(("table", ["Uraian", "Keterangan"], [["Perusahaan", cfg.get("perusahaan") or "-"], ["Nomor IUP", lb.get("nomor_iup") or "-"],
                                             ["Lokasi", lb.get("lokasi") or "-"], ["Sistem koordinat", lb["sistem_koordinat"]],
                                             ["Trase", f"{cfg['alinyemen'].get('nama', '')}: STA {cx.fmt_sta(s['sta_awal'])} - {cx.fmt_sta(s['sta_akhir'])}"],
                                             ["Panjang", f"{_n(s['panjang_m'])} m"], ["Jumlah jalur", f"{cfg['jumlah_jalur']}"],
                                             ["Kecepatan rencana", f"{cfg['kecepatan_rencana_kmh']:.0f} km/jam"]], [0.35, 0.65]))
    add(("img", fig["situasi"], "Gambar 1.1  Situasi trase jalan"))
    add(("h2", "1.4  Dasar Acuan"))
    add(("ul", ["Peraturan Menteri ESDM Nomor 26 Tahun 2018 tentang Pelaksanaan Kaidah Pertambangan yang Baik dan Pengawasan Pertambangan Minerba.",
                "Keputusan Menteri ESDM Nomor 1827 K/30/MEM/2018 tentang Pedoman Pelaksanaan Kaidah Teknik Pertambangan yang Baik.",
                "AASHTO, A Policy on Geometric Design of Highways and Streets (praktik rekayasa: radius, superelevasi, jarak pandang, lengkung vertikal).",
                "Kaufman & Ault, Design of Surface Mine Haulage Roads, USBM IC 8758 (praktik rekayasa: lebar tikungan, tebal perkerasan).",
                "SNI 1726 (beban gempa) untuk koefisien seismik analisis lereng."]))

    add(("h1", "BAB 2  DATA DAN ASUMSI"))
    add(("h2", "2.1  Data Topografi"))
    add(("p", f"Sumber topografi: {lb['sumber_topografi']}. Kepmen 1827 mensyaratkan peta topografi skala 1:2.000 dengan akurasi 1 m "
              "(hal. 50); gambar rencana plan & profile disusun pada skala horizontal "
              f"1:{_n(lb['skala_horizontal'], 0)}."))
    add(("h2", "2.2  Unit Angkut Terbesar"))
    add(("table", ["Parameter", "Nilai"], [["Model", u["nama"]], ["Lebar unit", f"{u['lebar_m']} m"], ["Diameter roda", f"{u['diameter_roda_m']} m"],
                                           ["Lebar roda", f"{u['lebar_roda_m']} m"], ["Jarak jejak roda", f"{u['jarak_jejak_roda_m']} m"],
                                           ["Wheelbase", f"{u['wheelbase_m']} m"], ["Juntai depan / belakang", f"{u['juntai_depan_m']} / {u['juntai_belakang_m']} m"],
                                           ["Berat kotor (GVW)", f"{u['gvw_ton']} t"], ["Tinggi mata pengemudi", f"{u['tinggi_mata_pengemudi_m']} m"]], [0.45, 0.55]))
    add(("h2", "2.3  Parameter Desain"))
    sal, tg, gl, tm = cfg["saluran"], cfg["tanggul"], cfg["galian"], cfg["timbunan"]
    add(("table", ["Parameter", "Nilai"], [
        ["Tipe penampang", cfg.get("penampang", {}).get("tipe", "adaptif")],
        ["Gesekan samping f / superelevasi maks", f"{cfg['gesekan_samping_f']} / {cfg['superelevasi_maks'] * 100:.0f}%"],
        ["Grade maksimum desain", f"{cfg['grade_maks_desain'] * 100:.1f}%"],
        ["Kemiringan melintang", f"{max(cfg['kemiringan_melintang'], 0.02) * 100:.1f}%"],
        ["Saluran (dasar x dalam, sisi)", f"{sal['lebar_dasar_m']} x {sal['dalam_m']} m, {sal['kemiringan_sisi_HV']}H:1V"],
        ["Intensitas hujan rencana", f"{sal['intensitas_hujan_mm_jam']} mm/jam"],
        ["Lereng galian", f"{gl['kemiringan_HV']}H:1V, jenjang {gl['lebar_jenjang_m']} m tiap {gl['tinggi_jenjang_m']} m"],
        ["Lereng timbunan", f"{tm['kemiringan_HV']}H:1V, jenjang {tm['lebar_jenjang_m']} m tiap {tm['tinggi_jenjang_m']} m"],
        ["Lapis perkerasan", f"{cfg['lapis_perkerasan']['tebal_m']} m {cfg['lapis_perkerasan']['material']} (CBR tanah dasar {cfg['lapis_perkerasan']['cbr_tanah_dasar']}%)"],
        ["Interval penampang hitungan / gambar", f"{cfg['interval_penampang_m']:g} m / {lb['interval_penampang_lembar_m']:g} m"]], [0.45, 0.55]))
    add(("h2", "2.4  Asumsi"))
    asum = ["Topografi dianggap mewakili kondisi lapangan terkini; perubahan kontur > 1 m memerlukan pembaruan desain.",
            "Spesifikasi unit angkut sesuai Tabel 2.2; bila unit terbesar berubah, lebar, tanggul, dan tikungan harus dihitung ulang."]
    if s.get("geoteknik", {}).get("aktif"):
        asum.append(f"Parameter geoteknik: {s['geoteknik']['status_parameter']}.")
    if cfg["topografi"].get("sumber") == "demo":
        asum.append("DATA DEMO (sintetis): seluruh angka hanya contoh, bukan data proyek.")
    add(("ul", asum))

    add(("h1", "BAB 3  KRITERIA DESAIN"))
    add(("p", "Ketentuan yang bersumber dari Kepmen ESDM 1827 K/30/MEM/2018 dicantumkan dengan nomor halaman. Ketentuan yang tidak diberi angka "
              "oleh Kepmen dihitung dengan metode rekayasa dan ditandai \"praktik rekayasa\"."))
    rows = [["Lebar jalan lurus", f">= {kr['lebar_jalan_dua_jalur_min_x_lebar_unit']} x lebar unit (2 jalur); >= {kr['lebar_jalan_satu_jalur_min_x_lebar_unit']} x (1 jalur)", "Kepmen hal. 99 (i)"],
            ["Tanggul pengaman", f">= {kr['tanggul_pengaman_min_x_diameter_roda']} x diameter roda terbesar", "Kepmen hal. 99 (ii)"],
            ["Drainase", "mampu mengalirkan debit limpasan tertinggi", "Kepmen hal. 99 (v)"],
            ["Kemiringan melintang", f">= {kr['kemiringan_melintang_min'] * 100:.0f}%", "Kepmen hal. 99 (vi)"],
            ["Kemiringan memanjang", f"<= {kr['grade_maks'] * 100:.0f}% (lebih: kajian teknis)", "Kepmen hal. 99 (vii), 100 (viii)"],
            ["Tikungan", "lebar, radius, superelevasi sesuai gaya kendaraan pada batas kecepatan", "Kepmen hal. 100 (ix)"],
            ["Daya dukung", "> beban statis unit terbesar bermuatan", "Kepmen hal. 100 (xi)"],
            ["Separator", f">= {kr['separator_tinggi_min_x_diameter_roda']} x D roda; lebar atas >= lebar roda", "Kepmen hal. 100 (xii)"],
            ["Persimpangan", f">= {kr['sudut_persimpangan_tiga_min_deg']:.0f} derajat", "Kepmen hal. 100 (xiii)"],
            ["Kapasitas jalan", ">= laju produksi + 25%", "Kepmen hal. 67"],
            ["Lereng galian/timbunan", "FK & PoF Tabel 1; timbunan dengan parameter residual", "Kepmen hal. 57-58"],
            ["Radius minimum", "R = V^2 / (127 (e + f))", "Praktik rekayasa (AASHTO)"],
            ["Lebar tikungan", "W = n(U + Fa + Fb + Z) + C; off-tracking", "Praktik rekayasa"],
            ["Jarak pandang henti & lengkung vertikal", "AASHTO", "Praktik rekayasa"],
            ["Tebal perkerasan", "kurva CBR", "Praktik rekayasa (Kaufman & Ault)"]]
    add(("table", ["Item", "Kriteria", "Dasar"], rows, [0.25, 0.45, 0.30]))

    add(("h1", "BAB 4  HASIL PERENCANAAN"))
    add(("h2", "4.1  Alinyemen Horizontal"))
    add(("p", f"Radius minimum untuk V = {cfg['kecepatan_rencana_kmh']:.0f} km/jam: R = V^2/(127(e+f)) = {cfg['kecepatan_rencana_kmh']:.0f}^2/(127 x ({cfg['superelevasi_maks']} + {cfg['gesekan_samping_f']})) = {_n(g['R_min'])} m."))
    add(("table", ["PI", "Arah", "R (m)", "Delta (deg)", "T (m)", "L (m)", "e", "W (m)", "STA PC", "STA PT"],
         [[str(c["pi_no"]), c["arah"], _n(c["radius"], 0), _n(c["delta_deg"]), _n(c["T"]), _n(c["L"]), f"{c.get('e', 0) * 100:.1f}%",
           _n(c.get("W", 0)), cx.fmt_sta(c["sta_pc"]), cx.fmt_sta(c["sta_pt"])] for c in s["tikungan"]] or [["-"] * 10], None))
    add(("h2", "4.2  Alinyemen Vertikal"))
    pv = s["pvi"]
    gr = s["grade_pct"]
    add(("table", ["Segmen", "Panjang (m)", "Grade"], [[f"{cx.fmt_sta(pv[i]['sta'])} - {cx.fmt_sta(pv[i + 1]['sta'])}", _n(pv[i + 1]['sta'] - pv[i]['sta']), f"{gr[i]:.2f}%"]
                                                      for i in range(len(gr))], [0.5, 0.25, 0.25]))
    add(("p", f"Jarak pandang henti (JPH) = 0,278 V t + V^2 / (254 (f - G)) = {_n(s['jarak_pandang_henti_m'])} m (praktik rekayasa)."))
    lv = [v for v in s["lengkung_vertikal"] if v["A_pct"] >= 0.5]
    if lv:
        add(("table", ["PVI", "Jenis", "A (%)", "L perlu (m)", "L desain (m)"],
             [[cx.fmt_sta(v["sta"]), v["jenis"], _n(v["A_pct"]), _n(v["L_perlu"], 1), _n(v["L_pakai"], 0)] for v in lv], None))
    add(("img", fig["profil"], "Gambar 4.1  Profil memanjang"))
    add(("h2", "4.3  Penampang Melintang"))
    add(("p", f"Lebar jalur lalu lintas lurus {_n(g['W_lurus'])} m (rumus L = n.Wt + (n+1)(0,5.Wt) = {_n(g['W_formula'])} m; minimum Kepmen {_n(g['W_min_kepmen'])} m). "
              f"Tanggul pengaman setinggi {_n(s['tanggul_tinggi_m'])} m. Kemiringan melintang {max(cfg['kemiringan_melintang'], 0.02) * 100:.1f}% (crown). "
              f"Tinggi galian maksimum {_n(s['h_galian_maks'])} m dan tinggi timbunan maksimum {_n(s['h_timbunan_maks'])} m."))
    add(("h2", "4.4  Drainase"))
    dr = s["drainase"]
    add(("p", f"Kapasitas saluran (Manning, n = {sal['manning_n']}, kemiringan dasar {dr['kemiringan_dasar_min'] * 100:.1f}%): Q = {_n(dr['Q_kapasitas_m3s'], 3)} m3/detik. "
              f"Debit rencana (rasional, C = {sal['koef_limpasan']}, I = {sal['intensitas_hujan_mm_jam']} mm/jam, panjang tangkapan {sal['panjang_ke_sump_m']:.0f} m): "
              f"Q = {_n(dr['Q_rencana_m3s'], 3)} m3/detik. Gorong-gorong/sump ditempatkan paling jauh setiap {sal['panjang_ke_sump_m']:.0f} m dan di setiap titik rendah profil."))
    add(("h2", "4.5  Perkerasan dan Daya Dukung"))
    tp = s["perkerasan"]
    add(("p", f"Beban roda {_n(tp['beban_roda_kg'], 0)} kg, tekanan ban {tp['tekanan_kontak_kpa']} kPa, CBR tanah dasar {tp['cbr_tanah_dasar']}% "
              f"-> tebal perlu {_n(tp['tebal_perlu_m'])} m; tebal rencana {_n(tp['tebal_rencana_m'])} m."))
    add(("h2", "4.6  Kestabilan Lereng Galian dan Timbunan"))
    geo = s.get("geoteknik", {})
    if geo.get("aktif") and geo.get("hasil"):
        add(("p", f"Analisis Bishop disederhanakan + Monte Carlo (PoF), CoF = {geo['cof']}, ru = {geo['ru']}, kh = {geo['kh']}. "
                  f"Parameter: {geo['status_parameter']}."))
        add(("table", ["Lereng", "STA", "H (m)", "Sudut", "FK statis", "FK dinamis", "PoF", "Syarat", "Status"],
             [[h["jenis"], cx.fmt_sta(h["sta"]), _n(h["tinggi"], 1), f"{h['sudut']:.1f} deg", _n(h["fk_statis"]), _n(h["fk_dinamis"]), f"{h['pof'] * 100:.1f}%",
               f">= {h['syarat']['fk_statis']} / {h['syarat']['fk_dinamis']} / <= {h['syarat']['pof_maks'] * 100:.0f}%", h["status"]] for h in geo["hasil"]], None))
        if fig.get("lereng"):
            add(("img", fig["lereng"], "Gambar 4.2  Bidang gelincir kritis lereng tertinggi"))
    else:
        add(("p", "Analisis lereng belum dilakukan (aktifkan geoteknik.aktif dan isi parameter hasil uji)."))
    add(("h2", "4.7  Volume Pekerjaan"))
    add(("table", ["Pekerjaan", "Volume (m3)", "Keterangan"], [
        ["Galian", _n(s["volume_galian_m3"]), f"average end area, penampang tiap {cfg['interval_penampang_m']:g} m (TIN: {_n(s['volume_galian_tin_m3'])})"],
        ["Timbunan", _n(s["volume_timbunan_m3"]), f"(TIN: {_n(s['volume_timbunan_tin_m3'])})"],
        ["Lapis perkerasan", _n(s["volume_perkerasan_m3"]), "lebar jalur x tebal x panjang"],
        ["Neraca", _n(s["volume_galian_m3"] * cfg["timbunan"]["faktor_susut"] - s["volume_timbunan_m3"]),
         f"galian x faktor susut {cfg['timbunan']['faktor_susut']} - timbunan (negatif = perlu material timbun dari luar)"]], [0.25, 0.25, 0.5]))
    add(("img", fig["masshaul"], "Gambar 4.3  Diagram mass-haul"))
    add(("img", fig["3d"], "Gambar 4.4  Model 3D koridor jalan"))

    add(("h1", "BAB 5  PEMERIKSAAN KEPATUHAN"))
    add(("table", ["No", "Item", "Nilai desain", "Syarat", "Status", "Dasar"],
         [[str(i), c["item"], c["nilai"], c["syarat"], c["status"], _dasar_pendek(c["dasar"])] for i, c in enumerate(s["pemeriksaan"], 1)],
         [0.05, 0.2, 0.18, 0.22, 0.12, 0.23]))

    add(("h1", "BAB 6  KESIMPULAN DAN REKOMENDASI"))
    gagal = [c for c in s["pemeriksaan"] if c["status"] != "MEMENUHI"]
    add(("h2", "6.1  Kesimpulan"))
    add(("p", ("Seluruh butir pemeriksaan memenuhi kriteria." if not gagal else
               f"Terdapat {len(gagal)} butir yang belum memenuhi kriteria dan wajib diperbaiki sebelum pengesahan.")))
    add(("h2", "6.2  Rekomendasi Perbaikan"))
    rek = [_rekomendasi(c, cfg) for c in gagal] or ["Tidak ada perbaikan geometri yang diperlukan berdasarkan data saat ini."]
    add(("ol", rek))
    add(("h2", "6.3  Pengendalian Keselamatan dan Pemantauan"))
    add(("ol", [f"Pasang rambu batas kecepatan {cfg['kecepatan_rencana_kmh']:.0f} km/jam, rambu tikungan, tanjakan/turunan, dan persimpangan.",
                "Inspeksi harian tanggul pengaman, saluran, dan permukaan jalan; perbaiki erosi, lubang, dan genangan.",
                "Pemantauan lereng galian/timbunan (inspeksi visual tiap shift saat hujan, patok/prisma geser untuk lereng tinggi).",
                "Penyiraman jalan untuk pengendalian debu dan pengaturan jarak antar unit.",
                "Verifikasi as-built (survei) setelah konstruksi dan sebelum jalan dioperasikan; dokumentasikan untuk KTT."]))
    add(("h1", "LAMPIRAN"))
    add(("h2", "A. Daftar Gambar"))
    add(("table", ["No", "Nomor gambar", "Judul"], [[str(d["no"]), d["nomor"], d["judul"]] for d in s.get("daftar_lembar", [])], [0.08, 0.22, 0.70]))
    add(("h2", "B. Daftar Berkas Digital"))
    add(("table", ["Berkas", "Isi"], [["gambar_perencanaan_jalan.pdf", "Paket gambar (situasi, plan & profile, penampang, volume)"],
                                      ["jalan.xml", "LandXML 1.2: alignment, profile, cross section, surface EG/FG/komposit"],
                                      ["jalan_plan.dxf / jalan_3d.dxf", "Denah 2D berlapis NCS / feature line & TIN 3D"],
                                      ["jalan_profil.dxf / jalan_penampang.dxf", "Profil memanjang / penampang melintang"],
                                      ["koridor.obj/.stl, komposit.obj", "Model 3D"], ["volume.csv, titik_koridor.csv", "Volume per stasiun, titik PENZD"],
                                      ["laporan.json", "Data perhitungan lengkap"]], [0.4, 0.6]))
    add(("p", "Hasil perencanaan ini adalah alat bantu teknis. Pengesahan dan keputusan pelaksanaan tetap berada pada Kepala Teknik Tambang (KTT)."))
    return B


def _dasar_pendek(t):
    """'hal. 99 butir (i): lebar ...' -> 'Kepmen 1827 hal. 99 (i)'"""
    if t.startswith("hal."):
        head = t.split(":")[0].replace(" butir", "")
        return "Kepmen 1827 " + head
    return t


def _rekomendasi(c, cfg):
    it = c["item"].lower()
    if "lebar" in it:
        return f"{c['item']}: perlebar jalur hingga memenuhi {c['syarat']}."
    if "tikungan" in it:
        return f"{c['item']}: perbesar radius, tambah superelevasi (maks {cfg['superelevasi_maks'] * 100:.0f}%), atau turunkan batas kecepatan di tikungan dengan rambu."
    if "tanggul" in it:
        return f"{c['item']}: tinggikan tanggul hingga {c['syarat']}."
    if "grade" in it or "memanjang" in it:
        return f"{c['item']}: landaikan trase (perpanjang/switchback) atau lakukan kajian teknis (hal. 100 viii) termasuk jalur penyelamat dan uji kemampuan rem unit."
    if "saluran" in it or "drainase" in it:
        return f"{c['item']}: perbesar dimensi saluran, perapat gorong-gorong/sump, dan atur kemiringan dasar >= 0,5%."
    if "perkerasan" in it or "daya dukung" in it:
        return f"{c['item']}: pertebal lapis perkerasan atau perbaiki tanah dasar; verifikasi dengan uji CBR/DCP."
    if "lereng" in it:
        return f"{c['item']}: landaikan lereng, perlebar jenjang, kendalikan air (drainase lereng, ru), atau perkuatan; lakukan uji laboratorium untuk parameter aktual."
    if "lengkung vertikal" in it:
        return f"{c['item']}: perpanjang lengkung vertikal atau batasi kecepatan dan pasang rambu di puncak."
    return f"{c['item']}: perbaiki hingga {c['syarat']}."


# ============================================================================ gambar laporan
def _gambar_laporan(cfg, s, out):
    import json
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    d = os.path.join(out, "laporan_gambar")
    os.makedirs(d, exist_ok=True)
    j = json.load(open(os.path.join(out, "laporan.json"))) if os.path.exists(os.path.join(out, "laporan.json")) else s
    fig = {}
    import csv
    rows = list(csv.DictReader(open(os.path.join(out, "volume.csv"))))
    sta = np.array([float(r["sta"]) for r in rows]); elev = np.array([float(r["elev_cl"]) for r in rows])
    pts = np.loadtxt(os.path.join(out, "titik_koridor.csv"), delimiter=",", skiprows=1, usecols=(1, 2, 3))
    # situasi
    f, ax = plt.subplots(figsize=(7, 4.2))
    ax.scatter(pts[:, 0], pts[:, 1], s=0.3, c=pts[:, 2], cmap="terrain")
    ax.set_aspect("equal"); ax.grid(lw=0.2); ax.set_xlabel("Easting (m)"); ax.set_ylabel("Northing (m)")
    ax.set_title("Situasi koridor jalan (warna = elevasi desain)", fontsize=8)
    ax.tick_params(labelsize=6)
    p = os.path.join(d, "situasi.png"); f.tight_layout(); f.savefig(p, dpi=170); plt.close(f); fig["situasi"] = p
    # profil
    f, ax = plt.subplots(figsize=(7, 2.8))
    pv = s["pvi"]
    ax.plot([v["sta"] for v in pv], [v["elev"] for v in pv], "o-", ms=2, lw=0.8, c="#1f4e9c", label="PVI / desain")
    ax.plot(sta, elev, lw=0.6, c="#1f4e9c")
    ax.set_xlabel("Stasiun (m)", fontsize=7); ax.set_ylabel("Elevasi (m)", fontsize=7); ax.grid(lw=0.2); ax.tick_params(labelsize=6)
    for i, gg in enumerate(s["grade_pct"]):
        xm = (pv[i]["sta"] + pv[i + 1]["sta"]) / 2; ym = (pv[i]["elev"] + pv[i + 1]["elev"]) / 2
        ax.text(xm, ym, f"{gg:.2f}%", fontsize=5.5, ha="center", va="bottom")
    p = os.path.join(d, "profil.png"); f.tight_layout(); f.savefig(p, dpi=170); plt.close(f); fig["profil"] = p
    # mass haul
    f, ax = plt.subplots(figsize=(7, 2.4))
    ax.plot(sta, [float(r["kumulatif_massa"]) for r in rows], c="#111", lw=0.9); ax.axhline(0, c="#999", lw=0.5)
    ax.set_xlabel("Stasiun (m)", fontsize=7); ax.set_ylabel("Kumulatif (m3)", fontsize=7); ax.grid(lw=0.2); ax.tick_params(labelsize=6)
    p = os.path.join(d, "masshaul.png"); f.tight_layout(); f.savefig(p, dpi=170); plt.close(f); fig["masshaul"] = p
    # 3D
    f = plt.figure(figsize=(7, 4)); ax = f.add_subplot(projection="3d")
    ax.scatter(pts[:, 0], pts[:, 1], pts[:, 2], s=0.4, c=pts[:, 2], cmap="terrain")
    ax.set_box_aspect((np.ptp(pts[:, 0]), np.ptp(pts[:, 1]), max(np.ptp(pts[:, 2]) * 3, 1))); ax.tick_params(labelsize=5)
    ax.view_init(30, -60)
    p = os.path.join(d, "koridor3d.png"); f.tight_layout(); f.savefig(p, dpi=170); plt.close(f); fig["3d"] = p
    # lereng
    geo = s.get("geoteknik", {})
    if geo.get("aktif") and geo.get("hasil"):
        n = len(geo["hasil"])
        f, axs = plt.subplots(1, n, figsize=(7, 2.8)); axs = np.atleast_1d(axs)
        for a, h in zip(axs, geo["hasil"]):
            xz = np.array(h["xz"])
            a.fill_between(xz[:, 0], xz[:, 1], xz[:, 1].min() - 5, color="#e4ddd0"); a.plot(xz[:, 0], xz[:, 1], c="#111", lw=0.8)
            if h["lingkaran"]:
                xc, zc, R = h["lingkaran"]
                t = np.linspace(0, 2 * np.pi, 400); xx, zz = xc + R * np.cos(t), zc + R * np.sin(t)
                mm = zz <= np.interp(xx, xz[:, 0], xz[:, 1])
                a.plot(np.where(mm, xx, np.nan), np.where(mm, zz, np.nan), c="#c0392b", lw=1)
            a.set_aspect("equal", adjustable="datalim"); a.tick_params(labelsize=5)
            a.set_title(f"{h['jenis']} H={h['tinggi']:.1f} m: FKs {h['fk_statis']:.2f}, PoF {h['pof'] * 100:.1f}%", fontsize=6.5)
        p = os.path.join(d, "lereng.png"); f.tight_layout(); f.savefig(p, dpi=170); plt.close(f); fig["lereng"] = p
    return fig


# ============================================================================ renderer
def ke_md(B, path):
    L = []
    for blk in B:
        kind, v = blk[0], (blk[1] if len(blk) == 2 else blk[1:])
        if kind == "judul":
            L += [f"# {v['judul']}", "", f"**{v['sub']}**", "", f"{v['perusahaan']} | IUP {v['iup']} | {v['lokasi']}", "",
                  f"No. dokumen {v['nomor']} | Revisi {v['revisi']} | {v['tanggal']}", ""]
        elif kind == "pengesahan":
            L += ["## LEMBAR PENGESAHAN", "", "| " + " | ".join(j for j, _ in v) + " |", "|" + "---|" * len(v),
                  "| " + " | ".join((n or "( ............ )") for _, n in v) + " |", ""]
        elif kind == "toc":
            continue
        elif kind == "h1":
            L += [f"## {v}", ""]
        elif kind == "h2":
            L += [f"### {v}", ""]
        elif kind == "p":
            L += [v, ""]
        elif kind in ("ul", "ol"):
            L += [(f"{i}. " if kind == "ol" else "- ") + t for i, t in enumerate(v, 1)] + [""]
        elif kind == "table":
            h, rows, _ = v[0], v[1], v[2] if len(v) > 2 else None
            L += ["| " + " | ".join(h) + " |", "|" + "---|" * len(h)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows] + [""]
        elif kind == "img":
            L += [f"![{v[1]}]({os.path.relpath(v[0], os.path.dirname(path))})", "", f"*{v[1]}*", ""]
    open(path, "w").write("\n".join(L) + "\n")
    return path


def ke_docx(B, path, cfg):
    try:
        import docx
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.shared import Cm, Pt
    except Exception:
        return None
    D = docx.Document()
    sec = D.sections[0]
    sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
    sec.left_margin = Cm(3); sec.right_margin = Cm(2); sec.top_margin = Cm(2.5); sec.bottom_margin = Cm(2.5)
    st = D.styles["Normal"]; st.font.name = "Arial"; st.font.size = Pt(10.5)
    hdr = sec.header.paragraphs[0]; hdr.text = f"{cfg.get('perusahaan') or ''}  |  Laporan Perencanaan Jalan Tambang"
    hdr.runs[0].font.size = Pt(8)
    for blk in B:
        kind, v = blk[0], (blk[1] if len(blk) == 2 else blk[1:])
        if kind == "judul":
            for _ in range(5):
                D.add_paragraph()
            for txt, sz, b in ((v["judul"], 20, True), (v["sub"], 13, False), ("", 10, False), (v["perusahaan"], 14, True),
                               (f"IUP: {v['iup']}", 10, False), (f"Lokasi: {v['lokasi']}", 10, False), ("", 10, False),
                               (f"No. dokumen {v['nomor']}  |  Revisi {v['revisi']}  |  {v['tanggal']}", 9, False)):
                p = D.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r = p.add_run(txt); r.font.size = Pt(sz); r.bold = b
            D.add_page_break()
        elif kind == "pengesahan":
            p = D.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; r = p.add_run("LEMBAR PENGESAHAN"); r.bold = True; r.font.size = Pt(13)
            t = D.add_table(rows=3, cols=len(v)); t.style = "Table Grid"
            for i, (j, n) in enumerate(v):
                t.cell(0, i).text = j; t.cell(1, i).text = "\n\n\n"; t.cell(2, i).text = n or "( .................. )"
            D.add_page_break()
        elif kind == "toc":
            continue
        elif kind == "h1":
            D.add_heading(v, level=1)
        elif kind == "h2":
            D.add_heading(v, level=2)
        elif kind == "p":
            D.add_paragraph(v)
        elif kind == "ul":
            for t_ in v:
                D.add_paragraph(t_, style="List Bullet")
        elif kind == "ol":
            for t_ in v:
                D.add_paragraph(t_, style="List Number")
        elif kind == "table":
            h, rows = v[0], v[1]
            t = D.add_table(rows=1, cols=len(h)); t.style = "Table Grid"
            for i, x in enumerate(h):
                t.rows[0].cells[i].text = x
                for r in t.rows[0].cells[i].paragraphs[0].runs:
                    r.bold = True; r.font.size = Pt(8.5)
            for row in rows:
                cells = t.add_row().cells
                for i, x in enumerate(row):
                    cells[i].text = str(x)
                    for r in cells[i].paragraphs[0].runs:
                        r.font.size = Pt(8.5)
            D.add_paragraph()
        elif kind == "img":
            D.add_picture(v[0], width=Cm(15.5))
            p = D.add_paragraph(v[1]); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.runs[0].italic = True; p.runs[0].font.size = Pt(9)
    D.save(path)
    return path


def ke_pdf(B, path, cfg):
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (Image, ListFlowable, ListItem, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                        TableStyle)
        from reportlab.platypus.tableofcontents import TableOfContents
    except Exception:
        return None
    ss = getSampleStyleSheet()
    body = ParagraphStyle("b", parent=ss["Normal"], fontName="Helvetica", fontSize=9.5, leading=13.5, spaceAfter=5, alignment=4)
    cell = ParagraphStyle("c", parent=body, fontSize=7.6, leading=9.4, spaceAfter=0, alignment=0)
    cellb = ParagraphStyle("cb", parent=cell, fontName="Helvetica-Bold")
    h1 = ParagraphStyle("h1", parent=ss["Heading1"], fontName="Helvetica-Bold", fontSize=13, spaceBefore=6, spaceAfter=8)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=10.5, spaceBefore=8, spaceAfter=4)
    cap = ParagraphStyle("cap", parent=body, fontSize=8, alignment=TA_CENTER, textColor=colors.HexColor("#444444"))
    title = ParagraphStyle("t", parent=body, fontName="Helvetica-Bold", fontSize=20, leading=26, alignment=TA_CENTER)
    center = ParagraphStyle("ctr", parent=body, alignment=TA_CENTER)

    class Doc(SimpleDocTemplate):
        def afterFlowable(self, f):
            if isinstance(f, Paragraph) and f.style.name in ("h1", "h2"):
                self.notify("TOCEntry", (0 if f.style.name == "h1" else 1, f.getPlainText(), self.page))

    W = A4[0] - 5 * cm
    doc = Doc(path, pagesize=A4, leftMargin=3 * cm, rightMargin=2 * cm, topMargin=2.5 * cm, bottomMargin=2.2 * cm,
              title="Laporan Perencanaan Jalan Tambang", author=cfg.get("perusahaan", ""))
    nomor = [""]

    def deco(c, d):
        if d.page == 1:
            return
        c.saveState(); c.setFont("Helvetica", 7.5); c.setFillColor(colors.HexColor("#555555"))
        c.drawString(3 * cm, A4[1] - 1.5 * cm, f"{cfg.get('perusahaan') or ''}  |  Laporan Perencanaan Jalan Tambang")
        c.drawRightString(A4[0] - 2 * cm, A4[1] - 1.5 * cm, nomor[0])
        c.line(3 * cm, A4[1] - 1.65 * cm, A4[0] - 2 * cm, A4[1] - 1.65 * cm)
        c.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Halaman {d.page}")
        c.restoreState()

    F = []
    for blk in B:
        kind, v = blk[0], (blk[1] if len(blk) == 2 else blk[1:])
        if kind == "judul":
            nomor[0] = f"No. {v['nomor']} Rev {v['revisi']}"
            F += [Spacer(1, 4.5 * cm), Paragraph(v["judul"], title), Spacer(1, 0.4 * cm), Paragraph(v["sub"], center), Spacer(1, 3 * cm),
                  Paragraph(f"<b>{v['perusahaan']}</b>", ParagraphStyle("p2", parent=center, fontSize=14, leading=18)),
                  Paragraph(f"IUP: {v['iup']}<br/>Lokasi: {v['lokasi']}", center), Spacer(1, 4 * cm),
                  Paragraph(f"No. dokumen {v['nomor']}  |  Revisi {v['revisi']}  |  {v['tanggal']}", center), PageBreak()]
        elif kind == "pengesahan":
            F += [Paragraph("LEMBAR PENGESAHAN", ParagraphStyle("pg", parent=h1, alignment=TA_CENTER)), Spacer(1, 0.6 * cm)]
            data = [[Paragraph(f"<b>{j}</b>", ParagraphStyle("x", parent=cell, alignment=TA_CENTER)) for j, _ in v],
                    ["" for _ in v], [Paragraph(n or "( .................. )", ParagraphStyle("y", parent=cell, alignment=TA_CENTER)) for _, n in v],
                    [Paragraph("Tanggal: ..........", ParagraphStyle("z", parent=cell, alignment=TA_CENTER)) for _ in v]]
            t = Table(data, colWidths=[W / len(v)] * len(v), rowHeights=[0.8 * cm, 2.6 * cm, 0.8 * cm, 0.7 * cm])
            t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
            F += [t, Spacer(1, 0.8 * cm), Paragraph("Dokumen ini disusun sebagai alat bantu teknis dan berlaku setelah disahkan oleh Kepala Teknik Tambang (KTT).", body), PageBreak()]
        elif kind == "toc":
            toc = TableOfContents()
            toc.levelStyles = [ParagraphStyle("t1", fontName="Helvetica-Bold", fontSize=9.5, leftIndent=0, leading=14),
                               ParagraphStyle("t2", fontName="Helvetica", fontSize=9, leftIndent=14, leading=12)]
            F += [Paragraph("DAFTAR ISI", ParagraphStyle("di", parent=h1, alignment=TA_CENTER)), toc, PageBreak()]
        elif kind == "h1":
            if F and not isinstance(F[-1], PageBreak):
                F.append(PageBreak())
            F.append(Paragraph(v, h1))
        elif kind == "h2":
            F.append(Paragraph(v, h2))
        elif kind == "p":
            F.append(Paragraph(v, body))
        elif kind in ("ul", "ol"):
            F.append(ListFlowable([ListItem(Paragraph(t_, body), leftIndent=12) for t_ in v],
                                  bulletType="1" if kind == "ol" else "bullet", start="1" if kind == "ol" else None, leftIndent=14, bulletFontSize=8))
        elif kind == "table":
            h, rows, cw = v[0], v[1], (v[2] if len(v) > 2 else None)
            cw = [W * c for c in cw] if cw else [W / len(h)] * len(h)
            data = [[Paragraph(x, cellb) for x in h]] + [[Paragraph(str(x), cell) for x in r] for r in rows]
            t = Table(data, colWidths=cw, repeatRows=1)
            sty = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#555555")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8ecef")),
                   ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]
            for ri, r in enumerate(rows, 1):
                for ci, x in enumerate(r):
                    if str(x) == "TIDAK MEMENUHI":
                        sty.append(("TEXTCOLOR", (ci, ri), (ci, ri), colors.HexColor("#b3261e")))
                        sty.append(("BACKGROUND", (ci, ri), (ci, ri), colors.HexColor("#fbe9e7")))
            t.setStyle(TableStyle(sty))
            F += [t, Spacer(1, 0.3 * cm)]
        elif kind == "img":
            from PIL import Image as PImage
            iw, ih = PImage.open(v[0]).size
            from reportlab.platypus import KeepTogether
            hmax = 12 * cm
            w = min(W, hmax * iw / ih)
            F.append(KeepTogether([Image(v[0], width=w, height=w * ih / iw), Paragraph(v[1], cap)]))
    doc.multiBuild(F, onLaterPages=deco, onFirstPage=deco)
    return path


def tulis(cfg, s, out):
    B = susun(cfg, s, out)
    files = {"md": ke_md(B, os.path.join(out, "laporan_perencanaan_jalan.md"))}
    p = ke_pdf(B, os.path.join(out, "laporan_perencanaan_jalan.pdf"), cfg)
    if p:
        files["pdf"] = p
    d = ke_docx(B, os.path.join(out, "laporan_perencanaan_jalan.docx"), cfg)
    if d:
        files["docx"] = d
    return {k: os.path.basename(v) for k, v in files.items()}
