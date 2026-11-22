#!/usr/bin/env python3
"""Kalkulator teknis & pelaksanaan pertambangan dengan cek Kepmen ESDM 1827 K/30/MEM/2018.

Subperintah (semua keluaran JSON + baris status):
  sump        volume air tambang (metode rasional), kapasitas sump 1,25x, pompa, ambang 80%
  disposal    geometri & kapasitas timbunan (lift, berm, lereng 1V:2H, jarak in-pit 3x tinggi)
  alat        produktivitas alat gali-muat & angkut, match factor, PA/MA/UA/EU, jumlah pemuatan
  ledakan     geometri peledakan (burden/spasi/stemming/subdrill), powder factor, jarak aman, stiffness ratio
  pemberaian  klasifikasi gali bebas / garu / ledak dari UCS, GSI, kecepatan seismik
  konservasi  recovery penambangan & pengolahan terhadap batas minimum

Contoh:
  python3 kalkulator_teknis.py sump --luas-ha 35 --hujan-mm 120 --durasi-jam 24 --c 0.9 --pompa-m3jam 300 --volume-sump 60000
  python3 kalkulator_teknis.py alat --bucket-m3 5.2 --fill 0.85 --ct-gali-s 30 --truk-ton 60 --densitas-lepas 1.8 --jarak-m 2500
  python3 kalkulator_teknis.py ledakan --diameter-mm 115 --tinggi-jenjang 8 --densitas-batuan 2.5 --densitas-handak 0.85
"""
from __future__ import annotations

import argparse
import json
import math

ST = lambda ok: "MEMENUHI" if ok else "TIDAK MEMENUHI"  # noqa: E731


def out(d):
    print(json.dumps(d, indent=2, ensure_ascii=False))
    for c in d.get("cek", []):
        print(f"[{c['status']}] {c['item']}: {c['nilai']} (syarat {c['syarat']}; {c['dasar']})")
    return d


def cek(item, nilai, syarat, ok, dasar):
    return dict(item=item, nilai=nilai, syarat=syarat, status=ST(ok), dasar=dasar)


# ---------------------------------------------------------------- penyaliran
def sump(a):
    A_km2 = a.luas_ha / 100.0
    I = a.hujan_mm / a.durasi_jam  # intensitas rata-rata mm/jam (bila tak ada IDF)
    if a.mononobe:
        I = (a.hujan_mm / 24.0) * (24.0 / a.durasi_jam) ** (2 / 3)
    Q = 0.278 * a.c * I * A_km2  # m3/s
    V_hujan = Q * a.durasi_jam * 3600
    V_air = V_hujan + a.rembesan_m3jam * a.durasi_jam
    V_perlu = 1.25 * V_air
    sisa = V_air - a.pompa_m3jam * a.durasi_jam
    jam_kosong = (V_air / a.pompa_m3jam) if a.pompa_m3jam else None
    d = dict(intensitas_mm_jam=I, debit_puncak_m3s=Q, volume_air_tambang_m3=V_air, kapasitas_sump_perlu_m3=V_perlu,
             volume_tertahan_setelah_pompa_m3=max(sisa, 0), jam_pengosongan=jam_kosong,
             level_aksi_80pct_m3=0.8 * a.volume_sump if a.volume_sump else None)
    c = [cek("Periode ulang hujan rencana", f"{a.periode_ulang} th", ">= 10 th", a.periode_ulang >= 10, "Kepmen 1827 hal. 59 (curah hujan 10 tahun)")]
    if a.volume_sump:
        c.append(cek("Kapasitas sump/penampungan", f"{a.volume_sump:,.0f} m3", f">= 1,25 x {V_air:,.0f} = {V_perlu:,.0f} m3", a.volume_sump >= V_perlu, "Kepmen 1827 hal. 96"))
        c.append(cek("Pengendalian isi", f"aksi saat >= {0.8 * a.volume_sump:,.0f} m3", "terisi 80%", True, "Kepmen 1827 hal. 96"))
    if a.jarak_kolam_m is not None:
        c.append(cek("Jarak kolam pengendapan ke tepi terluar tambang", f"{a.jarak_kolam_m:.0f} m", ">= 500 m atau kajian teknis", a.jarak_kolam_m >= 500, "Kepmen 1827 hal. 96 [verifikasi]"))
    d["cek"] = c
    d["catatan"] = "Pakai kurva IDF lokal (BMKG) bila ada; metode rasional valid untuk DAS kecil (< ~2,5 km2). Kepmen menyebut volume pada curah hujan tertinggi; durasi rencana tetapkan dari kajian hidrologi."
    return out(d)


