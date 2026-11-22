#!/usr/bin/env python3
"""Desain pit tambang terbuka dari block model, sesuai Kepmen ESDM 1827 K/30/MEM/2018 (geoteknik hal. 57-58,
tambang permukaan hal. 84, 91-94; jalan/ramp hal. 99-100).

Alur:
 1. Block model (CSV x,y,z,kadar,densitas atau demo sintetis) -> nilai ekonomi per blok
 2. Geoteknik: evaluasi / optimasi geometri jenjang (FK Bishop + PoF Monte Carlo) -> sudut lereng keseluruhan
 3. Pit akhir (ultimate pit) = penutupan maksimum (Lerchs-Grossmann setara) via min-cut / max-flow
 4. Desain jenjang (crest/toe), berm, ramp spiral (lebar 3,5 x unit, grade <= 12%), bottom minimum
 5. Permukaan desain 3D (TIN), cadangan dalam desain, nisbah kupas, penampang 2D
 6. Ekspor LandXML/DXF/OBJ/STL/CSV + lembar PDF + laporan kepatuhan

Pakai:
  python3 pit_design.py --demo --out hasil_pit/
  python3 pit_design.py --config pit.json --out hasil_pit/
"""
from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cad_export as cx  # noqa: E402
import geotek as gt  # noqa: E402

