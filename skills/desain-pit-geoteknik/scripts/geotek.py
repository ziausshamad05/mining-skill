#!/usr/bin/env python3
"""Analisis kestabilan lereng tambang terbuka untuk kepatuhan Kepmen ESDM 1827 K/30/MEM/2018 (Tabel 1 hal. 57).

- Geometri lereng dari parameter jenjang (tinggi, sudut muka, lebar berm) -> profil 2D, sudut inter-ramp & keseluruhan
- Faktor keamanan metode Bishop disederhanakan (bidang gelincir lingkaran), pencarian grid pusat x titik keluar
- Kondisi statis & dinamis (pseudo-statik, koefisien gempa horizontal kh), tekanan air pori (ru)
- Probabilitas longsor (PoF) Monte Carlo pada c, phi, gamma (bidang kritis tetap + pencarian ulang terbatas)
- Material berlapis (lapisan horizontal) didukung: daftar lapisan dengan elevasi atas
- Optimasi geometri: cari sudut keseluruhan paling curam yang masih memenuhi FK & PoF Kepmen

Ini alat penyaring desain. Desain final tetap diverifikasi dengan perangkat lunak geoteknik (Slide2, GeoStudio, RS2)
dan data uji laboratorium/lapangan, lalu disahkan KTT.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KRITERIA_PATH = os.path.join(HERE, "..", "references", "kriteria_geoteknik_kepmen1827.json")


def load_kriteria(path=KRITERIA_PATH):
    with open(path) as f:
        return json.load(f)


def syarat(jenis: str, cof: str, kr=None):
    """Syarat FK statis, FK dinamis, PoF maks untuk jenis lereng ('tunggal','inter_ramp','keseluruhan') & CoF."""
    kr = kr or load_kriteria()
    row = kr["tabel_fk_pof"][jenis][cof]
    i = 1 if kr.get("pakai_batas", "atas") == "atas" else 0
    pof = row["pof_maks"][0]  # PoF selalu ambil batas paling ketat
    return dict(fk_statis=row["fk_statis"][i], fk_dinamis=row["fk_dinamis"], pof_maks=pof)


@dataclass
class Lapisan:
    nama: str
    z_atas: float          # elevasi atas lapisan (lapisan berlaku di bawah z_atas sampai lapisan berikutnya)
    gamma: float           # kN/m3
    c: float               # kPa
    phi: float             # derajat
    sd_c: float = 0.0      # simpangan baku untuk Monte Carlo
    sd_phi: float = 0.0
    sd_gamma: float = 0.0


@dataclass
class Material:
    lapisan: list = field(default_factory=list)   # urut dari atas ke bawah

    def at(self, z, c_s=None, phi_s=None, g_s=None):
        """Properti pada elevasi z (array). c_s/phi_s/g_s: skala sampel per lapisan untuk Monte Carlo."""
        z = np.asarray(z, float)
        idx = np.zeros(z.shape, int)
        for k, L in enumerate(self.lapisan):
            idx = np.where(z <= L.z_atas, k, idx)
        c = np.array([L.c for L in self.lapisan])
        p = np.array([L.phi for L in self.lapisan])
        g = np.array([L.gamma for L in self.lapisan])
        if c_s is not None:
            c, p, g = c_s, phi_s, g_s
        return c[idx], np.radians(p[idx]), g[idx]

    @classmethod
    def tunggal(cls, gamma, c, phi, sd_c=0.0, sd_phi=0.0, sd_gamma=0.0):
        return cls([Lapisan("massa batuan", 1e9, gamma, c, phi, sd_c, sd_phi, sd_gamma)])

    @classmethod
    def from_dict(cls, d):
        if "lapisan" in d:
            return cls([Lapisan(**L) for L in d["lapisan"]])
        return cls.tunggal(d["gamma"], d["c"], d["phi"], d.get("sd_c", 0), d.get("sd_phi", 0), d.get("sd_gamma", 0))


def profil_lereng(tinggi_jenjang, sudut_muka_deg, lebar_berm, n_jenjang, z_dasar=0.0, lantai=None, puncak=None,
                  ramp_di_jenjang=None, lebar_ramp=0.0):
    """Profil 2D lereng (x naik ke kanan; puncak di kiri, kaki di kanan). Return (xz Nx2, info)."""
    H, a = tinggi_jenjang, math.radians(sudut_muka_deg)
    dh = H / math.tan(a)
    Ht = H * n_jenjang
    lantai = lantai if lantai is not None else max(2 * Ht, 30)
    puncak = puncak if puncak is not None else max(2 * Ht, 30)
    pts = [(0.0, z_dasar + Ht)]
    x = puncak
    pts.append((x, z_dasar + Ht))
    z = z_dasar + Ht
    for k in range(n_jenjang):
        x += dh
        z -= H
        pts.append((x, z))
        if k < n_jenjang - 1:
            w = lebar_berm + (lebar_ramp if ramp_di_jenjang and (k + 1) in ramp_di_jenjang else 0.0)
            x += w
            pts.append((x, z))
    x_toe = x
    pts.append((x + lantai, z))
    horiz = n_jenjang * dh + (n_jenjang - 1) * lebar_berm
    osa = math.degrees(math.atan2(Ht, horiz + (lebar_ramp * len(ramp_di_jenjang or []))))
    ira = math.degrees(math.atan2(H, dh + lebar_berm))
    return np.array(pts), dict(tinggi_total=Ht, sudut_keseluruhan=osa, sudut_inter_ramp=ira, x_crest=puncak, x_toe=x_toe,
                               z_toe=z, z_crest=z_dasar + Ht)


def _surface(xz):
    xs, zs = xz[:, 0], xz[:, 1]
    return lambda x: np.interp(x, xs, zs)


def bishop(xz, mat: Material, xc, zc, R, ru=0.0, kh=0.0, nslice=50, props=None, water=None):
    """FK Bishop disederhanakan untuk satu lingkaran. Lereng menurun ke +x.
    water: fungsi muka air tanah zw(x) (opsional, menggantikan ru)."""
    surf = _surface(xz)
    x0, x1 = max(xc - R, xz[0, 0]), min(xc + R, xz[-1, 0])
    if x1 <= x0:
        return np.inf
    xx = np.linspace(x0, x1, 400)
    zb = zc - np.sqrt(np.clip(R ** 2 - (xx - xc) ** 2, 0, None))
    zs = surf(xx)
    m = zb < zs - 1e-6
    if m.sum() < 3:
        return np.inf
    # ambil bagian kontigu terbesar
    idx = np.where(m)[0]
    br = np.where(np.diff(idx) > 1)[0]
    segs = np.split(idx, br + 1)
    seg = max(segs, key=len)
    xa, xb = xx[seg[0]], xx[seg[-1]]
    if xb - xa < 1.0:
        return np.inf
    e = np.linspace(xa, xb, nslice + 1)
    xm = 0.5 * (e[1:] + e[:-1])
    b = np.diff(e)
    zbase = zc - np.sqrt(np.clip(R ** 2 - (xm - xc) ** 2, 0, None))
    ztop = surf(xm)
    h = np.clip(ztop - zbase, 0, None)
    alpha = np.arcsin(np.clip((xc - xm) / R, -1, 1))
    if props is None:
        c, phi, g = mat.at(zbase)
        _, _, gcol = mat.at(0.5 * (ztop + zbase))
    else:
        c, phi, g = mat.at(zbase, *props)
        _, _, gcol = mat.at(0.5 * (ztop + zbase), *props)
    W = gcol * b * h
    if water is not None:
        hw = np.clip(water(xm) - zbase, 0, h)
        u = 9.81 * hw
    else:
        u = ru * gcol * h
    tphi = np.tan(phi)
    zcen = 0.5 * (ztop + zbase)
    drive = np.sum(W * np.sin(alpha)) + np.sum(kh * W * (zc - zcen)) / R
    if drive <= 1e-9:
        return np.inf
    F = 1.2
    for _ in range(60):
        ma = np.cos(alpha) + np.sin(alpha) * tphi / F
        if np.any(ma < 0.2):
            ma = np.clip(ma, 0.2, None)
        resist = np.sum((c * b + (W - u * b) * tphi) / ma)
        Fn = resist / drive
        if abs(Fn - F) < 1e-5:
            F = Fn
            break
        F = Fn
    return float(F)


def cari_fk_min(xz, mat, ru=0.0, kh=0.0, info=None, n_pusat=14, n_keluar=12, water=None, min_kedalaman=1.0, halus=True):
    """Pencarian grid pusat lingkaran x titik keluar di sekitar kaki lereng. Return (FK, (xc,zc,R))."""
    if info is None:
        xs = xz[:, 0]
        x_crest, x_toe = xs[1], xs[-2]
        z_toe, z_crest = xz[-1, 1], xz[0, 1]
    else:
        x_crest, x_toe, z_toe, z_crest = info["x_crest"], info["x_toe"], info["z_toe"], info["z_crest"]
    H = max(z_crest - z_toe, 1.0)
    L = max(x_toe - x_crest, 1.0)
    best = (np.inf, None)
    xcs = np.linspace(x_crest - 0.3 * L, x_toe + 0.3 * H, n_pusat)
    zcs = np.linspace(z_toe + 0.6 * H, z_crest + 1.6 * H, n_pusat)
    xe = np.linspace(x_toe - 0.85 * L, x_toe + 0.25 * H, n_keluar)  # titik keluar pada/menjelang kaki
    surf = _surface(xz)
    ze = surf(xe)
    for xc in xcs:
        for zc in zcs:
            R = np.hypot(xe - xc, ze - zc)
            for Ri in R:
                if zc - Ri > z_crest - min_kedalaman:
                    continue
                F = bishop(xz, mat, xc, zc, Ri, ru, kh, water=water)
                if F < best[0]:
                    best = (F, (xc, zc, Ri))
    # penghalusan lokal
    if best[1] is not None and halus:
        xc0, zc0, R0 = best[1]
        for scale in (0.15, 0.05):
            for dx in np.linspace(-1, 1, 5) * scale * L:
                for dz in np.linspace(-1, 1, 5) * scale * H:
                    for dr in np.linspace(-1, 1, 5) * scale * H:
                        F = bishop(xz, mat, xc0 + dx, zc0 + dz, R0 + dr, ru, kh, water=water)
                        if F < best[0]:
                            best = (F, (xc0 + dx, zc0 + dz, R0 + dr))
            xc0, zc0, R0 = best[1]
    return best


def monte_carlo_pof(xz, mat: Material, circle, n=2000, ru=0.0, kh=0.0, seed=7, water=None, xz_info=None, research=12):
    """PoF = P(FK<1). Properti tiap lapisan disampel normal terpotong. Untuk sebagian sampel (research) dilakukan
    pencarian ulang kasar agar bidang kritis ikut bergeser."""
    rng = np.random.default_rng(seed)
    Ls = mat.lapisan
    C = np.array([[max(rng.normal(L.c, L.sd_c), 0.0) for L in Ls] for _ in range(n)])
    P = np.array([[float(np.clip(rng.normal(L.phi, L.sd_phi), 1, 70)) for L in Ls] for _ in range(n)])
    G = np.array([[max(rng.normal(L.gamma, L.sd_gamma), 5.0) for L in Ls] for _ in range(n)])
    xc, zc, R = circle
    F = np.array([bishop(xz, mat, xc, zc, R, ru, kh, props=(C[i], P[i], G[i]), water=water) for i in range(n)])
    # pencarian ulang kasar untuk sampel terlemah
    weakest = np.argsort(F)[:research]
    for i in weakest:
        sub = Material([Lapisan(L.nama, L.z_atas, G[i][k], C[i][k], P[i][k]) for k, L in enumerate(Ls)])
        Fi, _ = cari_fk_min(xz, sub, ru, kh, xz_info, n_pusat=6, n_keluar=6, water=water, halus=False)
        F[i] = min(F[i], Fi)
    return float(np.mean(F < 1.0)), dict(fk_rata=float(np.mean(F)), fk_sd=float(np.std(F)), n=n,
                                         fk_p5=float(np.percentile(F, 5)))


def evaluasi(geom: dict, mat: Material, cof="menengah", ru=0.0, kh=0.1, n_mc=1000, kr=None, water=None):
    """Evaluasi lengkap: lereng tunggal, inter-ramp (2 jenjang + berm) dan keseluruhan."""
    kr = kr or load_kriteria()
    out = {}
    H, a, b, n = geom["tinggi_jenjang"], geom["sudut_muka"], geom["lebar_berm"], geom["jumlah_jenjang"]
    nir = int(geom.get("jenjang_per_inter_ramp", min(n, 4)))
    cases = [("tunggal", 1), ("inter_ramp", min(nir, n)), ("keseluruhan", n)]
    for jenis, nj in cases:
        # lereng tunggal & inter-ramp dievaluasi di bagian ATAS dinding (umumnya zona paling lapuk = kritis)
        z0 = geom.get("z_dasar", 0.0) + (n - nj) * H
        xz, info = profil_lereng(H, a, b, nj, z_dasar=z0,
                                 ramp_di_jenjang=geom.get("ramp_di_jenjang") if jenis == "keseluruhan" else None,
                                 lebar_ramp=geom.get("lebar_ramp", 0.0))
        fs, circ = cari_fk_min(xz, mat, ru, 0.0, info, water=water)
        fd, circ_d = cari_fk_min(xz, mat, ru, kh, info, water=water) if kh > 0 else (None, None)
        pof, mc = monte_carlo_pof(xz, mat, circ, n_mc, ru, 0.0, water=water, xz_info=info) if circ else (1.0, {})
        sy = syarat(jenis, cof, kr)
        ok = fs >= sy["fk_statis"] and pof <= sy["pof_maks"] and (sy["fk_dinamis"] is None or fd is None or fd >= sy["fk_dinamis"])
        out[jenis] = dict(jumlah_jenjang=nj, tinggi=info["tinggi_total"], sudut=info["sudut_keseluruhan"],
                          fk_statis=fs, fk_dinamis=fd, pof=pof, mc=mc, lingkaran=circ, lingkaran_dinamis=circ_d,
                          syarat=sy, status="MEMENUHI" if ok else "TIDAK MEMENUHI", xz=xz.tolist())
    return out


def optimasi_geometri(mat, cof, tinggi_jenjang, n_jenjang, sudut_muka_opsi=(45, 50, 55, 60, 65, 70),
                      berm_opsi=(3, 4, 5, 6, 8, 10), ru=0.0, kh=0.1, n_mc=300, kr=None, water=None, berm_min=None, z_dasar=0.0):
    """Cari kombinasi sudut muka & lebar berm dengan sudut keseluruhan paling curam yang memenuhi Kepmen."""
    kr = kr or load_kriteria()
    cands = []
    for a in sudut_muka_opsi:
        for b in berm_opsi:
            if berm_min and b < berm_min:
                continue
            xz, info = profil_lereng(tinggi_jenjang, a, b, n_jenjang, z_dasar=z_dasar)
            cands.append((info["sudut_keseluruhan"], a, b))
    cands.sort(reverse=True)
    tried = []
    sy_k = syarat("keseluruhan", cof, kr)
    for osa, a, b in cands:
        # saringan cepat: FK statis & dinamis lereng keseluruhan
        xz, info = profil_lereng(tinggi_jenjang, a, b, n_jenjang, z_dasar=z_dasar)
        fs, _ = cari_fk_min(xz, mat, ru, 0.0, info, n_pusat=9, n_keluar=8, water=water, halus=False)
        fd, _ = cari_fk_min(xz, mat, ru, kh, info, n_pusat=9, n_keluar=8, water=water, halus=False) if kh > 0 else (9, None)
        if fs < sy_k["fk_statis"] * 0.97 or (sy_k["fk_dinamis"] and fd < sy_k["fk_dinamis"] * 0.97):
            tried.append(dict(sudut_muka=a, lebar_berm=b, sudut_keseluruhan=osa, lolos=False, fk_keseluruhan=fs, pof_keseluruhan=float("nan")))
            continue
        g = dict(tinggi_jenjang=tinggi_jenjang, sudut_muka=a, lebar_berm=b, jumlah_jenjang=n_jenjang, z_dasar=z_dasar)
        ev = evaluasi(g, mat, cof, ru, kh, n_mc, kr, water)
        ok = all(v["status"] == "MEMENUHI" for v in ev.values())
        tried.append(dict(sudut_muka=a, lebar_berm=b, sudut_keseluruhan=osa, lolos=ok,
                          fk_keseluruhan=ev["keseluruhan"]["fk_statis"], pof_keseluruhan=ev["keseluruhan"]["pof"]))
        if ok:
            return dict(sudut_muka=a, lebar_berm=b, sudut_keseluruhan=osa, evaluasi=ev, dicoba=tried)
    return dict(sudut_muka=None, lebar_berm=None, sudut_keseluruhan=None, evaluasi=None, dicoba=tried)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Cek FK/PoF lereng terhadap Kepmen 1827")
    ap.add_argument("--H", type=float, default=10)
    ap.add_argument("--muka", type=float, default=60)
    ap.add_argument("--berm", type=float, default=5)
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--gamma", type=float, default=20)
    ap.add_argument("--c", type=float, default=60)
    ap.add_argument("--phi", type=float, default=30)
    ap.add_argument("--ru", type=float, default=0.1)
    ap.add_argument("--kh", type=float, default=0.1)
    ap.add_argument("--cof", default="menengah")
    a = ap.parse_args()
    mat = Material.tunggal(a.gamma, a.c, a.phi, a.c * 0.2, 3.0, 0.5)
    ev = evaluasi(dict(tinggi_jenjang=a.H, sudut_muka=a.muka, lebar_berm=a.berm, jumlah_jenjang=a.n), mat, a.cof, a.ru, a.kh, 500)
    for k, v in ev.items():
        print(f"{k:12s} H={v['tinggi']:.0f} m sudut={v['sudut']:.1f} FKs={v['fk_statis']:.2f} FKd={v['fk_dinamis'] or 0:.2f} "
              f"PoF={v['pof'] * 100:.1f}% syarat={v['syarat']} -> {v['status']}")