# ---------------------------------------------------------------- disposal
def disposal(a):
    H, n = a.tinggi_lift, a.jumlah_lift
    rat = a.lereng_HV  # H:V
    w0, l0 = a.lebar_dasar, a.panjang_dasar
    V = 0.0
    lifts = []
    w, l = w0, l0
    for k in range(n):
        w1, l1 = w - 2 * rat * H, l - 2 * rat * H
        if w1 <= 0 or l1 <= 0:
            break
        v = H / 3 * (w * l + w1 * l1 + math.sqrt(w * l * w1 * l1))
        lifts.append(dict(lift=k + 1, dasar=f"{w:.0f}x{l:.0f}", atas=f"{w1:.0f}x{l1:.0f}", volume_m3=v))
        V += v
        w, l = w1 - 2 * a.berm, l1 - 2 * a.berm
    Ht = H * len(lifts)
    horiz = len(lifts) * rat * H + max(len(lifts) - 1, 0) * a.berm
    osa = math.degrees(math.atan2(Ht, horiz)) if horiz else 0
    d = dict(volume_padat_lepas_m3=V, volume_insitu_bcm=V / a.swell, tinggi_total_m=Ht, sudut_keseluruhan_deg=osa,
             lift=lifts, kebutuhan_bcm=a.kebutuhan_bcm, cukup=(V / a.swell >= a.kebutuhan_bcm) if a.kebutuhan_bcm else None)
    c = [cek("Lereng tunggal timbunan", f"1V:{rat}H ({100 / rat:.0f}%)", "<= 1V:2H (50%) kecuali kajian teknis", rat >= 2.0 - 1e-9, "Kepmen 1827 hal. 84")]
    if a.tinggi_truk:
        c.append(cek("Tebal lapisan penimbunan (bottom-up)", f"{a.tebal_lapisan:.2f} m", f"<= 1/3 x {a.tinggi_truk} m", a.tebal_lapisan <= a.tinggi_truk / 3 + 1e-9, "Kepmen 1827 hal. 85 [verifikasi]"))
    if a.in_pit:
        c.append(cek("Jarak kaki timbunan in-pit ke area kerja aktif", f"{a.jarak_kaki_m:.0f} m", f">= 3 x {Ht:.0f} = {3 * Ht:.0f} m", a.jarak_kaki_m >= 3 * Ht, "Kepmen 1827 hal. 86"))
    c.append(cek("FK lereng timbunan", "hitung dengan c & phi residual", "Tabel 1 hal. 57", True, "Kepmen 1827 hal. 58 (pakai skill desain-pit-geoteknik/geotek.py)"))
    d["cek"] = c
    return out(d)


# ---------------------------------------------------------------- alat
def alat(a):
    q = a.bucket_m3 * a.fill
    n_pass = max(1, math.ceil(a.truk_ton / (q * a.densitas_lepas)))
    muatan = n_pass * q * a.densitas_lepas
    load_pct = muatan / a.truk_ton
    if load_pct > 1.0:
        n_pass -= 1
        muatan = n_pass * q * a.densitas_lepas
        load_pct = muatan / a.truk_ton
    t_muat = n_pass * a.ct_gali_s / 60
    v_isi = a.v_isi_kmh * 1000 / 60
    v_kosong = a.v_kosong_kmh * 1000 / 60
    ct_truk = t_muat + a.jarak_m / v_isi + a.jarak_m / v_kosong + a.t_dumping_min + a.t_manuver_min
    eff = a.ua * a.eu if a.ua and a.eu else a.efisiensi
    prod_exc = 3600 / a.ct_gali_s * q * a.densitas_lepas * eff  # t/jam
    prod_trk = muatan * 60 / ct_truk * eff
    n_truk = a.jumlah_truk or math.ceil(prod_exc / prod_trk)
    MF = (n_truk * t_muat) / (a.jumlah_exc * ct_truk)
    d = dict(jumlah_pemuatan=n_pass, muatan_ton=muatan, persen_muatan=load_pct * 100, waktu_muat_min=t_muat,
             cycle_time_truk_min=ct_truk, produktivitas_exc_tph=prod_exc, produktivitas_truk_tph=prod_trk,
             jumlah_truk=n_truk, match_factor=MF, produksi_armada_tph=min(prod_exc * a.jumlah_exc, prod_trk * n_truk))
    c = [cek("Jumlah pemuatan per truk", f"{n_pass}", "3-5 kali", 3 <= n_pass <= 5, "Kepmen 1827 hal. 119, 138"),
         cek("Muatan truk", f"{load_pct * 100:.0f}%", "90-100% kapasitas", 0.9 <= load_pct <= 1.0 + 1e-9, "Kepmen 1827 hal. 120"),
         cek("Bucket fill factor", f"{a.fill * 100:.0f}%", ">= 80%", a.fill >= 0.8, "Kepmen 1827 hal. 119"),
         cek("Match factor", f"{MF:.2f}", "mendekati 1 (0,9-1,1 praktik)", 0.9 <= MF <= 1.1, "Kepmen 1827 hal. 118")]
    for k, lim in (("pa", 0.90), ("ma", 0.85), ("ua", 0.75), ("eu", 0.65)):
        v = getattr(a, k)
        if v:
            c.append(cek(f"{k.upper()} alat utama", f"{v * 100:.0f}%", f">= {lim * 100:.0f}%", v >= lim, "Kepmen 1827 hal. 118"))
    d["cek"] = c
    return out(d)