DEFAULT = {
    "proyek": "Desain Pit",
    "perusahaan": "",
    "epsg": None,
    "block_model": {"sumber": "demo", "kolom": {"x": "x", "y": "y", "z": "z", "kadar": "kadar", "densitas": "densitas"},
                    "ukuran_blok": [10.0, 10.0, 5.0]},
    "topografi": {"sumber": "demo"},
    "ekonomi": {"harga_per_ton_logam": 9000.0, "satuan_kadar": "%", "recovery": 0.85, "biaya_olah_per_ton": 18.0,
                "biaya_tambang_per_ton": 2.5, "biaya_tambahan_per_m_kedalaman": 0.01, "faktor_pendapatan": 1.0},
    "geoteknik": {
        "keparahan_longsor": "menengah",
        "ru": 0.1, "kh": 0.10,
        "material": {"lapisan": [
            {"nama": "zona lapuk", "z_atas": 1e9, "gamma": 18.5, "c": 40.0, "phi": 28.0, "sd_c": 8.0, "sd_phi": 2.5, "sd_gamma": 0.5},
            {"nama": "batuan segar", "z_atas": 150.0, "gamma": 25.0, "c": 250.0, "phi": 38.0, "sd_c": 40.0, "sd_phi": 3.0, "sd_gamma": 0.5}]},
        "optimasi": True,
        "tinggi_jenjang": 10.0, "sudut_muka": 60.0, "lebar_berm": 6.0,
        "sudut_muka_opsi": [50, 55, 60, 65, 70], "berm_opsi": [5, 6, 7, 8, 10],
        "jenjang_per_inter_ramp": 4,
        "n_monte_carlo": 600,
    },
    "ramp": {"lebar_unit_m": 3.5, "jumlah_jalur": 2, "diameter_roda_m": 1.6, "grade": 0.10, "azimut_awal_deg": 200.0,
             "arah": "ccw", "lebar_saluran_m": 1.0, "jumlah_akses": 1},
    "dasar_pit_min_m": 30.0,
    "jangkauan_alat_gali_m": 10.5,
    "grid_permukaan_m": 2.5,
    "penampang": [],
    "cutoff_kadar": None,
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
    return cfg


# =============================================================================== data
def demo_topo(X, Y):
    return 160 + 0.04 * X - 0.02 * Y + 18 * np.exp(-(((X - 250) / 220) ** 2 + ((Y - 300) / 180) ** 2)) + 2 * np.sin(X / 60) * np.cos(Y / 80)


def demo_block_model(dims=(10.0, 10.0, 5.0), nx=50, ny=50, nz=38, x0=0.0, y0=0.0, z0=0.0, seed=3):
    """Endapan sintetis: tubuh bijih miring + kadar menurun ke tepi + derau. z0 = dasar model."""
    rng = np.random.default_rng(seed)
    dx, dy, dz = dims
    xs = x0 + dx / 2 + dx * np.arange(nx)
    ys = y0 + dy / 2 + dy * np.arange(ny)
    zs = z0 + dz / 2 + dz * np.arange(nz)
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    T = demo_topo(X, Y)
    keep = Z + dz / 2 <= T + dz / 2  # blok yang centroid-nya di bawah topografi (+toleransi setengah blok)
    keep &= Z <= T
    # sumbu tubuh bijih miring
    cx_, cy_ = 250 + 0.35 * (Z - 120), 260 + 0.1 * (Z - 120)
    r2 = ((X - cx_) / 90) ** 2 + ((Y - cy_) / 65) ** 2 + ((Z - 118) / 32) ** 2
    g = 1.4 * np.exp(-r2) * (1 + rng.normal(0, 0.15, X.shape))
    g = np.clip(g, 0, None)
    dens = np.where(Z > T - 20, 1.9, 2.6) + rng.normal(0, 0.03, X.shape)
    df = dict(x=X[keep], y=Y[keep], z=Z[keep], kadar=g[keep], densitas=dens[keep])
    return {k: np.asarray(v) for k, v in df.items()}


def load_block_model(cfg):
    bm = cfg["block_model"]
    if bm["sumber"] == "demo":
        return demo_block_model(tuple(bm["ukuran_blok"]))
    import pandas as pd

    df = pd.read_csv(bm["sumber"])
    k = bm["kolom"]
    out = {n: df[k[n]].to_numpy(float) for n in ("x", "y", "z", "kadar")}
    out["densitas"] = df[k["densitas"]].to_numpy(float) if k.get("densitas") in df else np.full(len(df), bm.get("densitas_default", 2.5))
    return out


def topo_from_cfg(cfg, bm):
    t = cfg["topografi"]
    if t.get("sumber", "demo") == "demo":
        x0, x1 = bm["x"].min() - 150, bm["x"].max() + 150
        y0, y1 = bm["y"].min() - 150, bm["y"].max() + 150
        return cx.Terrain.from_function(demo_topo, x0, x1, y0, y1, 5.0)
    src = t["sumber"]
    if src.lower().endswith(".xml"):
        return cx.Terrain.from_landxml(src, t.get("nama_surface"))
    return cx.Terrain.from_csv(src)


# =============================================================================== ekonomi & pit akhir
def nilai_blok(cfg, bm, dims):
    e = cfg["ekonomi"]
    vol = dims[0] * dims[1] * dims[2]
    ton = vol * bm["densitas"]
    gr = bm["kadar"] / (100.0 if e["satuan_kadar"] == "%" else 1e6 if e["satuan_kadar"] == "ppm" else 1.0)
    rev_t = gr * e["recovery"] * e["harga_per_ton_logam"] * e["faktor_pendapatan"]
    zmax = bm["z"].max()
    cmine = e["biaya_tambang_per_ton"] + e["biaya_tambahan_per_m_kedalaman"] * (zmax - bm["z"])
    cutoff = cfg["cutoff_kadar"]
    if cutoff is None:
        cutoff = e["biaya_olah_per_ton"] / (e["recovery"] * e["harga_per_ton_logam"]) * (100.0 if e["satuan_kadar"] == "%" else 1.0)
    ore = (rev_t > e["biaya_olah_per_ton"]) & (bm["kadar"] >= cutoff)
    val = np.where(ore, ton * (rev_t - e["biaya_olah_per_ton"] - cmine), -ton * cmine)
    return val, ton, ore, cutoff


def ultimate_pit(bm, dims, val, sudut_deg, maks_level=8):
    """Penutupan maksimum (setara Lerchs-Grossmann) via min-cut (scipy.sparse.csgraph.maximum_flow).
    Preseden kerucut: blok di atas dalam radius l*dz/tan(sudut), l=1..maks_level. Blok udara diabaikan,
    blok di luar batas model melarang penambangan (konservatif)."""
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import breadth_first_order, maximum_flow

    dx, dy, dz = dims
    x0, y0, z0 = bm["x"].min(), bm["y"].min(), bm["z"].min()
    i = np.rint((bm["x"] - x0) / dx).astype(int)
    j = np.rint((bm["y"] - y0) / dy).astype(int)
    k = np.rint((bm["z"] - z0) / dz).astype(int)
    nx, ny, nz = i.max() + 1, j.max() + 1, k.max() + 1
    lut = -np.ones((nx, ny, nz), int)
    lut[i, j, k] = np.arange(len(i))
    # kolom tertinggi berisi blok (di atasnya udara)
    top = -np.ones((nx, ny), int)
    np.maximum.at(top, (i, j), k)
    N = len(i)
    src, dst = [], []
    forbid = np.zeros(N, bool)
    t = math.tan(math.radians(sudut_deg))
    for l in range(1, maks_level + 1):
        r = l * dz / t
        ri, rj = int(r // dx), int(r // dy)
        r_prev = (l - 1) * dz / t
        # hanya cincin baru (offset dalam radius sebelumnya sudah tercakup lewat rantai preseden)
        offs = [(a, b) for a in range(-ri, ri + 1) for b in range(-rj, rj + 1)
                if (a * dx) ** 2 + (b * dy) ** 2 <= r ** 2 + 1e-6
                and (l == 1 or math.hypot(a * dx, b * dy) > r_prev + 1e-6)]
        kk = k + l
        for a, b in offs:
            ii, jj = i + a, j + b
            inside = (ii >= 0) & (ii < nx) & (jj >= 0) & (jj < ny)
            m_out = ~inside & (kk < nz + 50)
            # di luar model lateral: hanya larang bila blok itu bukan udara (asumsi model mencakup seluruh area relevan)
            forbid |= m_out & (kk <= k.max())
            ii_c, jj_c = np.clip(ii, 0, nx - 1), np.clip(jj, 0, ny - 1)
            ok = inside & (kk < nz)
            tgt = np.full(N, -1)
            tgt[ok] = lut[ii_c[ok], jj_c[ok], kk[ok]]
            m = tgt >= 0
            src.append(np.nonzero(m)[0])
            dst.append(tgt[m])
    src = np.concatenate(src)
    dst = np.concatenate(dst)
    pos = val.clip(min=0)
    scale = 4e8 / max(pos.sum(), 1.0)
    v = np.rint(val * scale).astype(np.int64)
    INF = np.int64(1_000_000_000)
    S, T = N, N + 1
    rows = [np.full((v > 0).sum(), S), np.nonzero(v < 0)[0], src, np.nonzero(forbid)[0]]
    cols = [np.nonzero(v > 0)[0], np.full((v < 0).sum(), T), dst, np.full(forbid.sum(), T)]
    caps = [v[v > 0], -v[v < 0], np.full(len(src), INF), np.full(forbid.sum(), INF)]
    r_, c_, w_ = np.concatenate(rows), np.concatenate(cols), np.concatenate(caps).astype(np.int64)
    w_ = np.minimum(w_, INF).astype(np.int32)
    G = csr_matrix((w_, (r_, c_)), shape=(N + 2, N + 2))
    G.sum_duplicates()
    res = maximum_flow(G, S, T, method="dinic")
    F = res.flow
    Rm = (G - F).tocsr()
    Rm.data = np.where(Rm.data > 0, 1, 0)
    Rm.eliminate_zeros()
    order = breadth_first_order(Rm, S, directed=True, return_predecessors=False)
    mined = np.zeros(N, bool)
    order = order[order < N]
    mined[order] = True
    return mined, dict(nilai=float(val[mined].sum()), n_blok=int(mined.sum()), busur=int(len(src)))


# =============================================================================== desain jenjang
def _largest(geom):
    from shapely.geometry import MultiPolygon, Polygon

    if geom.is_empty:
        return geom
    if isinstance(geom, MultiPolygon):
        return max(geom.geoms, key=lambda g: g.area)
    if isinstance(geom, Polygon):
        return Polygon(geom.exterior)  # buang lubang
    polys = [g for g in getattr(geom, "geoms", []) if g.geom_type == "Polygon"]
    return max(polys, key=lambda g: g.area) if polys else geom


def footprint(bm, mask, dims, z_lantai):
    """Jejak blok tertambang pada level blok yang dasarnya = z_lantai."""
    from shapely.geometry import box
    from shapely.ops import unary_union

    dx, dy, dz = dims
    sel = mask & (np.abs((bm["z"] - dz / 2) - z_lantai) < 1e-3)
    if not sel.any():
        return None
    boxes = [box(x - dx / 2, y - dy / 2, x + dx / 2, y + dy / 2) for x, y in zip(bm["x"][sel], bm["y"][sel])]
    g = unary_union(boxes).buffer(dx, join_style=1).buffer(-1.5 * dx, join_style=1).buffer(0.5 * dx, join_style=1)
    if g.is_empty:
        g = unary_union(boxes)
    return g.simplify(0.5)


def ring_segment(poly, start_xy, L, ccw=True):
    from shapely.geometry import LineString, Point
    from shapely.geometry.polygon import orient
    from shapely.ops import substring

    ring = LineString(orient(poly, 1.0).exterior.coords)
    if not ccw:
        ring = LineString(list(ring.coords)[::-1])
    P = ring.length
    L = min(L, 0.9 * P)
    s0 = ring.project(Point(start_xy))
    if s0 + L <= P:
        seg = substring(ring, s0, s0 + L)
    else:
        a = substring(ring, s0, P)
        b = substring(ring, 0, s0 + L - P)
        seg = LineString(list(a.coords) + list(b.coords)[1:])
    return seg


def desain_jenjang(cfg, bm, mined, dims, topo, H, sudut_muka, berm, ramp_w, ramp_grade):
    from shapely.geometry import Point

    dx, dy, dz = dims
    nb = max(1, int(round(H / dz)))
    zb0 = bm["z"].min() - dz / 2
    floors_all = zb0 + H * np.arange(0, int((bm["z"].max() - zb0) / H) + 3)
    wmin = cfg["dasar_pit_min_m"]
    dh = H / math.tan(math.radians(sudut_muka))
    benches = []
    T = None
    start = None
    ccw = cfg["ramp"]["arah"] == "ccw"
    zmax_topo = float(topo.pts[:, 2].max())
    for zf in floors_all:
        shell = None
        for sub in range(nb):
            fp = footprint(bm, mined, dims, zf + sub * dz)
            if fp is not None and not fp.is_empty:
                shell = fp if shell is None else shell.union(fp)
        if T is None:
            if shell is None:
                continue
            core = shell.buffer(-wmin / 2).buffer(wmin / 2)
            if core.is_empty or core.area < wmin ** 2 * 0.7:
                continue
            T = _largest(core)
            c = T.centroid
            az = math.radians(cfg["ramp"]["azimut_awal_deg"])
            far = Point(c.x + 5000 * math.sin(az), c.y + 5000 * math.cos(az))
            from shapely.geometry import LineString
            inter = LineString([c, far]).intersection(T.exterior)
            start = (inter.coords[0] if inter.geom_type == "Point" else list(getattr(inter, "geoms", [inter]))[0].coords[0])
        else:
            if shell is not None:
                T = _largest(T.union(shell))
        # ramp untuk jenjang ini
        Lr = H / ramp_grade
        seg = ring_segment(T, start, Lr, ccw)
        band = seg.buffer(ramp_w, cap_style=2, join_style=2).difference(T)
        band = _largest(band) if not band.is_empty else band
        U = T.union(band) if not band.is_empty else T
        C = _largest(U.buffer(dh, join_style=2, mitre_limit=2.0))
        benches.append(dict(z=float(zf), toe=T, ramp=band, seg=seg, crest=C, U=U))
        # berikutnya
        T = _largest(C.buffer(berm, join_style=2, mitre_limit=2.0))
        end = seg.coords[-1]
        start = T.exterior.interpolate(T.exterior.project(Point(end))).coords[0]
        # berhenti bila seluruh toe berikut di atas topografi
        ring = np.array(T.exterior.coords)
        if zf + H > zmax_topo or np.all(topo.z(ring[:, 0], ring[:, 1]) < zf + H):
            break
    return benches, dict(dh=dh, n_level_per_jenjang=nb)


def z_desain(benches, X, Y, sudut_muka, topo=None):
    """Elevasi permukaan pit (tanpa topografi) di titik X,Y."""
    import shapely

    X = np.asarray(X, float).ravel()
    Y = np.asarray(Y, float).ravel()
    P = shapely.points(X, Y)
    Z = np.full(X.shape, np.inf)
    done = np.zeros(X.shape, bool)
    tf = math.tan(math.radians(sudut_muka))
    for b in benches:
        H = (benches[1]["z"] - benches[0]["z"]) if len(benches) > 1 else 10.0
        m = ~done & shapely.contains_xy(b["toe"], X, Y)
        Z[m] = b["z"]; done |= m
        if not b["ramp"].is_empty:
            m = ~done & shapely.contains_xy(b["ramp"], X, Y)
            if m.any():
                fr = shapely.line_locate_point(b["seg"], P[m]) / b["seg"].length
                Z[m] = b["z"] + H * fr; done |= m
        m = ~done & shapely.contains_xy(b["crest"], X, Y)
        if m.any():
            dT = shapely.distance(b["U"].boundary, P[m])
            dC = shapely.distance(b["crest"].boundary, P[m])
            base = np.full(m.sum(), b["z"])
            if not b["ramp"].is_empty:
                dR = shapely.distance(b["ramp"], P[m])
                dTo = shapely.distance(b["toe"], P[m])
                onr = dR < dTo
                if onr.any():
                    fr = shapely.line_locate_point(b["seg"], P[m][onr]) / b["seg"].length
                    base[onr] = b["z"] + H * fr
            top = b["z"] + H
            Z[m] = base + (top - base) * dT / np.maximum(dT + dC, 1e-9)
            done |= m
    # badan ramp: lereng dari tepi ramp ke bawah dengan sudut muka
    for b in benches:
        if b["ramp"].is_empty:
            continue
        H = (benches[1]["z"] - benches[0]["z"]) if len(benches) > 1 else 10.0
        d = shapely.distance(b["ramp"], P)
        near = (d > 0) & (d < H / tf * 1.2)
        if near.any():
            fr = shapely.line_locate_point(b["seg"], P[near]) / b["seg"].length
            zr = b["z"] + H * fr - d[near] * tf
            Z[near] = np.maximum(Z[near], zr)
    if topo is not None:
        Z = np.minimum(Z, topo.z(X, Y))
    return Z


def _ring_strings(poly_ring_xy, z_of, topo, step=2.0):
    """Sampel cincin, buang bagian di atas topografi -> list potongan 3D."""
    from shapely.geometry import LineString

    ls = LineString(poly_ring_xy)
    n = max(int(ls.length / step), 8)
    pts = np.array([ls.interpolate(t).coords[0] for t in np.linspace(0, ls.length, n)])
    z = z_of(pts)
    tz = topo.z(pts[:, 0], pts[:, 1])
    ok = z <= tz + 0.05
    runs, cur = [], []
    for p, zz, o in zip(pts, z, ok):
        if o:
            cur.append((p[0], p[1], zz))
        elif cur:
            if len(cur) > 1:
                runs.append(np.array(cur))
            cur = []
    if len(cur) > 1:
        runs.append(np.array(cur))
    return runs


# =============================================================================== utama
DEMO_CFG = {"proyek": "Contoh Desain Pit A (DEMO, data sintetis)", "perusahaan": "PT. Surya Saga Utama", "epsg": 32751}


def run(cfg, out):
    os.makedirs(out, exist_ok=True)
    kr = gt.load_kriteria()
    dims = tuple(cfg["block_model"]["ukuran_blok"])
    bm = load_block_model(cfg)
    topo = topo_from_cfg(cfg, bm)
    val, ton, ore, cutoff = nilai_blok(cfg, bm, dims)
    g = cfg["geoteknik"]
    mat = gt.Material.from_dict(g["material"])
    H = g["tinggi_jenjang"]
    cof = g["keparahan_longsor"]
    # perkiraan tinggi lereng: pit akhir awal dengan sudut sementara, lalu geoteknik untuk tinggi itu
    mined0, _ = ultimate_pit(bm, dims, val, g.get("sudut_awal_deg", 40.0))
    if not mined0.any():
        raise SystemExit("Tidak ada blok ekonomis - cek harga/biaya/kadar.")
    zt = float(np.max(topo.z(bm["x"][mined0], bm["y"][mined0])))
    z_ore_min = float(bm["z"][mined0].min())
    n_jenjang = max(2, int(math.ceil((zt - (z_ore_min - dims[2] / 2)) / H)))
    # sesuaikan elevasi lapisan ke koordinat profil (profil dimulai dari z_dasar = dasar pit perkiraan)
    if g["optimasi"]:
        opt = gt.optimasi_geometri(mat, cof, H, n_jenjang, g["sudut_muka_opsi"], g["berm_opsi"], g["ru"], g["kh"],
                                   max(200, g["n_monte_carlo"] // 3), kr, berm_min=_berm_min(cfg, H),
                                   z_dasar=z_ore_min - dims[2] / 2)
        if opt["sudut_muka"] is None:
            raise SystemExit("Tidak ada kombinasi geometri jenjang yang memenuhi Kepmen 1827. Perlebar opsi berm/sudut atau tinjau parameter material.")
        sudut_muka, berm = opt["sudut_muka"], opt["lebar_berm"]
    else:
        opt = None
        sudut_muka, berm = g["sudut_muka"], g["lebar_berm"]
    geom = dict(tinggi_jenjang=H, sudut_muka=sudut_muka, lebar_berm=berm, jumlah_jenjang=n_jenjang,
                jenjang_per_inter_ramp=g["jenjang_per_inter_ramp"], z_dasar=z_ore_min - dims[2] / 2)
    _, info_geo = gt.profil_lereng(H, sudut_muka, berm, n_jenjang)
    osa = info_geo["sudut_keseluruhan"]

    # ramp
    rp = cfg["ramp"]
    Hb = 0.75 * rp["diameter_roda_m"]
    lebar_tanggul = 2 * 1.5 * Hb + 0.6
    ramp_w = (3.5 if rp["jumlah_jalur"] >= 2 else 2.0) * rp["lebar_unit_m"] + lebar_tanggul + rp["lebar_saluran_m"]
    ramp_grade = min(rp["grade"], 0.12)

    # pit akhir dengan sudut keseluruhan dikurangi kelonggaran ramp
    sudut_opt = max(osa - 3.0, 25.0)
    mined, upinfo = ultimate_pit(bm, dims, val, sudut_opt)
    benches, dinfo = desain_jenjang(cfg, bm, mined, dims, topo, H, sudut_muka, berm, ramp_w, ramp_grade)
    if not benches:
        raise SystemExit("Pit akhir kosong / tidak ekonomis dengan parameter ini.")

    # permukaan
    from shapely.ops import unary_union
    outer = benches[-1]["crest"].buffer(60)
    x0, y0, x1, y1 = outer.bounds
    st = cfg["grid_permukaan_m"]
    gx, gy = np.arange(x0, x1, st), np.arange(y0, y1, st)
    GX, GY = np.meshgrid(gx, gy)
    ZP = z_desain(benches, GX, GY, sudut_muka, topo).reshape(GX.shape)
    ZT = topo.z(GX.ravel(), GY.ravel()).reshape(GX.shape)
    fin_pts, fin_tris = cx.grid_tin(gx, gy, ZP)
    eg_pts, eg_tris = cx.grid_tin(gx, gy, ZT)
    inpit = ZP < ZT - 0.05
    pit_pts, pit_tris = cx.grid_tin(gx, gy, np.where(inpit | np.roll(inpit, 1, 0) | np.roll(inpit, 1, 1), ZP, np.nan))

    # cadangan dalam desain
    zd_blk = z_desain(benches, bm["x"], bm["y"], sudut_muka, topo)
    in_design = bm["z"] > zd_blk  # centroid di atas permukaan desain = tergali
    vol_cut, _ = cx.tin_volume_between(fin_pts, fin_tris, topo.z)
    rep = _tonase(bm, ton, ore, in_design, mined, val)

    # cek geoteknik pada geometri final (tinggi lereng aktual)
    z_bottom = benches[0]["z"]
    crest_ring = np.array(benches[-1]["crest"].exterior.coords)
    h_dinding = float(np.max(np.minimum(topo.z(crest_ring[:, 0], crest_ring[:, 1]), benches[-1]["z"] + H)) - z_bottom)
    n_final = max(2, int(round(h_dinding / H)))
    geom.update(jumlah_jenjang=n_final, z_dasar=z_bottom)
    mat_shift = gt.Material([gt.Lapisan(L.nama, L.z_atas, L.gamma, L.c, L.phi, L.sd_c, L.sd_phi, L.sd_gamma) for L in mat.lapisan])
    ev = gt.evaluasi(geom, mat_shift, cof, g["ru"], g["kh"], g["n_monte_carlo"], kr)

    # pemeriksaan kepatuhan
    chk = []
    def add(item, nilai, syarat, ok, dasar, ket=""):
        chk.append(dict(item=item, nilai=nilai, syarat=syarat, status="MEMENUHI" if ok else "TIDAK MEMENUHI", dasar=dasar, ket=ket))
    for jenis, v in ev.items():
        sy = v["syarat"]
        fd = f", FKd {v['fk_dinamis']:.2f}" if v["fk_dinamis"] is not None else ""
        add(f"Lereng {jenis.replace('_', '-')} (H {v['tinggi']:.0f} m, {v['sudut']:.1f} deg)",
            f"FKs {v['fk_statis']:.2f}{fd}, PoF {v['pof'] * 100:.1f}%",
            f"FKs >= {sy['fk_statis']}" + (f", FKd >= {sy['fk_dinamis']}" if sy["fk_dinamis"] else "") + f", PoF <= {sy['pof_maks'] * 100:.0f}% (CoF {cof})",
            v["status"] == "MEMENUHI", "Kepmen 1827 Tabel 1 hal. 57")
    jt = cfg["jangkauan_alat_gali_m"]
    add("Tinggi jenjang vs jangkauan alat gali", f"{H:.1f} m", f"<= {jt:.1f} m", H <= jt + 1e-9, "Kepmen 1827 hal. 91 (xiv.xi)")
    add("Lebar ramp (2 jalur + tanggul + saluran)", f"{ramp_w:.2f} m", f">= {3.5 if rp['jumlah_jalur'] >= 2 else 2.0} x {rp['lebar_unit_m']} m + tanggul",
        True, "Kepmen 1827 hal. 99 (i)")
    add("Grade ramp", f"{ramp_grade * 100:.1f}%", "<= 12%", ramp_grade <= 0.12 + 1e-9, "Kepmen 1827 hal. 99 (vii)")
    add("Tanggul pengaman ramp", f"{Hb:.2f} m", f">= 3/4 x {rp['diameter_roda_m']} m", True, "Kepmen 1827 hal. 99 (ii)")
    jr = kr["tambang_permukaan"]["jarak_aman_bibir_pit_akhir_m"]
    jarak_bibir = jr["konstanta"] + jr["persen_tinggi_lereng"] * h_dinding
    add("Jarak aman bibir pit akhir", f"{jarak_bibir:.1f} m (tandai di lapangan)", "1 m + 4% tinggi lereng", True, "Kepmen 1827 hal. 94 (xvi.viii) [verifikasi]")
    add("Peledakan dekat lereng akhir", f"baris terakhir >= {2 * H:.0f} m dari lereng akhir", "2 x tinggi jenjang", True, "Kepmen 1827 hal. 93 (xvi.iii)")
    nak = rp.get("jumlah_akses", 1)
    add("Jumlah akses keluar pit", f"{nak} akses (kedalaman {h_dinding:.0f} m)", "2 akses bila kedalaman akhir > 45 m",
        h_dinding <= 45 or nak >= 2, "Kepmen 1827 hal. 95", "tambahkan jalan akses/darurat kedua lalu set ramp.jumlah_akses")
    add("Lebar dasar pit minimum", f"{cfg['dasar_pit_min_m']:.0f} m", "cukup untuk manuver alat (praktik)", True, "Praktik rekayasa")

    summary = dict(proyek=cfg["proyek"], geometri=dict(tinggi_jenjang=H, sudut_muka=sudut_muka, lebar_berm=berm,
                   sudut_inter_ramp=info_geo["sudut_inter_ramp"], sudut_keseluruhan=osa, sudut_optimasi_pit=sudut_opt,
                   lebar_ramp=ramp_w, grade_ramp=ramp_grade, tinggi_dinding_maks=h_dinding, dasar_pit=z_bottom,
                   jumlah_jenjang=len(benches)), cutoff=cutoff, pit_akhir=upinfo, cadangan=rep,
                   volume_galian_tin_m3=vol_cut, geoteknik={k: {kk: vv for kk, vv in v.items() if kk != "xz"} for k, v in ev.items()},
                   optimasi_geoteknik=(opt or {}).get("dicoba"), pemeriksaan=chk,
                   lolos_semua=all(c["status"] == "MEMENUHI" for c in chk))

    # ---------------- ekspor
    def zfun(pts):
        return z_desain(benches, pts[:, 0], pts[:, 1], sudut_muka, None)
    crest_runs, toe_runs, ramp_runs, shell_rings = [], [], [], []
    for b in benches:
        toe_runs += [(b["z"], r) for r in _ring_strings(np.array(b["toe"].exterior.coords), lambda p, z=b["z"]: np.full(len(p), z), topo)]
        crest_runs += [(b["z"] + H, r) for r in _ring_strings(np.array(b["crest"].exterior.coords), lambda p, z=b["z"] + H: np.full(len(p), z), topo)]
        seg = np.array(b["seg"].coords)
        # garis tengah ramp: geser keluar setengah lebar
        from shapely.geometry import LineString
        segL = LineString(seg)
        n = max(int(segL.length / 2), 4)
        cl = []
        for tpar in np.linspace(0, segL.length, n):
            p = np.array(segL.interpolate(tpar).coords[0])
            p2 = np.array(segL.interpolate(min(tpar + 0.5, segL.length)).coords[0])
            p1 = np.array(segL.interpolate(max(tpar - 0.5, 0)).coords[0])
            tv = (p2 - p1) / max(np.linalg.norm(p2 - p1), 1e-9)
            nv = np.array([tv[1], -tv[0]])
            import shapely
            if shapely.contains_xy(b["toe"], *(p + nv * 0.5)):
                nv = -nv
            q = p + nv * ramp_w / 2
            cl.append((q[0], q[1], b["z"] + H * tpar / segL.length))
        cl = np.array(cl)
        tz = topo.z(cl[:, 0], cl[:, 1])
        cl = cl[cl[:, 2] <= tz + 0.1]
        if len(cl) > 1:
            ramp_runs.append(cl)
    for zf in sorted(set(np.round(bm["z"][mined] - dims[2] / 2, 3))):
        fp = footprint(bm, mined, dims, zf)
        if fp is not None:
            for g_ in getattr(fp, "geoms", [fp]):
                if g_.geom_type == "Polygon":
                    shell_rings.append((zf, np.array(g_.exterior.coords)))

    lx = cx.LandXML(cfg["proyek"], "Desain pit - Kepmen ESDM 1827 K/30/MEM/2018", cfg.get("epsg"), cfg.get("perusahaan", ""))
    lx.add_surface("EG_Topografi", eg_pts, eg_tris, "Topografi awal")
    brk = [("CREST", r) for _, r in crest_runs] + [("TOE", r) for _, r in toe_runs]
    lx.add_surface("Pit_Desain_Final", fin_pts, fin_tris, "Permukaan akhir (topografi + pit)", brk)
    if len(pit_tris):
        lx.add_surface("Pit_Saja", pit_pts, pit_tris, "Permukaan pit di bawah topografi")
    lx.write(os.path.join(out, "pit.xml"))

    d = cx.DXF()
    for lev, seg in cx.contours(eg_pts, eg_tris, 5.0):
        d.poly2d(seg, "C-TOPO-MAJR" if abs(lev % 25) < 1e-6 else "C-TOPO-MINR", elevation=lev)
    for z, r in crest_runs:
        d.poly2d(r[:, :2], "C-PIT-CRST", elevation=z)
    for z, r in toe_runs:
        d.poly2d(r[:, :2], "C-PIT-TOES", elevation=z)
    for r in ramp_runs:
        d.poly2d(r[:, :2], "C-PIT-RAMP")
    for z, r in shell_rings:
        d.poly2d(r, "C-PIT-SHEL", closed=True, elevation=z)
    for b in benches:
        p = np.array(b["toe"].exterior.coords)
        k = int(np.argmax(p[:, 1]))
        if b["z"] <= float(topo.z(p[k, 0], p[k, 1])[0]):
            d.text(f"{b['z']:.0f}", p[k], 2.5, "C-ANNO-TEXT", z=b["z"])
    secs = _penampang_garis(cfg, benches)
    for name, a, bpt in secs:
        d.line((*a, 0), (*bpt, 0), "C-PIT-XSEC")
        d.text(name, a, 4, "C-PIT-XSEC")
    d.save(os.path.join(out, "pit_plan.dxf"))

    d3 = cx.DXF()
    for _, r in crest_runs:
        d3.poly3d(r, "C-PIT-CRST")
    for _, r in toe_runs:
        d3.poly3d(r, "C-PIT-TOES")
    for r in ramp_runs:
        d3.poly3d(r, "C-PIT-RAMP")
    sub_t = pit_tris if len(pit_tris) else fin_tris
    sub_p = pit_pts if len(pit_tris) else fin_pts
    d3.faces(sub_p, sub_t, "C-TINN-FG")
    d3.save(os.path.join(out, "pit_3d.dxf"))
    org = np.array([x0, y0, 0.0])
    cx.write_obj(os.path.join(out, "pit_final.obj"), fin_pts, fin_tris, "pit_final", org)
    cx.write_stl(os.path.join(out, "pit_final.stl"), fin_pts, fin_tris, "pit_final", org)
    if len(pit_tris):
        cx.write_obj(os.path.join(out, "pit_saja.obj"), pit_pts, pit_tris, "pit", org)

    with open(os.path.join(out, "block_model_hasil.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["x", "y", "z", "kadar", "densitas", "tonase", "nilai", "bijih", "pit_optimasi", "pit_desain"])
        for r in zip(bm["x"], bm["y"], bm["z"], bm["kadar"], bm["densitas"], ton, val, ore, mined, in_design):
            w.writerow([f"{r[0]:.2f}", f"{r[1]:.2f}", f"{r[2]:.2f}", f"{r[3]:.4f}", f"{r[4]:.3f}", f"{r[5]:.1f}", f"{r[6]:.1f}", int(r[7]), int(r[8]), int(r[9])])

    sec_data = []
    for name, a, bpt in secs:
        sec_data.append(_potong(name, a, bpt, benches, topo, bm, dims, mined, in_design, ore, sudut_muka))
    _dxf_penampang(sec_data, os.path.join(out, "pit_penampang.dxf"))

    import sheets_pit
    sheets_pit.render(cfg, summary, benches, crest_runs, toe_runs, ramp_runs, shell_rings, eg_pts, eg_tris, fin_pts, fin_tris,
                      sec_data, ev, bm, ton, ore, in_design, os.path.join(out, "lembar_gambar.pdf"), out, H)
    with open(os.path.join(out, "laporan.json"), "w") as f:
        json.dump(summary, f, indent=2, default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o))
    _laporan_md(cfg, summary, os.path.join(out, "laporan.md"))
    return summary


def _berm_min(cfg, H):
    """Lebar berm minimum praktik (Ritchie / modifikasi Call): 0,2 x H + 4,5 m, dibulatkan."""
    return math.floor(0.2 * H + 4.5)


def _tonase(bm, ton, ore, in_design, mined, val):
    def agg(mask):
        t_ore = float(ton[mask & ore].sum())
        t_w = float(ton[mask & ~ore].sum())
        g = float((bm["kadar"][mask & ore] * ton[mask & ore]).sum() / t_ore) if t_ore > 0 else 0.0
        return dict(bijih_ton=t_ore, kadar_rata=g, waste_ton=t_w, nisbah_kupas=t_w / t_ore if t_ore else None,
                    nilai=float(val[mask].sum()))
    return dict(desain=agg(in_design), optimasi=agg(mined))


def _penampang_garis(cfg, benches):
    if cfg["penampang"]:
        return [(s["nama"], tuple(s["a"]), tuple(s["b"])) for s in cfg["penampang"]]
    C = benches[-1]["crest"]
    c = benches[0]["toe"].centroid
    x0, y0, x1, y1 = C.bounds
    pad = 40
    return [("A-A'", (x0 - pad, c.y), (x1 + pad, c.y)), ("B-B'", (c.x, y0 - pad), (c.x, y1 + pad))]


def _potong(name, a, b, benches, topo, bm, dims, mined, in_design, ore, sudut_muka):
    a, b = np.array(a, float), np.array(b, float)
    L = np.linalg.norm(b - a)
    u = (b - a) / L
    s = np.linspace(0, L, int(L / 1.0))
    P = a[None, :] + s[:, None] * u[None, :]
    zt = topo.z(P[:, 0], P[:, 1])
    zd = z_desain(benches, P[:, 0], P[:, 1], sudut_muka, topo)
    dx = dims[0]
    rel = np.column_stack([bm["x"] - a[0], bm["y"] - a[1]])
    along = rel @ u
    perp = np.abs(rel @ np.array([-u[1], u[0]]))
    sel = (perp <= dx / 2) & (along >= 0) & (along <= L)
    blocks = dict(s=along[sel], z=bm["z"][sel], kadar=bm["kadar"][sel], mined=mined[sel], desain=in_design[sel], bijih=ore[sel])
    return dict(nama=name, a=a, b=b, s=s, zt=zt, zd=zd, blocks=blocks, dims=dims)


def _dxf_penampang(secs, path):
    d = cx.DXF({"C-SECT-EG": (8, "DASHED", "Topografi"), "C-SECT-FG": (1, "CONTINUOUS", "Desain pit"),
                "C-SECT-BLK": (5, "CONTINUOUS", "Blok bijih"), "C-SECT-TEXT": (7, "CONTINUOUS", "Label")})
    oy = 0.0
    for sd in secs:
        zmin = float(min(sd["zd"].min(), sd["blocks"]["z"].min() if len(sd["blocks"]["z"]) else sd["zd"].min())) - 20
        d.poly2d(np.column_stack([sd["s"], sd["zt"] - zmin + oy]), "C-SECT-EG")
        d.poly2d(np.column_stack([sd["s"], sd["zd"] - zmin + oy]), "C-SECT-FG")
        bl = sd["blocks"]
        dx, _, dz = sd["dims"]
        for s_, z_, o_ in zip(bl["s"], bl["z"], bl["bijih"]):
            if o_:
                d.poly2d([(s_ - dx / 2, z_ - dz / 2 - zmin + oy), (s_ + dx / 2, z_ - dz / 2 - zmin + oy),
                          (s_ + dx / 2, z_ + dz / 2 - zmin + oy), (s_ - dx / 2, z_ + dz / 2 - zmin + oy)], "C-SECT-BLK", closed=True)
        for z in np.arange(math.ceil(zmin / 10) * 10, sd["zt"].max() + 10, 10):
            d.line((0, z - zmin + oy, 0), (sd["s"][-1], z - zmin + oy, 0), "C-SECT-TEXT")
            d.text(f"{z:.0f}", (-8, z - zmin + oy), 2.5, "C-SECT-TEXT")
        d.text(f"PENAMPANG {sd['nama']}", (sd["s"][-1] / 2, sd["zt"].max() - zmin + oy + 15), 5, "C-SECT-TEXT")
        oy += float(sd["zt"].max() - zmin) + 60
    d.save(path)


def _laporan_md(cfg, s, path):
    g = s["geometri"]
    c = s["cadangan"]["desain"]
    o = s["cadangan"]["optimasi"]
    L = [f"# Laporan Desain Pit - {cfg['proyek']}", "",
         "Dasar: Kepmen ESDM 1827 K/30/MEM/2018 (Tabel 1 FK/PoF hal. 57; tambang permukaan hal. 84, 91-94; jalan hal. 99-100).", "",
         "## Geometri lereng & pit", "",
         f"- Tinggi jenjang {g['tinggi_jenjang']:.1f} m, sudut muka {g['sudut_muka']:.0f} deg, lebar berm {g['lebar_berm']:.1f} m",
         f"- Sudut inter-ramp {g['sudut_inter_ramp']:.1f} deg; sudut keseluruhan {g['sudut_keseluruhan']:.1f} deg (optimasi pit memakai {g['sudut_optimasi_pit']:.1f} deg untuk kelonggaran ramp)",
         f"- Ramp {g['lebar_ramp']:.2f} m, grade {g['grade_ramp'] * 100:.1f}%; dasar pit EL {g['dasar_pit']:.1f}; tinggi dinding maks {g['tinggi_dinding_maks']:.1f} m; {g['jumlah_jenjang']} jenjang",
         "", "## Tonase", "", "| | Bijih (t) | Kadar rata | Waste (t) | Nisbah kupas | Nilai |", "|---|---|---|---|---|---|",
         f"| Pit optimasi | {o['bijih_ton']:,.0f} | {o['kadar_rata']:.3f} | {o['waste_ton']:,.0f} | {o['nisbah_kupas'] or 0:.2f} | {o['nilai']:,.0f} |",
         f"| Pit desain | {c['bijih_ton']:,.0f} | {c['kadar_rata']:.3f} | {c['waste_ton']:,.0f} | {c['nisbah_kupas'] or 0:.2f} | {c['nilai']:,.0f} |",
         f"", f"Cut-off kadar: {s['cutoff']:.3f} {cfg['ekonomi']['satuan_kadar']}. Volume galian (TIN): {s['volume_galian_tin_m3']:,.0f} m3.",
         "", "## Pemeriksaan kepatuhan", "", "| No | Item | Nilai | Syarat | Status | Dasar |", "|---|---|---|---|---|---|"]
    for i, ch in enumerate(s["pemeriksaan"], 1):
        L.append(f"| {i} | {ch['item']} | {ch['nilai']} | {ch['syarat']} | {ch['status']} | {ch['dasar']} |")
    if s.get("optimasi_geoteknik"):
        L += ["", "## Iterasi optimasi geometri lereng", "", "| Sudut muka | Berm (m) | Sudut keseluruhan | FK keseluruhan | PoF | Lolos |", "|---|---|---|---|---|---|"]
        for t in s["optimasi_geoteknik"]:
            L.append(f"| {t['sudut_muka']} | {t['lebar_berm']} | {t['sudut_keseluruhan']:.1f} | {t['fk_keseluruhan']:.2f} | {t['pof_keseluruhan'] * 100:.1f}% | {'ya' if t['lolos'] else 'tidak'} |")
    L += ["", "## Catatan", "",
          "- Pit akhir dihitung dengan min-cut (setara Lerchs-Grossmann) pada block model; untuk model besar/produksi gunakan MineFlow (pseudoflow) atau Whittle/Deswik.",
          "- Ramp dimodelkan sebagai pita spiral yang memotong muka jenjang; geometri tikungan switchback & sambungan ke jalan luar dirapikan di CAD (Civil 3D/Surpac/Minescape).",
          "- FK memakai Bishop disederhanakan + lapisan horizontal; PoF Monte Carlo. Verifikasi dengan Slide2/RS2, data uji lab, kinematik (planar/baji/toppling), dan muka air tanah aktual. Rekomendasi geoteknik wajib disahkan KTT.",
          "- Impor `pit.xml` ke Civil 3D (Insert > LandXML) untuk surface EG/desain; DXF crest/toe berelevasi bisa dipakai langsung sebagai breakline."]
    with open(path, "w") as f:
        f.write("\n".join(L) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--out", default="hasil_pit")
    ap.add_argument("--cepat", action="store_true", help="kurangi sampel Monte Carlo (uji cepat)")
    a = ap.parse_args(argv)
    cfg = load_config(a.config, DEMO_CFG if a.demo and not a.config else None)
    if a.cepat:
        cfg["geoteknik"]["n_monte_carlo"] = 150
    s = run(cfg, a.out)
    print(json.dumps(dict(geometri=s["geometri"], cadangan=s["cadangan"], lolos_semua=s["lolos_semua"]), indent=2, default=float))
    for c in s["pemeriksaan"]:
        print(f"[{c['status']}] {c['item']}: {c['nilai']} ({c['syarat']})")


if __name__ == "__main__":
    main()
