#!/usr/bin/env python3
"""Desain jalan tambang (haul road) sesuai Kepmen ESDM 1827 K/30/MEM/2018 + praktik AASHTO.

Keluaran (folder --out):
  jalan.xml                LandXML 1.2: Alignment, Profile (EG & FG), CrossSects, Surface EG/Koridor/Komposit
  jalan_plan.dxf           Denah 2D: CL+stasiun, tepi jalur, tanggul, saluran, daylight, kontur EG & FG, tabel tikungan
  jalan_3d.dxf             Feature line 3D (POLYLINE 3D) + TIN koridor (3DFACE) + MESH
  jalan_profil.dxf         Profil memanjang (skala vertikal dibesarkan)
  jalan_penampang.dxf      Penampang melintang tersusun grid (seperti section view Civil 3D)
  koridor.obj / .stl       Mesh 3D koridor; komposit.obj permukaan akhir
  titik_koridor.csv        Titik PENZD
  volume.csv               Tabel luas & volume galian/timbunan per stasiun (average end area)
  lembar_gambar.pdf        Lembar denah, profil, penampang, 3D, diagram mass-haul, laporan kepatuhan
  laporan.md / laporan.json  Pemeriksaan kepatuhan Kepmen 1827 + perhitungan

Pakai:
  python3 haul_road.py --config contoh_jalan.json --out hasil/
  python3 haul_road.py --demo --out hasil/
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import sys
from dataclasses import dataclass

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cad_export as cx  # noqa: E402

KRITERIA_PATH = os.path.join(HERE, "..", "references", "kriteria_jalan_kepmen1827.json")

DEFAULT = {
    "proyek": "Jalan Tambang",
    "perusahaan": "",
    "epsg": None,
    "alinyemen": {"pi": [], "radius": [], "sta_awal": 0.0, "nama": "HR-01"},
    "unit_terbesar": {
        "nama": "isi model unit angkut terbesar",
        "lebar_m": 2.5,
        "diameter_roda_m": 1.08,
        "lebar_roda_m": 0.30,
        "jarak_jejak_roda_m": 2.05,
        "wheelbase_m": 4.6,
        "juntai_depan_m": 1.4,
        "juntai_belakang_m": 1.9,
        "gvw_ton": 41.0,
        "porsi_beban_gandar_belakang": 0.67,
        "jumlah_roda_belakang": 8,
        "tekanan_ban_kpa": 700,
        "tinggi_mata_pengemudi_m": 2.4,
    },
    "jumlah_jalur": 2,
    "kecepatan_rencana_kmh": 30.0,
    "gesekan_samping_f": 0.12,
    "superelevasi_maks": 0.05,
    "grade_maks_desain": 0.10,
    "beda_grade_maks": 0.06,
    "kemiringan_melintang": 0.03,
    "bahu_m": 0.5,
    "tanggul": {"rasio_tinggi_x_diameter": 0.75, "lebar_atas_m": 0.6, "kemiringan_sisi_HV": 1.5},
    "saluran": {"lebar_dasar_m": 0.6, "dalam_m": 0.6, "kemiringan_sisi_HV": 1.0, "manning_n": 0.03,
                 "intensitas_hujan_mm_jam": 100.0, "koef_limpasan": 0.9, "panjang_ke_sump_m": 200.0},
    "galian": {"kemiringan_HV": 1.0, "tinggi_jenjang_m": 5.0, "lebar_jenjang_m": 2.0},
    "timbunan": {"kemiringan_HV": 1.5, "tinggi_jenjang_m": 5.0, "lebar_jenjang_m": 2.0, "faktor_susut": 0.9},
    "lapis_perkerasan": {"tebal_m": 0.3, "material": "sirtu/laterit dipadatkan", "cbr_tanah_dasar": 6.0},
    "profil": {"mode": "otomatis", "jarak_pvi_m": 80.0, "elev_awal": None, "elev_akhir": None, "pvi": []},
    "jarak_pandang": {"waktu_reaksi_s": 2.5, "f_memanjang": 0.30, "tinggi_objek_m": 0.6},
    "interval_penampang_m": 20.0,
    "lebar_sampel_tanah_m": 60.0,
    "topografi": {"sumber": "demo"},
    "produksi_tph": None,
    "kapasitas_jalan_tph": None,
    "persimpangan_deg": [],
    "skala_vertikal_profil": 5.0,
    "penampang": {"tipe": "adaptif"},
    "geoteknik": {
        "aktif": True, "keparahan_longsor": "tinggi", "ru": 0.2, "kh": 0.10, "n_monte_carlo": 300,
        "status_parameter": "ASUMSI - ganti dengan hasil uji laboratorium",
        "material_galian": {"gamma": 19.0, "c": 40.0, "phi": 30.0, "sd_c": 8.0, "sd_phi": 2.5, "sd_gamma": 0.5},
        "material_timbunan": {"gamma": 19.0, "c": 10.0, "phi": 30.0, "sd_c": 3.0, "sd_phi": 2.0, "sd_gamma": 0.5},
    },
    "lembar": {
        "kertas": "A3",
        "skala_horizontal": 2000,
        "skala_vertikal": 400,
        "skala_penampang": 200,
        "interval_label_sta_m": 100,
        "interval_data_profil_m": 20,
        "interval_penampang_lembar_m": 100,
        "penampang_per_lembar": 2,
        "overlap_m": 20,
        "interval_grid_m": None,
        "ortofoto": None,
        "sistem_koordinat": "UTM Zona 51S, Datum WGS 84 (EPSG:32751)",
        "sumber_topografi": "isi: survei/foto udara, tanggal, akurasi",
        "nomor_gambar": "HR-01",
        "revisi": "0",
        "nomor_iup": "",
        "lokasi": "",
        "logo": None,
        "pengesahan": [["Digambar", ""], ["Diperiksa", ""], ["Disetujui (KTT)", ""]],
        "label_baris_profil": ["EXISTING ELEVATIONS", "PROPOSED ELEVATIONS", "STATION"],
    },
}


def deep_update(base, upd):
    for k, v in upd.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            deep_update(base[k], v)
        else:
            base[k] = v
    return base


def load_config(path=None, override=None):
    cfg = copy.deepcopy(DEFAULT)
    if path:
        with open(path) as f:
            deep_update(cfg, json.load(f))
    if override:
        deep_update(cfg, override)
    with open(KRITERIA_PATH) as f:
        cfg["_kriteria"] = json.load(f)
    return cfg


# =============================================================================== alinyemen horizontal
@dataclass
class Elem:
    type: str
    sta: float
    length: float
    start: np.ndarray
    end: np.ndarray
    center: np.ndarray | None = None
    radius: float = math.inf
    sgn: int = 0          # +1 belok kiri (ccw), -1 belok kanan (cw)
    delta: float = 0.0
    pi: np.ndarray | None = None
    theta0: float = 0.0


class HAlignment:
    def __init__(self, pis, radii, sta0=0.0):
        P = np.asarray(pis, float)
        n = len(P)
        if n < 2:
            raise ValueError("Minimal 2 titik PI (awal & akhir)")
        R = list(radii) + [0] * max(0, n - 2 - len(radii))
        self.P, self.sta0 = P, sta0
        self.curves = []
        self.warnings = []
        prev_end = P[0].copy()
        elems = []
        sta = sta0
        for i in range(1, n - 1):
            u1 = _unit(P[i] - P[i - 1])
            u2 = _unit(P[i + 1] - P[i])
            cross = u1[0] * u2[1] - u1[1] * u2[0]
            dot = float(np.clip(u1 @ u2, -1, 1))
            delta = abs(math.atan2(cross, dot))
            Ri = float(R[i - 1]) if i - 1 < len(R) else 0.0
            if Ri <= 0 or delta < 1e-6:
                continue
            T = Ri * math.tan(delta / 2)
            pc, pt = P[i] - u1 * T, P[i] + u2 * T
            avail_in = np.linalg.norm(pc - prev_end) * np.sign((pc - prev_end) @ u1)
            avail_out = (P[i + 1] - pt) @ u2
            if avail_in < -1e-6 or avail_out < -1e-6:
                self.warnings.append(f"PI{i}: tangen T={T:.1f} m tidak muat (radius {Ri} m terlalu besar)")
            sgn = 1 if cross > 0 else -1
            nrm = np.array([-u1[1], u1[0]]) * sgn
            c = pc + nrm * Ri
            Lc = Ri * delta
            Lt = float(np.linalg.norm(pc - prev_end))
            if Lt > 1e-6:
                elems.append(Elem("Line", sta, Lt, prev_end.copy(), pc.copy()))
                sta += Lt
            th0 = math.atan2(pc[1] - c[1], pc[0] - c[0])
            e = Elem("Curve", sta, Lc, pc.copy(), pt.copy(), c, Ri, sgn, delta, P[i].copy(), th0)
            elems.append(e)
            self.curves.append(dict(pi_no=i, pi=P[i].tolist(), radius=Ri, delta_deg=math.degrees(delta), T=T, L=Lc,
                                    sta_pc=sta, sta_pt=sta + Lc, arah="kiri" if sgn > 0 else "kanan", elem=e))
            sta += Lc
            prev_end = pt
        Lt = float(np.linalg.norm(P[-1] - prev_end))
        if Lt > 1e-6:
            elems.append(Elem("Line", sta, Lt, prev_end.copy(), P[-1].copy()))
            sta += Lt
        self.elems = elems
        self.sta_end = sta
        self.length = sta - sta0

    def at(self, s):
        """(xy, tangen unit, kelengkungan bertanda 1/R, elem)"""
        s = min(max(s, self.sta0), self.sta_end)
        for e in self.elems:
            if s <= e.sta + e.length + 1e-9:
                ds = s - e.sta
                if e.type == "Line":
                    t = _unit(e.end - e.start)
                    return e.start + t * ds, t, 0.0, e
                th = e.theta0 + e.sgn * ds / e.radius
                p = e.center + e.radius * np.array([math.cos(th), math.sin(th)])
                t = np.array([-math.sin(th), math.cos(th)]) * e.sgn
                return p, t, e.sgn / e.radius, e
        e = self.elems[-1]
        return e.end, _unit(e.end - e.start), 0.0, e

    def landxml_elements(self):
        out = []
        for e in self.elems:
            d = dict(type=e.type, sta=e.sta, length=e.length, start=tuple(e.start), end=tuple(e.end))
            if e.type == "Curve":
                d.update(center=tuple(e.center), radius=e.radius, rot="ccw" if e.sgn > 0 else "cw",
                         pi=tuple(e.pi), delta=e.delta)
            out.append(d)
        return out


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


# =============================================================================== perhitungan geometri
def geometri(cfg):
    u = cfg["unit_terbesar"]
    kr = cfg["_kriteria"]
    n = int(cfg["jumlah_jalur"])
    Wt = u["lebar_m"]
    W_formula = n * Wt + (n + 1) * 0.5 * Wt       # AASHTO: L = n.Wt + (n+1)(0,5.Wt)
    W_min_kepmen = (kr["lebar_jalan_dua_jalur_min_x_lebar_unit"] if n >= 2 else kr["lebar_jalan_satu_jalur_min_x_lebar_unit"]) * Wt
    W_lurus = max(W_formula, W_min_kepmen)
    V = cfg["kecepatan_rencana_kmh"]
    f = cfg["gesekan_samping_f"]
    emax = cfg["superelevasi_maks"]
    R_min = V ** 2 / (127 * (emax + f))
    tanggul_h = max(cfg["tanggul"]["rasio_tinggi_x_diameter"], kr["tanggul_pengaman_min_x_diameter_roda"]) * u["diameter_roda_m"]
    tanggul_h = max(tanggul_h, cfg["tanggul"].get("tinggi_m") or 0.0)
    sep_h = kr["separator_tinggi_min_x_diameter_roda"] * u["diameter_roda_m"]
    sep_w = max(kr["separator_lebar_atas_min_x_lebar_roda"] * u["lebar_roda_m"], 0.3)
    return dict(W_lurus=W_lurus, W_formula=W_formula, W_min_kepmen=W_min_kepmen, R_min=R_min,
                tanggul_tinggi=tanggul_h, separator_tinggi=sep_h, separator_lebar_atas=sep_w)


def lebar_tikungan(cfg, R):
    """Lebar jalan pada tikungan.
    (a) rumus buku teks tambang (AASHTO): W = n(U + Fa + Fb + Z) + C, Fa/Fb = juntai x sin(alpha), Z = C = 0,5(U+Fa+Fb)
    (b) lebar lurus + n x off-tracking (R - sqrt(R^2 - WB^2)).
    Diambil yang terbesar."""
    u = cfg["unit_terbesar"]
    n = int(cfg["jumlah_jalur"])
    U = u["jarak_jejak_roda_m"]
    sin_a = min(1.0, u["wheelbase_m"] / R)
    Fa = u["juntai_depan_m"] * sin_a
    Fb = u["juntai_belakang_m"] * sin_a
    Z = 0.5 * (U + Fa + Fb)
    C = Z
    Wa = n * (U + Fa + Fb + Z) + C
    off = R - math.sqrt(max(R ** 2 - u["wheelbase_m"] ** 2, 0))
    Wb = geometri(cfg)["W_lurus"] + n * off + n * u["lebar_m"] * 0.0
    return max(Wa, Wb), dict(W_rumus=Wa, W_offtracking=Wb, alpha_deg=math.degrees(math.asin(sin_a)), offtracking=off)


def superelevasi(cfg, R):
    V, f, emax = cfg["kecepatan_rencana_kmh"], cfg["gesekan_samping_f"], cfg["superelevasi_maks"]
    e_req = V ** 2 / (127 * R) - f
    return float(np.clip(e_req, 0.0, emax)), e_req


def jarak_pandang_henti(cfg, grade_turun):
    V = cfg["kecepatan_rencana_kmh"]
    jp = cfg["jarak_pandang"]
    return 0.278 * V * jp["waktu_reaksi_s"] + V ** 2 / (254 * max(jp["f_memanjang"] - abs(grade_turun), 0.05))


def panjang_lengkung_vertikal(cfg, A_pct, cembung, S):
    """AASHTO: cembung L = A S^2 / (200 (sqrt h1 + sqrt h2)^2) bila S<L, cekung L = A S^2 / (120 + 3,5 S)."""
    h1 = cfg["unit_terbesar"]["tinggi_mata_pengemudi_m"]
    h2 = cfg["jarak_pandang"]["tinggi_objek_m"]
    if cembung:
        L = A_pct * S ** 2 / (200 * (math.sqrt(h1) + math.sqrt(h2)) ** 2)
        if L < S:
            L = 2 * S - 200 * (math.sqrt(h1) + math.sqrt(h2)) ** 2 / max(A_pct, 1e-6)
    else:
        L = A_pct * S ** 2 / (120 + 3.5 * S)
        if L < S:
            L = 2 * S - (120 + 3.5 * S) / max(A_pct, 1e-6)
    return max(L, 0.0)


# =============================================================================== profil memanjang
class VProfile:
    def __init__(self, pvis):
        """pvis: list (sta, elev, L_lengkung)."""
        self.pvis = [(float(s), float(z), float(L or 0)) for s, z, L in pvis]

    def grades(self):
        p = self.pvis
        return [(p[i + 1][1] - p[i][1]) / (p[i + 1][0] - p[i][0]) for i in range(len(p) - 1)]

    def z(self, s):
        s = np.atleast_1d(np.asarray(s, float))
        S = np.array([p[0] for p in self.pvis])
        Z = np.array([p[1] for p in self.pvis])
        out = np.interp(s, S, Z)
        g = self.grades()
        for i in range(1, len(self.pvis) - 1):
            si, zi, L = self.pvis[i]
            if L <= 0:
                continue
            g1, g2 = g[i - 1], g[i]
            bvc = si - L / 2
            m = (s >= bvc) & (s <= si + L / 2)
            x = s[m] - bvc
            out[m] = (zi - g1 * L / 2) + g1 * x + (g2 - g1) / (2 * L) * x ** 2
        return out

    def grade_at(self, s, h=0.05):
        return float((self.z(s + h)[0] - self.z(s - h)[0]) / (2 * h))


def profil_otomatis(cfg, al: HAlignment, terrain: cx.Terrain):
    """Optimasi garis kemiringan (LP, solver HiGHS via scipy.optimize.linprog):
    min sum |z(s)-EG(s)|  s.t. |grade| <= grade_maks_desain, |delta grade| <= beda_grade_maks, ujung tetap (opsional)."""
    from scipy.optimize import linprog

    pc = cfg["profil"]
    gmax = min(cfg["grade_maks_desain"], cfg["_kriteria"]["grade_maks"]) if cfg["grade_maks_desain"] <= cfg["_kriteria"]["grade_maks"] else cfg["grade_maks_desain"]
    dA = cfg["beda_grade_maks"]
    L = al.length
    npv = max(2, int(round(L / pc["jarak_pvi_m"])) + 1)
    S = np.linspace(al.sta0, al.sta_end, npv)
    ss = np.arange(al.sta0, al.sta_end + 1e-6, 5.0)
    if ss[-1] < al.sta_end:
        ss = np.append(ss, al.sta_end)
    xy = np.array([al.at(s)[0] for s in ss])
    g = terrain.z(xy[:, 0], xy[:, 1])
    m = len(ss)
    # interpolasi linear antar PVI
    Wm = np.zeros((m, npv))
    idx = np.clip(np.searchsorted(S, ss, side="right") - 1, 0, npv - 2)
    t = (ss - S[idx]) / (S[idx + 1] - S[idx])
    Wm[np.arange(m), idx] = 1 - t
    Wm[np.arange(m), idx + 1] = t
    nv = npv + m
    c = np.concatenate([np.zeros(npv), np.ones(m)])
    A, b = [], []
    for j in range(m):  # z - g <= d ; g - z <= d
        r = np.zeros(nv); r[:npv] = Wm[j]; r[npv + j] = -1; A.append(r); b.append(g[j])
        r = np.zeros(nv); r[:npv] = -Wm[j]; r[npv + j] = -1; A.append(r); b.append(-g[j])
    for i in range(npv - 1):
        ds = S[i + 1] - S[i]
        r = np.zeros(nv); r[i + 1] = 1; r[i] = -1; A.append(r); b.append(gmax * ds)
        r = np.zeros(nv); r[i + 1] = -1; r[i] = 1; A.append(r); b.append(gmax * ds)
    for i in range(1, npv - 1):
        d1, d2 = S[i] - S[i - 1], S[i + 1] - S[i]
        r = np.zeros(nv); r[i + 1] = 1 / d2; r[i] = -1 / d2 - 1 / d1; r[i - 1] = 1 / d1
        A.append(r); b.append(dA); A.append(-r); b.append(dA)
    Aeq, beq = [], []
    for k, key in ((0, "elev_awal"), (npv - 1, "elev_akhir")):
        if pc.get(key) is not None:
            r = np.zeros(nv); r[k] = 1; Aeq.append(r); beq.append(float(pc[key]))
    res = linprog(c, A_ub=np.array(A), b_ub=np.array(b), A_eq=np.array(Aeq) if Aeq else None,
                  b_eq=np.array(beq) if beq else None, bounds=[(None, None)] * nv, method="highs")
    if not res.success:
        raise RuntimeError("Optimasi profil gagal (cek elevasi awal/akhir vs grade maksimum): " + res.message)
    Z = res.x[:npv]
    return S, Z


def susun_profil(cfg, al, terrain):
    pc = cfg["profil"]
    if pc["mode"] == "manual" and pc["pvi"]:
        S = np.array([p[0] for p in pc["pvi"]], float)
        Z = np.array([p[1] for p in pc["pvi"]], float)
    else:
        S, Z = profil_otomatis(cfg, al, terrain)
    grades = np.diff(Z) / np.diff(S)
    g_down = float(max(0.0, -grades.min())) if len(grades) else 0.0
    SSD = jarak_pandang_henti(cfg, g_down)
    pvis = [(S[0], Z[0], 0.0)]
    vc_info = []
    for i in range(1, len(S) - 1):
        g1, g2 = grades[i - 1], grades[i]
        A = abs(g2 - g1) * 100
        cembung = g2 < g1
        Lreq = panjang_lengkung_vertikal(cfg, A, cembung, SSD) if A > 0.2 else 0.0
        Lmax = 0.9 * min(S[i] - S[i - 1], S[i + 1] - S[i])
        Luse = min(max(Lreq, 0.0 if A <= 0.2 else 20.0), Lmax)
        Luse = round(Luse / 5) * 5 if Luse >= 5 else Luse
        pvis.append((S[i], Z[i], Luse))
        vc_info.append(dict(sta=float(S[i]), elev=float(Z[i]), A_pct=A, jenis="cembung" if cembung else "cekung",
                            L_perlu=Lreq, L_pakai=Luse, memenuhi=Luse + 1e-6 >= Lreq))
    pvis.append((S[-1], Z[-1], 0.0))
    return VProfile(pvis), dict(SSD=SSD, grade_turun_maks=g_down, lengkung=vc_info)


# =============================================================================== penampang melintang
def _path_daylight(o0, z0, side, ground_o, ground_z, up, ratio_HV, bench_h, bench_w, maxd=120.0):
    """Lereng dari (o0,z0) ke arah 'side' (+1 kanan, -1 kiri), naik (galian) atau turun (timbunan),
    dengan jenjang tiap bench_h. Return list titik (offset, z, kode) sampai memotong tanah."""
    pts = []
    o, z = o0, z0
    sgn_z = 1 if up else -1
    def gz(oo):
        return float(np.interp(oo, ground_o, ground_z))
    for k in range(60):
        dz = bench_h if bench_h and bench_h > 0 else maxd
        o1, z1 = o + side * ratio_HV * dz, z + sgn_z * dz
        f0, f1 = (z - gz(o)) * sgn_z, (z1 - gz(o1)) * sgn_z
        if f1 >= 0 or abs(o1 - o0) > maxd:
            # cari potong dengan bisection
            lo, hi = 0.0, 1.0
            for _ in range(40):
                mid = (lo + hi) / 2
                om, zm = o + (o1 - o) * mid, z + (z1 - z) * mid
                if (zm - gz(om)) * sgn_z >= 0:
                    hi = mid
                else:
                    lo = mid
            om, zm = o + (o1 - o) * hi, z + (z1 - z) * hi
            pts.append((om, zm, "DAYL"))
            return pts
        pts.append((o1, z1, "BNCH_TOE" if up else "BNCH_CRS"))
        o2 = o1 + side * bench_w
        if (z1 - gz(o2)) * sgn_z >= 0:
            # tanah memotong di jenjang datar
            lo, hi = 0.0, 1.0
            for _ in range(40):
                mid = (lo + hi) / 2
                om = o1 + (o2 - o1) * mid
                if (z1 - gz(om)) * sgn_z >= 0:
                    hi = mid
                else:
                    lo = mid
            pts.append((o1 + (o2 - o1) * hi, z1, "DAYL"))
            return pts
        pts.append((o2, z1, "BNCH_OUT"))
        o, z = o2, z1
    pts.append((o, z, "DAYL"))
    return pts


def penampang(cfg, geo, al, prof, terrain, s, curve_state):
    """Bangun satu penampang melintang pada stasiun s. Offset positif = kanan arah stasiun."""
    xy, t, kappa, elem = al.at(s)
    nR = np.array([t[1], -t[0]])  # normal kanan
    zc = float(prof.z(s)[0])
    half = cfg["lebar_sampel_tanah_m"]
    go = np.arange(-half * 2, half * 2 + 0.25, 0.5)
    gxy = xy[None, :] + go[:, None] * nR[None, :]
    gz = terrain.z(gxy[:, 0], gxy[:, 1])

    W_s = geo["W_lurus"]
    cf = max(cfg["kemiringan_melintang"], cfg["_kriteria"]["kemiringan_melintang_min"])
    wid_in, e, frac, turn = 0.0, 0.0, 0.0, 0
    if curve_state:
        frac, e, Wc, turn = curve_state
        wid_in = max(Wc - W_s, 0) * frac
    hw = {+1: W_s / 2, -1: W_s / 2}
    slope = {+1: -cf, -1: -cf}
    if turn:
        inside = +1 if turn < 0 else -1  # belok kanan -> sisi dalam kanan
        hw[inside] += wid_in
        if e > 0:
            # sisi luar berputar dari -cf (crown normal) ke +e; sisi dalam dari -cf ke -max(cf, e)
            slope[-inside] = -cf + (e + cf) * frac
            slope[inside] = -cf - (max(cf, e) - cf) * frac
    pts = {+1: [], -1: []}
    tg = cfg["tanggul"]
    sal = cfg["saluran"]
    gal, tim = cfg["galian"], cfg["timbunan"]
    Hb = max(geo["tanggul_tinggi"], tg.get("tinggi_m") or 0.0)
    tipe = cfg.get("penampang", {}).get("tipe", "adaptif")
    sisi_info = {}
    for side in (+1, -1):
        o_e = side * hw[side]
        z_e = zc + slope[side] * hw[side]
        P = [(o_e, z_e, "ETW")]
        o_s = o_e + side * cfg["bahu_m"]
        z_s = z_e + slope[side] * cfg["bahu_m"] if slope[side] < 0 else z_e - 0.02 * cfg["bahu_m"]
        P.append((o_s, z_s, "SHLD"))
        g_at = float(np.interp(o_s, go, gz))
        cut = g_at > z_s + 0.3
        if tipe == "saluran_tanggul_dua_sisi":
            P = [(o_e, z_e, "ETW")]
            d, bw, ss = sal["dalam_m"], sal["lebar_dasar_m"], sal["kemiringan_sisi_HV"]
            o1 = o_e + side * ss * d
            P.append((o1, z_e - d, "DTCH_BI"))
            o2 = o1 + side * bw
            P.append((o2, z_e - d, "DTCH_BO"))
            o3 = o2 + side * ss * d
            P.append((o3, z_e, "DTCH_TO"))
            if tg.get("bentuk", "trapesium") == "blok":
                P.append((o3, z_e + Hb, "BERM_TI"))
                o4 = o3 + side * tg["lebar_atas_m"]
                P.append((o4, z_e + Hb, "BERM_TO"))
                zs0 = z_e + Hb
            else:
                hs = tg["kemiringan_sisi_HV"]
                o3b = o3 + side * hs * Hb
                P.append((o3b, z_e + Hb, "BERM_TI"))
                o4b = o3b + side * tg["lebar_atas_m"]
                P.append((o4b, z_e + Hb, "BERM_TO"))
                o4 = o4b + side * hs * Hb
                P.append((o4, z_e, "BERM_TOE"))
                zs0 = z_e
            g4 = float(np.interp(o4, go, gz))
            if g4 > zs0 + 0.05:
                P += _path_daylight(o4, zs0, side, go, gz, True, gal["kemiringan_HV"], gal["tinggi_jenjang_m"], gal["lebar_jenjang_m"])
                sisi_info[side] = "galian"
            else:
                P += _path_daylight(o4, zs0, side, go, gz, False, tim["kemiringan_HV"], tim["tinggi_jenjang_m"], tim["lebar_jenjang_m"])
                sisi_info[side] = "timbunan"
            pts[side] = P
            continue
        if cut:
            # saluran
            d, bw, ss = sal["dalam_m"], sal["lebar_dasar_m"], sal["kemiringan_sisi_HV"]
            o1 = o_s + side * ss * d
            P.append((o1, z_s - d, "DTCH_BI"))
            o2 = o1 + side * bw
            P.append((o2, z_s - d, "DTCH_BO"))
            P += _path_daylight(o2, z_s - d, side, go, gz, True, gal["kemiringan_HV"], gal["tinggi_jenjang_m"], gal["lebar_jenjang_m"])
            sisi_info[side] = "galian"
        else:
            hs = tg["kemiringan_sisi_HV"]
            o1 = o_s + side * hs * Hb
            P.append((o1, z_s + Hb, "BERM_TI"))
            o2 = o1 + side * tg["lebar_atas_m"]
            P.append((o2, z_s + Hb, "BERM_TO"))
            o3 = o2 + side * hs * Hb
            P.append((o3, z_s, "BERM_TOE"))
            g3 = float(np.interp(o3, go, gz))
            if g3 >= z_s:
                P.append((o3, g3, "DAYL"))
            else:
                P += _path_daylight(o3, z_s, side, go, gz, False, tim["kemiringan_HV"], tim["tinggi_jenjang_m"], tim["lebar_jenjang_m"])
            sisi_info[side] = "timbunan"
        pts[side] = P
    left = list(reversed(pts[-1]))
    right = pts[+1]
    design = left + [(0.0, zc, "CL")] + right
    o_d = np.array([p[0] for p in design])
    z_d = np.array([p[1] for p in design])
    # luas galian/timbunan
    oo = np.linspace(o_d[0], o_d[-1], 600)
    dz = np.interp(oo, o_d, z_d) - np.interp(oo, go, gz)
    dx = oo[1] - oo[0]
    fill_a = float(np.clip(dz, 0, None).sum() * dx)
    cut_a = float(np.clip(-dz, 0, None).sum() * dx)
    xyz = np.array([[*(xy + o * nR), z] for o, z, _ in design])
    gz_d = np.interp(o_d, go, gz)
    h_tim = float(max(0.0, np.max(z_d - gz_d)))
    h_gal = float(max(0.0, np.max(gz_d - z_d)))
    m = (go >= o_d[0] - 10) & (go <= o_d[-1] + 10)
    return dict(sta=float(s), zc=zc, design=design, xyz=xyz, codes=[p[2] for p in design],
                ground=np.column_stack([go[m], gz[m]]), cut=cut_a, fill=fill_a, xy=xy, nR=nR,
                lebar=hw[+1] + hw[-1], slope_kiri=slope[-1], slope_kanan=slope[+1], sisi=sisi_info,
                e=curve_state[1] * curve_state[0] if curve_state else 0.0, h_timbunan=h_tim, h_galian=h_gal)


def curve_state_at(cfg, al, s):
    """(frac 0..1, e, Wc, turn) memperhitungkan transisi (runoff) sepanjang Lr di luar PC/PT."""
    for c in al.curves:
        e, _ = superelevasi(cfg, c["radius"])
        Wc, _ = lebar_tikungan(cfg, c["radius"])
        W_s = geometri(cfg)["W_lurus"]
        Lr = max(20.0, (W_s / 2) * (e + cfg["kemiringan_melintang"]) / 0.01)  # rasio relatif 1%
        a, b = c["sta_pc"], c["sta_pt"]
        if a - Lr * 2 / 3 <= s <= b + Lr * 2 / 3:
            if a + Lr / 3 <= s <= b - Lr / 3 or (b - a) < Lr * 2 / 3:
                frac = 1.0
            elif s < a + Lr / 3:
                frac = (s - (a - Lr * 2 / 3)) / Lr
            else:
                frac = ((b + Lr * 2 / 3) - s) / Lr
            return (float(np.clip(frac, 0, 1)), e, Wc, c["elem"].sgn)
    return None


# =============================================================================== pemeriksaan lain
def kapasitas_saluran(cfg, geo, lebar_tangkapan):
    sal = cfg["saluran"]
    b, d, z = sal["lebar_dasar_m"], sal["dalam_m"], sal["kemiringan_sisi_HV"]
    A = (b + z * d) * d
    Pw = b + 2 * d * math.sqrt(1 + z ** 2)
    S0 = 0.005
    Qcap = (1 / sal["manning_n"]) * A * (A / Pw) ** (2 / 3) * math.sqrt(S0)
    Akm2 = lebar_tangkapan * sal["panjang_ke_sump_m"] / 1e6
    Q = 0.278 * sal["koef_limpasan"] * sal["intensitas_hujan_mm_jam"] * Akm2
    return dict(Q_kapasitas_m3s=Qcap, Q_rencana_m3s=Q, memenuhi=Qcap >= Q, kemiringan_dasar_min=S0)


def tebal_perkerasan(cfg):
    """Kaufman & Ault (USBM IC 8758) - kurva CBR: t(in) = sqrt(P/(8.1 CBR) - A/pi), P beban roda (lb), A luas kontak (in2)."""
    u = cfg["unit_terbesar"]
    P_kg = u["gvw_ton"] * 1000 * u["porsi_beban_gandar_belakang"] / u["jumlah_roda_belakang"]
    P_lb = P_kg * 2.2046
    p_psi = u["tekanan_ban_kpa"] * 0.145038
    A_in2 = P_lb / p_psi
    cbr = cfg["lapis_perkerasan"]["cbr_tanah_dasar"]
    t_in = math.sqrt(max(P_lb / (8.1 * cbr) - A_in2 / math.pi, 0))
    return dict(beban_roda_kg=P_kg, tekanan_kontak_kpa=u["tekanan_ban_kpa"], cbr_tanah_dasar=cbr,
                tebal_perlu_m=t_in * 0.0254, tebal_rencana_m=cfg["lapis_perkerasan"]["tebal_m"],
                memenuhi=cfg["lapis_perkerasan"]["tebal_m"] + 1e-6 >= t_in * 0.0254)


# =============================================================================== utama
def demo_terrain():
    def f(X, Y):
        return (60 + 0.06 * X + 0.05 * Y + 38 * np.exp(-(((X - 470) / 150) ** 2 + ((Y - 230) / 110) ** 2))
                - 10 * np.exp(-(((X - 180) / 90) ** 2 + ((Y - 330) / 70) ** 2)) + 3.5 * np.sin(X / 45) * np.cos(Y / 60))
    return cx.Terrain.from_function(f, -50, 900, -50, 650, 5.0)


DEMO_CFG = {
    "proyek": "Contoh Jalan Angkut Pit A - Stockpile (DEMO)",
    "perusahaan": "PT. Surya Saga Utama",
    "epsg": 32751,
    "alinyemen": {"pi": [[40, 60], [260, 110], [430, 70], [620, 260], [780, 520]], "radius": [60, 50, 70], "nama": "HR-PITA-STP"},
    "profil": {"mode": "otomatis", "jarak_pvi_m": 80.0},
}


def terrain_from_cfg(cfg):
    t = cfg["topografi"]
    src = t.get("sumber", "demo")
    if src == "demo":
        return demo_terrain()
    if src.lower().endswith(".xml"):
        return cx.Terrain.from_landxml(src, t.get("nama_surface"))
    return cx.Terrain.from_csv(src)


def run(cfg, out):
    os.makedirs(out, exist_ok=True)
    kr = cfg["_kriteria"]
    terrain = terrain_from_cfg(cfg)
    alc = cfg["alinyemen"]
    al = HAlignment(alc["pi"], alc["radius"], alc.get("sta_awal", 0.0))
    geo = geometri(cfg)
    prof, vinfo = susun_profil(cfg, al, terrain)

    # stasiun penampang: interval + titik kunci
    sts = list(np.arange(al.sta0, al.sta_end, cfg["interval_penampang_m"])) + [al.sta_end]
    lb = cfg["lembar"]
    sts_tabel = sorted(set([round(al.sta0, 3)] + [round(v, 3) for v in np.arange(math.ceil(al.sta0 / lb["interval_penampang_lembar_m"]) * lb["interval_penampang_lembar_m"],
                                                                         al.sta_end, lb["interval_penampang_lembar_m"])] + [round(al.sta_end, 3)]))
    sts += sts_tabel
    for c in al.curves:
        sts += [c["sta_pc"], (c["sta_pc"] + c["sta_pt"]) / 2, c["sta_pt"]]
    sts = sorted(set(round(s, 3) for s in sts))
    xs = [penampang(cfg, geo, al, prof, terrain, s, curve_state_at(cfg, al, s)) for s in sts]

    # volume average end area
    vol_rows = []
    cum = 0.0
    cut_tot = fill_tot = 0.0
    shrink = cfg["timbunan"]["faktor_susut"]
    for i, x in enumerate(xs):
        if i == 0:
            vc = vf = 0.0
        else:
            d = x["sta"] - xs[i - 1]["sta"]
            vc = d * (x["cut"] + xs[i - 1]["cut"]) / 2
            vf = d * (x["fill"] + xs[i - 1]["fill"]) / 2
        cut_tot += vc
        fill_tot += vf
        cum += vc - vf / shrink
        vol_rows.append(dict(sta=x["sta"], luas_galian=x["cut"], luas_timbunan=x["fill"], vol_galian=vc,
                             vol_timbunan=vf, kumulatif_massa=cum, elev_cl=x["zc"], lebar_jalur=x["lebar"]))

    # tabel volume pada stasiun lembar (volume = jumlah volume halus di antaranya, lebih teliti dari 1 interval kasar)
    tabel_vol = []
    cf_, cc_ = 0.0, 0.0
    prev = None
    for T in sts_tabel:
        i = int(np.argmin([abs(x["sta"] - T) for x in xs]))
        if prev is None:
            vf = vc = 0.0
        else:
            seg = [r for r in vol_rows if prev < r["sta"] <= T + 1e-6]
            vf = sum(r["vol_timbunan"] for r in seg)
            vc = sum(r["vol_galian"] for r in seg)
        cf_ += vf
        cc_ += vc
        tabel_vol.append(dict(sta=T, luas_timbunan=xs[i]["fill"], luas_galian=xs[i]["cut"], vol_timbunan=vf, vol_galian=vc,
                              kum_timbunan=cf_, kum_galian=cc_, idx=i))
        prev = T

    # ---------------- geoteknik lereng galian & timbunan (opsional, butuh skill desain-pit-geoteknik)
    geo_lereng = evaluasi_lereng(cfg, xs)

    # ---------------- permukaan
    allpts = np.vstack([x["xyz"] for x in xs])
    codes = sum([x["codes"] for x in xs], [])
    from shapely.geometry import Polygon

    left_d = [x["xyz"][0, :2] for x in xs]
    right_d = [x["xyz"][-1, :2] for x in xs]
    boundary = Polygon(left_d + right_d[::-1]).buffer(0)
    _, ctris = cx.delaunay_tin(allpts, boundary)
    # EG grid
    xmin, ymin = allpts[:, :2].min(axis=0) - 80
    xmax, ymax = allpts[:, :2].max(axis=0) + 80
    gx = np.arange(xmin, xmax, 5.0)
    gy = np.arange(ymin, ymax, 5.0)
    GX, GY = np.meshgrid(gx, gy)
    GZ = terrain.z(GX.ravel(), GY.ravel()).reshape(GX.shape)
    eg_pts, eg_tris = cx.grid_tin(gx, gy, GZ)
    from scipy.interpolate import LinearNDInterpolator
    import shapely

    corr = LinearNDInterpolator(allpts[:, :2], allpts[:, 2])
    inside = shapely.contains_xy(boundary, GX.ravel(), GY.ravel())
    CZ = GZ.ravel().copy()
    vin = corr(GX.ravel()[inside], GY.ravel()[inside])
    CZ[inside] = np.where(np.isfinite(vin), vin, CZ[inside])
    cp_pts, cp_tris = cx.grid_tin(gx, gy, CZ.reshape(GX.shape))
    cut_tin, fill_tin = cx.tin_volume_between(allpts, ctris, terrain.z)

    # ---------------- pemeriksaan kepatuhan
    grades = prof.grades()
    gmax_actual = max(abs(g) for g in grades)
    chk = []
    def add(item, nilai, syarat, ok, dasar, ket=""):
        chk.append(dict(item=item, nilai=nilai, syarat=syarat, status="MEMENUHI" if ok else "TIDAK MEMENUHI", dasar=dasar, ket=ket))
    u = cfg["unit_terbesar"]
    min_lebar = min(x["lebar"] for x in xs)
    add("Lebar jalur lalu lintas lurus", f"{geo['W_lurus']:.2f} m", f">= {geo['W_min_kepmen']:.2f} m ({kr['lebar_jalan_dua_jalur_min_x_lebar_unit'] if cfg['jumlah_jalur'] >= 2 else kr['lebar_jalan_satu_jalur_min_x_lebar_unit']} x {u['lebar_m']} m)",
        min_lebar + 1e-6 >= geo["W_min_kepmen"], kr["pasal"]["lebar"])
    for c in al.curves:
        Wc, wd = lebar_tikungan(cfg, c["radius"])
        e, e_req = superelevasi(cfg, c["radius"])
        c.update(W=Wc, e=e, e_perlu=e_req, **{f"lebar_{k}": v for k, v in wd.items()})
        okR = c["radius"] >= geo["R_min"]
        add(f"Tikungan PI{c['pi_no']} (R={c['radius']:.0f} m, {c['arah']})",
            f"R={c['radius']:.0f} m, W={Wc:.2f} m, e={e * 100:.1f}%",
            f"R >= {geo['R_min']:.1f} m @ {cfg['kecepatan_rencana_kmh']:.0f} km/j; e perlu {max(e_req, 0) * 100:.1f}%",
            okR and e_req <= cfg["superelevasi_maks"] + 1e-9, kr["pasal"]["tikungan"],
            "jika tidak memenuhi: perbesar R atau turunkan batas kecepatan di tikungan")
    add("Tanggul pengaman (safety berm)", f"tinggi {geo['tanggul_tinggi']:.2f} m",
        f">= {kr['tanggul_pengaman_min_x_diameter_roda']} x {u['diameter_roda_m']} m = {kr['tanggul_pengaman_min_x_diameter_roda'] * u['diameter_roda_m']:.2f} m",
        geo["tanggul_tinggi"] + 1e-9 >= kr["tanggul_pengaman_min_x_diameter_roda"] * u["diameter_roda_m"], kr["pasal"]["tanggul"],
        "dipasang otomatis di sisi timbunan/terbuka; sisi galian (boxcut) tanpa tanggul")
    cf = max(cfg["kemiringan_melintang"], kr["kemiringan_melintang_min"])
    add("Kemiringan melintang (cross fall)", f"{cf * 100:.1f}%", f">= {kr['kemiringan_melintang_min'] * 100:.0f}%", cf >= kr["kemiringan_melintang_min"], kr["pasal"]["cross_fall"])
    add("Kemiringan memanjang (grade) maksimum", f"{gmax_actual * 100:.2f}%", f"<= {kr['grade_maks'] * 100:.0f}% (target desain {cfg['grade_maks_desain'] * 100:.0f}%)",
        gmax_actual <= kr["grade_maks"] + 1e-9, kr["pasal"]["grade"], "di atas 12% wajib kajian teknis (hal. 100 viii)")
    lt = geo["W_lurus"] / 2 + cfg["bahu_m"] + 10.0
    dr = kapasitas_saluran(cfg, geo, lt)
    add("Saluran drainase (Manning vs metode rasional)", f"Qkap={dr['Q_kapasitas_m3s']:.3f} m3/s", f">= Qrencana={dr['Q_rencana_m3s']:.3f} m3/s",
        dr["memenuhi"], kr["pasal"]["drainase"], f"I={cfg['saluran']['intensitas_hujan_mm_jam']} mm/jam, sump/gorong-gorong tiap {cfg['saluran']['panjang_ke_sump_m']:.0f} m, dasar saluran min 0,5%")
    tp = tebal_perkerasan(cfg)
    add("Daya dukung / tebal lapis perkerasan", f"{tp['tebal_rencana_m']:.2f} m", f">= {tp['tebal_perlu_m']:.2f} m (CBR tanah dasar {tp['cbr_tanah_dasar']}%)",
        tp["memenuhi"], kr["pasal"]["daya_dukung"], "metode kurva CBR Kaufman & Ault; verifikasi dengan uji CBR lapangan/DCP")
    add("Separator di tikungan/persimpangan (spesifikasi)", f"tinggi {geo['separator_tinggi']:.2f} m, lebar atas {geo['separator_lebar_atas']:.2f} m",
        f">= 1/2 x D roda; lebar atas >= lebar roda", True, kr["pasal"]["separator"], "dipasang bila jalur dipisah median")
    for i, ang in enumerate(cfg.get("persimpangan_deg") or []):
        add(f"Sudut persimpangan #{i + 1}", f"{ang:.0f} deg", f">= {kr['sudut_persimpangan_tiga_min_deg']:.0f} deg", ang >= kr["sudut_persimpangan_tiga_min_deg"], kr["pasal"]["persimpangan"])
    if cfg.get("produksi_tph") and cfg.get("kapasitas_jalan_tph"):
        need = cfg["produksi_tph"] * kr["kapasitas_jalan_min_x_laju_produksi"]
        add("Kapasitas jalan vs produksi", f"{cfg['kapasitas_jalan_tph']:.0f} t/jam", f">= {need:.0f} t/jam (+25%)", cfg["kapasitas_jalan_tph"] >= need, kr["pasal"]["kapasitas"])
    for v in vinfo["lengkung"]:
        if v["A_pct"] < 1.0:
            continue
        add(f"Lengkung vertikal {v['jenis']} STA {cx.fmt_sta(v['sta'])}", f"L={v['L_pakai']:.0f} m (A={v['A_pct']:.1f}%)",
            f"L >= {v['L_perlu']:.0f} m (JPH {vinfo['SSD']:.0f} m)", v["memenuhi"], "Praktik rekayasa AASHTO (Kepmen tidak memberi angka jarak pandang)",
            "bila kurang: batasi kecepatan/pasang rambu di puncak")
    for w in al.warnings:
        add("Geometri alinyemen", w, "tangen muat", False, "Praktik rekayasa")
    for gl in geo_lereng.get("hasil", []):
        sy = gl["syarat"]
        add(f"Lereng {gl['jenis']} maks (H {gl['tinggi']:.1f} m, STA {cx.fmt_sta(gl['sta'])})",
            f"FKs {gl['fk_statis']:.2f}, FKd {gl['fk_dinamis']:.2f}, PoF {gl['pof'] * 100:.1f}%",
            f"FKs >= {sy['fk_statis']}, FKd >= {sy['fk_dinamis']}, PoF <= {sy['pof_maks'] * 100:.0f}% (CoF {geo_lereng['cof']})",
            gl["status"] == "MEMENUHI", "Kepmen 1827 Tabel 1 hal. 57" + (", timbunan: parameter residual hal. 58" if gl["jenis"] == "timbunan" else ""),
            f"parameter {geo_lereng['status_parameter']}")

    summary = dict(
        proyek=cfg["proyek"], panjang_m=al.length, sta_awal=al.sta0, sta_akhir=al.sta_end,
        lebar_lurus_m=geo["W_lurus"], R_min_m=geo["R_min"], tanggul_tinggi_m=geo["tanggul_tinggi"],
        grade_maks_pct=gmax_actual * 100, jarak_pandang_henti_m=vinfo["SSD"],
        volume_galian_m3=cut_tot, volume_timbunan_m3=fill_tot, volume_galian_tin_m3=cut_tin, volume_timbunan_tin_m3=fill_tin,
        volume_perkerasan_m3=al.length * geo["W_lurus"] * cfg["lapis_perkerasan"]["tebal_m"],
        tikungan=[{k: v for k, v in c.items() if k != "elem"} for c in al.curves],
        pvi=[dict(sta=s, elev=z, L=L) for s, z, L in prof.pvis], grade_pct=[g * 100 for g in grades],
        lengkung_vertikal=vinfo["lengkung"], drainase=dr, perkerasan=tp, pemeriksaan=chk, geoteknik=geo_lereng,
        tabel_volume=[{k: v for k, v in r.items() if k != "idx"} for r in tabel_vol],
        h_timbunan_maks=max(x["h_timbunan"] for x in xs), h_galian_maks=max(x["h_galian"] for x in xs),
        jarak_pandang=vinfo, geometri=geo,
        lolos_semua=all(c["status"] == "MEMENUHI" for c in chk),
    )

    # ---------------- tulis berkas
    files = {}
    import csv
    with open(os.path.join(out, "volume.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(vol_rows[0].keys()))
        w.writeheader()
        for r in vol_rows:
            w.writerow({k: (f"{v:.3f}" if isinstance(v, float) else v) for k, v in r.items()})
    files["volume"] = "volume.csv"
    cx.write_points_csv(os.path.join(out, "titik_koridor.csv"), allpts, codes)

    lx = cx.LandXML(cfg["proyek"], "Desain jalan tambang - Kepmen ESDM 1827 K/30/MEM/2018", cfg.get("epsg"), cfg.get("perusahaan", ""))
    lx.add_surface("EG_Tanah_Asli", eg_pts, eg_tris, "Permukaan tanah asli")
    brk = []
    for code in ("CL", "ETW", "SHLD", "DAYL"):
        for side_idx in (0, -1) if code != "CL" else (None,):
            line = []
            for x in xs:
                cds = x["codes"]
                if code == "CL":
                    j = cds.index("CL")
                else:
                    js = [k for k, c in enumerate(cds) if c == code]
                    if not js:
                        continue
                    j = js[0] if side_idx == 0 else js[-1]
                line.append(x["xyz"][j])
            if len(line) > 1:
                brk.append((f"{code}{'' if side_idx is None else ('_L' if side_idx == 0 else '_R')}", line))
    lx.add_surface("FG_Koridor_Jalan", allpts, ctris, "Permukaan desain koridor jalan", brk)
    lx.add_surface("FG_Komposit", cp_pts, cp_tris, "Tanah asli + koridor (permukaan akhir)")
    xsec = []
    for x in xs:
        xsec.append(dict(sta=x["sta"], desc=f"galian {x['cut']:.2f} m2; timbunan {x['fill']:.2f} m2",
                         surfaces={"FG": [(o, z, c) for o, z, c in x["design"]],
                                   "EG": [(o, z, "") for o, z in x["ground"][::4]]}))
    eg_prof = [(s, float(terrain.z(*al.at(s)[0])[0])) for s in np.arange(al.sta0, al.sta_end, 5.0)]
    lx.add_alignment(alc.get("nama", "HR-01"), al.landxml_elements(), al.sta0,
                     profiles=[dict(name="EG", type="ProfSurf", pnts=eg_prof),
                               dict(name="FG_Desain", type="ProfAlign", pvis=prof.pvis)],
                     cross_sections=xsec, desc=f"V={cfg['kecepatan_rencana_kmh']} km/j; {cfg['jumlah_jalur']} jalur")
    lx.write(os.path.join(out, "jalan.xml"))
    files["landxml"] = "jalan.xml"

    _dxf_plan(cfg, al, xs, terrain, eg_pts, eg_tris, cp_pts, cp_tris, os.path.join(out, "jalan_plan.dxf"))
    _dxf_3d(xs, allpts, ctris, os.path.join(out, "jalan_3d.dxf"))
    _dxf_profil(cfg, al, prof, eg_prof, os.path.join(out, "jalan_profil.dxf"))
    _dxf_penampang(xs, os.path.join(out, "jalan_penampang.dxf"))
    origin = np.array([xmin, ymin, 0.0])
    cx.write_obj(os.path.join(out, "koridor.obj"), allpts, ctris, "koridor", origin)
    cx.write_stl(os.path.join(out, "koridor.stl"), allpts, ctris, "koridor", origin)
    cx.write_obj(os.path.join(out, "komposit.obj"), cp_pts, cp_tris, "komposit", origin)

    import sheets_jalan
    daftar_lembar = sheets_jalan.render(cfg, al, prof, eg_prof, xs, vol_rows, tabel_vol, summary, eg_pts, eg_tris, cp_pts, cp_tris,
                                        allpts, ctris, terrain, os.path.join(out, "gambar_perencanaan_jalan.pdf"), out)
    summary["daftar_lembar"] = daftar_lembar
    with open(os.path.join(out, "laporan.json"), "w") as f:
        json.dump(summary, f, indent=2, default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o))
    import laporan_jalan
    summary["berkas_laporan"] = laporan_jalan.tulis(cfg, summary, out)
    return summary


def evaluasi_lereng(cfg, xs):
    """FK & PoF lereng galian/timbunan tertinggi memakai geotek.py (skill desain-pit-geoteknik)."""
    g = cfg.get("geoteknik") or {}
    if not g.get("aktif", True):
        return {"aktif": False}
    gp = os.path.join(HERE, "..", "..", "desain-pit-geoteknik", "scripts")
    if not os.path.exists(os.path.join(gp, "geotek.py")):
        return {"aktif": False, "catatan": "geotek.py tidak ditemukan (pasang skill desain-pit-geoteknik)"}
    sys.path.insert(0, gp)
    import geotek as gt

    hasil = []
    for jenis, key, mk in (("galian", "h_galian", "material_galian"), ("timbunan", "h_timbunan", "material_timbunan")):
        x = max(xs, key=lambda r: r[key])
        H = x[key]
        if H < 1.0:
            continue
        p = cfg["galian"] if jenis == "galian" else cfg["timbunan"]
        hb = p["tinggi_jenjang_m"] or H
        n = max(1, int(math.ceil(H / hb)))
        hb = H / n
        muka = math.degrees(math.atan(1.0 / p["kemiringan_HV"]))
        mat = gt.Material.from_dict(g[mk])
        ev = gt.evaluasi(dict(tinggi_jenjang=hb, sudut_muka=muka, lebar_berm=p["lebar_jenjang_m"], jumlah_jenjang=n,
                              jenjang_per_inter_ramp=n), mat, g["keparahan_longsor"], g["ru"], g["kh"], g["n_monte_carlo"])
        v = ev["keseluruhan"]
        hasil.append(dict(jenis=jenis, sta=x["sta"], tinggi=H, sudut=v["sudut"], fk_statis=v["fk_statis"],
                          fk_dinamis=v["fk_dinamis"] or 0.0, pof=v["pof"], syarat=v["syarat"], status=v["status"],
                          lingkaran=v["lingkaran"], xz=v["xz"], muka=muka, n=n, tinggi_jenjang=hb))
    return dict(aktif=True, cof=g["keparahan_longsor"], ru=g["ru"], kh=g["kh"], status_parameter=g["status_parameter"],
                material_galian=g["material_galian"], material_timbunan=g["material_timbunan"], hasil=hasil)


def _feature_lines(xs):
    """Sambungkan titik berkode sama antar penampang menjadi feature line 3D (putus bila kode hilang)."""
    lines = {}
    keys = ["CL", "ETW", "SHLD", "BERM_TI", "BERM_TO", "BERM_TOE", "DTCH_BI", "DTCH_BO", "DTCH_TO", "DAYL"]
    for code in keys:
        for side in ("L", "R"):
            if code == "CL" and side == "R":
                continue
            runs, cur = [], []
            for x in xs:
                cds = x["codes"]
                ci = cds.index("CL")
                rng = range(0, ci) if side == "L" else range(ci + 1, len(cds))
                js = [k for k in rng if cds[k] == code] if code != "CL" else [ci]
                if js:
                    j = js[-1] if side == "L" else js[0]
                    if code == "DAYL":
                        j = 0 if side == "L" else len(cds) - 1
                    cur.append(x["xyz"][j])
                else:
                    if len(cur) > 1:
                        runs.append(cur)
                    cur = []
            if len(cur) > 1:
                runs.append(cur)
            if runs:
                lines[f"{code}" + ("" if code == "CL" else f"_{side}")] = runs
    return lines


LAYER_OF = {"CL": "C-ROAD-CNTR", "ETW": "C-ROAD-EDGE", "SHLD": "C-ROAD-SHLD", "BERM_TI": "C-ROAD-BERM", "BERM_TO": "C-ROAD-BERM",
            "BERM_TOE": "C-ROAD-BERM", "DTCH_BI": "C-ROAD-DTCH", "DTCH_BO": "C-ROAD-DTCH", "DTCH_TO": "C-ROAD-DTCH", "DAYL": "C-ROAD-DAYL"}


def _dxf_plan(cfg, al, xs, terrain, eg_pts, eg_tris, cp_pts, cp_tris, path):
    d = cx.DXF()
    for lev, seg in cx.contours(eg_pts, eg_tris, 1.0):
        d.poly2d(seg, "C-TOPO-MAJR" if abs(lev % 5) < 1e-6 else "C-TOPO-MINR", elevation=lev)
    for lev, seg in cx.contours(cp_pts, cp_tris, 1.0):
        if abs(lev % 5) < 1e-6:
            d.poly2d(seg, "C-TOPO-FG-MAJR", elevation=lev)
    for name, runs in _feature_lines(xs).items():
        lay = LAYER_OF[name.split("_L")[0].split("_R")[0]] if name != "CL" else "C-ROAD-CNTR"
        for r in runs:
            d.poly2d(np.array(r)[:, :2], lay)
    ss = np.arange(al.sta0, al.sta_end, 1.0)
    d.poly2d(np.array([al.at(s)[0] for s in ss] + [al.at(al.sta_end)[0]]), "C-ROAD-CNTR")
    for s in np.arange(al.sta0, al.sta_end + 1e-6, 20.0):
        p, t, _, _ = al.at(s)
        n = np.array([t[1], -t[0]])
        major = abs(s % 100) < 1e-6
        d.line((*(p - n * (2.5 if major else 1.2)), 0), (*(p + n * (2.5 if major else 1.2)), 0), "C-ROAD-STAN")
        if major:
            ang = math.degrees(math.atan2(n[1], n[0]))
            d.text(cx.fmt_sta(s), p + n * 6, 2.0, "C-ROAD-STAN", rot=ang)
    for c in al.curves:
        e = c["elem"]
        d.text(f"PI{c['pi_no']} R={c['radius']:.0f} D={c['delta_deg']:.1f}d L={c['L']:.1f} e={c.get('e', 0) * 100:.1f}% W={c.get('W', 0):.1f}",
               e.pi + np.array([0, 8]), 2.2, "C-ROAD-CURV")
        d.text("PC", e.start, 1.6, "C-ROAD-CURV")
        d.text("PT", e.end, 1.6, "C-ROAD-CURV")
    for x in xs:
        if abs(x["sta"] % 100) < 1e-6:
            a, b = x["xyz"][0], x["xyz"][-1]
            d.line((a[0], a[1], 0), (b[0], b[1], 0), "C-ROAD-XSEC")
    d.save(path)


def _dxf_3d(xs, allpts, ctris, path):
    d = cx.DXF()
    for name, runs in _feature_lines(xs).items():
        lay = LAYER_OF[name.split("_L")[0].split("_R")[0]] if name != "CL" else "C-ROAD-CNTR"
        for r in runs:
            d.poly3d(r, lay)
    for x in xs:
        d.poly3d(x["xyz"], "C-ROAD-XSEC")
    d.faces(allpts, ctris, "C-TINN-FG")
    d.mesh(allpts, ctris, "C-TINN-FG")
    d.save(path)


def _dxf_profil(cfg, al, prof, eg_prof, path):
    VE = cfg["skala_vertikal_profil"]
    d = cx.DXF({"C-PROF-GRID": (8, "CONTINUOUS", "Grid profil"), "C-PROF-EG": (8, "DASHED", "Profil tanah asli"),
                "C-PROF-FG": (1, "CONTINUOUS", "Profil desain"), "C-PROF-TEXT": (7, "CONTINUOUS", "Label profil")})
    s = np.array([p[0] for p in eg_prof])
    zeg = np.array([p[1] for p in eg_prof])
    sf = np.arange(al.sta0, al.sta_end + 0.1, 2.0)
    zfg = prof.z(sf)
    datum = math.floor(min(zeg.min(), zfg.min()) / 5) * 5 - 5
    top = math.ceil(max(zeg.max(), zfg.max()) / 5) * 5 + 5
    def P(st, z):
        return (st - al.sta0, (z - datum) * VE)
    for z in np.arange(datum, top + 0.1, 5):
        d.line((*P(al.sta0, z), 0), (*P(al.sta_end, z), 0), "C-PROF-GRID")
        d.text(f"{z:.0f}", (P(al.sta0, z)[0] - 8, P(al.sta0, z)[1]), 2.5, "C-PROF-TEXT")
    for st in np.arange(al.sta0, al.sta_end + 0.1, 50):
        d.line((*P(st, datum), 0), (*P(st, top), 0), "C-PROF-GRID")
        d.text(cx.fmt_sta(st), (P(st, datum)[0], P(st, datum)[1] - 6), 2.5, "C-PROF-TEXT")
        zg = float(np.interp(st, s, zeg)); zf = float(prof.z(st)[0])
        d.text(f"{zg:.2f}", (P(st, datum)[0], P(st, datum)[1] - 12), 2.0, "C-PROF-TEXT", rot=90)
        d.text(f"{zf:.2f}", (P(st, datum)[0], P(st, datum)[1] - 22), 2.0, "C-PROF-TEXT", rot=90)
    lab = cfg["lembar"]["label_baris_profil"]
    d.text(lab[0], (P(al.sta0, datum)[0] - 30, P(al.sta0, datum)[1] - 12), 2.2, "C-PROF-TEXT")
    d.text(lab[1], (P(al.sta0, datum)[0] - 30, P(al.sta0, datum)[1] - 22), 2.2, "C-PROF-TEXT")
    d.text(lab[2], (P(al.sta0, datum)[0] - 30, P(al.sta0, datum)[1] - 6), 2.2, "C-PROF-TEXT")
    d.poly2d([P(a, b) for a, b in zip(s, zeg)], "C-PROF-EG")
    d.poly2d([P(a, b) for a, b in zip(sf, zfg)], "C-PROF-FG")
    g = prof.grades()
    for i, (st, z, L) in enumerate(prof.pvis):
        x0, y0 = P(st, z)
        d.line((x0, y0, 0), (x0, y0 + 25, 0), "C-PROF-TEXT")
        d.text(f"PVI {cx.fmt_sta(st)} EL {z:.2f}" + (f" L={L:.0f}" if L else ""), (x0, y0 + 30), 2.2, "C-PROF-TEXT", rot=90)
        if i < len(g):
            st2, z2, _ = prof.pvis[i + 1]
            xm, ym = P((st + st2) / 2, (z + z2) / 2)
            ang = math.degrees(math.atan2((z2 - z) * VE, st2 - st))
            d.text(f"{g[i] * 100:+.2f}%", (xm, ym + 5), 2.5, "C-PROF-TEXT", rot=ang)
    d.text(f"PROFIL MEMANJANG {cfg['alinyemen'].get('nama', '')}  (skala vertikal x{VE:g})", (P((al.sta0 + al.sta_end) / 2, top)[0], P(al.sta0, top)[1] + 15), 4, "C-PROF-TEXT")
    d.save(path)


def _dxf_penampang(xs, path, ncol=4):
    d = cx.DXF({"C-SECT-GRID": (8, "CONTINUOUS", "Grid penampang"), "C-SECT-EG": (8, "DASHED", "Tanah asli"),
                "C-SECT-FG": (1, "CONTINUOUS", "Desain"), "C-SECT-TEXT": (7, "CONTINUOUS", "Label")})
    cw, ch = 110.0, 45.0
    for i, x in enumerate(xs):
        col, row = i % ncol, i // ncol
        ox, oy = col * (cw + 10), -row * (ch + 15)
        z0 = math.floor(min(x["ground"][:, 1].min(), min(p[1] for p in x["design"])) / 2) * 2 - 2
        def P(o, z):
            return (ox + cw / 2 + o, oy + (z - z0))
        d.poly2d([(ox, oy), (ox + cw, oy), (ox + cw, oy + ch), (ox, oy + ch)], "C-SECT-GRID", closed=True)
        for z in np.arange(z0, z0 + ch + 0.1, 5):
            if oy + (z - z0) <= oy + ch:
                d.line((ox, oy + z - z0, 0), (ox + cw, oy + z - z0, 0), "C-SECT-GRID")
                d.text(f"{z:.0f}", (ox - 4, oy + z - z0), 1.5, "C-SECT-TEXT")
        for o in np.arange(-50, 51, 10):
            d.line((ox + cw / 2 + o, oy, 0), (ox + cw / 2 + o, oy + ch, 0), "C-SECT-GRID")
        g = x["ground"]
        m = np.abs(g[:, 0]) <= cw / 2
        d.poly2d([P(o, z) for o, z in g[m]], "C-SECT-EG")
        dz = [(o, z) for o, z, _ in x["design"] if abs(o) <= cw / 2]
        d.poly2d([P(o, z) for o, z in dz], "C-SECT-FG")
        d.text(f"STA {cx.fmt_sta(x['sta'])}  CL EL {x['zc']:.2f}", (ox + cw / 2, oy + ch - 3), 2.2, "C-SECT-TEXT")
        d.text(f"G={x['cut']:.1f} m2  T={x['fill']:.1f} m2", (ox + cw / 2, oy + 3), 1.8, "C-SECT-TEXT")
    d.save(path)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", help="JSON konfigurasi")
    ap.add_argument("--demo", action="store_true", help="jalankan contoh dengan topografi sintetis")
    ap.add_argument("--out", default="hasil_jalan")
    a = ap.parse_args(argv)
    cfg = load_config(a.config, DEMO_CFG if a.demo and not a.config else None)
    s = run(cfg, a.out)
    print(json.dumps({k: s[k] for k in ("panjang_m", "lebar_lurus_m", "grade_maks_pct", "volume_galian_m3", "volume_timbunan_m3", "lolos_semua")}, indent=2))
    for c in s["pemeriksaan"]:
        print(f"[{c['status']}] {c['item']}: {c['nilai']} ({c['syarat']})")


if __name__ == "__main__":
    main()