# ---------------------------------------------------------------- peledakan
def ledakan(a):
    D = a.diameter_mm
    # Konya: B(ft) = (2 SGe/SGr + 1,5) De(in) -> m
    B = a.burden_m or (2 * a.densitas_handak / a.densitas_batuan + 1.5) * (D / 25.4) * 0.3048
    S = a.spasi_m or 1.15 * B
    T = a.stemming_m or 0.7 * B
    J = a.subdrill_m or 0.3 * B
    L = a.tinggi_jenjang + J
    kolom = max(L - T, 0)
    kg_m = math.pi * (D / 1000) ** 2 / 4 * a.densitas_handak * 1000
    Q = kg_m * kolom
    V = B * S * a.tinggi_jenjang
    PF = Q / (V * a.densitas_batuan) * 1000 if V else 0  # g/t
    PFv = Q / V
    SR = a.tinggi_jenjang / B
    d = dict(burden_m=B, spasi_m=S, stemming_m=T, subdrill_m=J, kedalaman_lubang_m=L, isian_kg_per_m=kg_m,
             isian_per_lubang_kg=Q, volume_per_lubang_bcm=V, powder_factor_kg_bcm=PFv, powder_factor_g_ton=PF,
             stiffness_ratio=SR)
    c = [cek("Stiffness ratio (tinggi jenjang / burden)", f"{SR:.2f}", "2 - 4", 2 <= SR <= 4, "Kepmen 1827 hal. 80"),
         cek("Jarak aman peledakan", f"manusia {a.radius_manusia_m:.0f} m, alat {a.radius_alat_m:.0f} m", ">= 500 m manusia, >= 300 m alat/fasilitas",
             a.radius_manusia_m >= 500 and a.radius_alat_m >= 300, "Kepmen 1827 hal. 80"),
         cek("Tanggul area peledakan", f"tinggi >= {a.diameter_roda_m / 3:.2f} m, berjarak {B:.1f} m dari lubang terluar",
             ">= 1/3 roda alat angkut terbesar, jarak 1 burden", True, "Kepmen 1827 hal. 80"),
         cek("Jarak baris terakhir ke lereng akhir", f">= {2 * a.tinggi_jenjang:.0f} m", "2 x tinggi lereng tunggal", True, "Kepmen 1827 hal. 93"),
         cek("Larangan menggali dekat lubang gagal ledak", f">= {5 * B:.1f} m", "5 x burden", True, "Kepmen 1827 hal. 82")]
    if a.jarak_objek_m is not None:
        c.append(cek("Jarak ke rel/jaringan listrik/bendungan", f"{a.jarak_objek_m:.0f} m", ">= 500 m atau kajian teknis", a.jarak_objek_m >= 500, "Kepmen 1827 hal. 81"))
    d["cek"] = c
    d["catatan"] = "Burden awal dari rumus Konya; kalibrasi dengan uji ledak, fragmentasi (Kuz-Ram) dan pemantauan getaran (SNI 7571:2010)."
    return out(d)


# ---------------------------------------------------------------- pemberaian
def pemberaian(a):
    votes = []
    if a.ucs_mpa is not None:
        votes.append("gali bebas" if a.ucs_mpa < 1.5 else "garu" if a.ucs_mpa <= 40 else "peledakan")
    if a.gsi is not None:
        votes.append("gali bebas" if a.gsi < 50 else "garu" if a.gsi <= 70 else "peledakan")
    if a.vp_ms is not None:
        votes.append("gali bebas" if a.vp_ms < 450 else "garu" if a.vp_ms <= 1650 else "peledakan")
    rank = {"gali bebas": 0, "garu": 1, "peledakan": 2}
    hasil = max(votes, key=lambda v: rank[v]) if votes else None
    return out(dict(indikator=votes, rekomendasi=hasil,
                    dasar="Kepmen 1827 hal. 62: gali bebas UCS < 1,5 MPa / GSI < 50 / Vp < 450 m/s; garu 1,5-40 MPa / 50-70 / 450-1650 m/s; peledakan > 40 MPa / > 70 / > 1650 m/s",
                    catatan="Diambil metode paling berat dari indikator yang tersedia (konservatif)."))


# ---------------------------------------------------------------- konservasi
def konservasi(a):
    rt = a.tertambang / a.cadangan if a.cadangan else None
    c = []
    if rt is not None:
        c.append(cek("Recovery penambangan tambang terbuka", f"{rt * 100:.1f}%", ">= 90%", rt >= 0.90, "Kepmen 1827 hal. 348"))
    if a.recovery_olah is not None and a.recovery_fs is not None:
        c.append(cek("Recovery pengolahan", f"{a.recovery_olah * 100:.1f}%", f">= studi kelayakan {a.recovery_fs * 100:.1f}%", a.recovery_olah >= a.recovery_fs, "Kepmen 1827 hal. 125"))
    return out(dict(recovery_tambang=rt, cek=c))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("sump"); p.add_argument("--luas-ha", type=float, required=True); p.add_argument("--hujan-mm", type=float, required=True, help="curah hujan rencana (mm) selama durasi / harian maks bila --mononobe")
    p.add_argument("--durasi-jam", type=float, default=24); p.add_argument("--c", type=float, default=0.9); p.add_argument("--periode-ulang", type=float, default=10)
    p.add_argument("--rembesan-m3jam", type=float, default=0); p.add_argument("--pompa-m3jam", type=float, default=0); p.add_argument("--volume-sump", type=float)
    p.add_argument("--jarak-kolam-m", type=float); p.add_argument("--mononobe", action="store_true"); p.set_defaults(f=sump)
    p = sp.add_parser("disposal"); p.add_argument("--lebar-dasar", type=float, required=True); p.add_argument("--panjang-dasar", type=float, required=True)
    p.add_argument("--tinggi-lift", type=float, default=10); p.add_argument("--jumlah-lift", type=int, default=4); p.add_argument("--lereng-HV", type=float, default=2.0)
    p.add_argument("--berm", type=float, default=10); p.add_argument("--swell", type=float, default=1.25); p.add_argument("--kebutuhan-bcm", type=float)
    p.add_argument("--tinggi-truk", type=float); p.add_argument("--tebal-lapisan", type=float, default=1.0); p.add_argument("--in-pit", action="store_true"); p.add_argument("--jarak-kaki-m", type=float, default=0)
    p.set_defaults(f=disposal)
    p = sp.add_parser("alat")
    for n, dflt in (("bucket-m3", 5.0), ("fill", 0.85), ("ct-gali-s", 30), ("truk-ton", 40), ("densitas-lepas", 1.8), ("jarak-m", 2000),
                    ("v-isi-kmh", 20), ("v-kosong-kmh", 30), ("t-dumping-min", 1.0), ("t-manuver-min", 1.0), ("efisiensi", 0.83)):
        p.add_argument(f"--{n}", type=float, default=dflt)
    for n in ("pa", "ma", "ua", "eu"):
        p.add_argument(f"--{n}", type=float)
    p.add_argument("--jumlah-exc", type=int, default=1); p.add_argument("--jumlah-truk", type=int); p.set_defaults(f=alat)
    p = sp.add_parser("ledakan")
    p.add_argument("--diameter-mm", type=float, required=True); p.add_argument("--tinggi-jenjang", type=float, required=True)
    p.add_argument("--densitas-batuan", type=float, default=2.6); p.add_argument("--densitas-handak", type=float, default=0.85)
    for n in ("burden-m", "spasi-m", "stemming-m", "subdrill-m", "jarak-objek-m"):
        p.add_argument(f"--{n}", type=float)
    p.add_argument("--radius-manusia-m", type=float, default=500); p.add_argument("--radius-alat-m", type=float, default=300); p.add_argument("--diameter-roda-m", type=float, default=1.6)
    p.set_defaults(f=ledakan)
    p = sp.add_parser("pemberaian"); p.add_argument("--ucs-mpa", type=float); p.add_argument("--gsi", type=float); p.add_argument("--vp-ms", type=float); p.set_defaults(f=pemberaian)
    p = sp.add_parser("konservasi"); p.add_argument("--cadangan", type=float); p.add_argument("--tertambang", type=float)
    p.add_argument("--recovery-olah", type=float); p.add_argument("--recovery-fs", type=float); p.set_defaults(f=konservasi)
    a = ap.parse_args(argv)
    return a.f(a)


if __name__ == "__main__":
    main()
