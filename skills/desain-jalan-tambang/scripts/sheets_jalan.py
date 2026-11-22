"""Paket gambar perencanaan jalan tambang (gaya Civil 3D plan production) dengan tata letak berparameter.

Urutan lembar (sama seperti paket gambar perencanaan jalan pada umumnya):
  1. Peta situasi / overview trase + indeks lembar
  2..n Plan & profile (panjang tiap lembar dihitung dari ukuran kertas dan skala horizontal)
  n+1 Penampang tipikal ("PENAMPANG JALAN")
  ... Penampang melintang (Material(s) at Station + data elevasi/offset)
  ... Total Volume Table
Setiap lembar memiliki informasi tepi: kop perusahaan, judul, peta indeks, legenda, sistem koordinat, skala numerik
& grafis, sumber data, catatan kriteria Kepmen ESDM 1827 K/30/MEM/2018, kolom pengesahan (KTT), nomor gambar.
Semua ukuran dalam milimeter kertas; skala dihormati persis (1 mm kertas = skala/1000 m).
"""
from __future__ import annotations

import datetime as _dt
import math
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Polygon as MPoly, Rectangle  # noqa: E402
from matplotlib.transforms import Affine2D  # noqa: E402

import cad_export as cx  # noqa: E402

KERTAS = {"A0": (1189, 841), "A1": (841, 594), "A2": (594, 420), "A3": (420, 297), "A4": (297, 210)}
SKALA_STANDAR = [50, 100, 200, 250, 400, 500, 1000, 1250, 2000, 2500, 5000, 10000, 25000, 50000]

INK = "#111111"
GRID = "#c9ced1"
EGC = "#c0392b"      # tanah asli
FGC = "#1f4e9c"      # desain
CUTC = "#e0322b"     # galian
FILLC = "#22b14c"    # timbunan
CLC = "#c0392b"
DTC = "#2f6fb0"
BERMC = "#5b3a1e"
DAYC = "#1e8f3a"
SAMPLE = "#f0a35e"
BAND = "#c46a2c"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 6, "axes.edgecolor": INK, "axes.linewidth": 0.5,
                     "hatch.linewidth": 0.4})


# ============================================================================ util
def _skala_pas(perlu_m, tersedia_mm, minimal):
    """Skala standar paling detail (>= minimal) yang memuat 'perlu_m' meter dalam 'tersedia_mm' mm kertas."""
    for s in SKALA_STANDAR:
        if s >= minimal and tersedia_mm * s / 1000.0 >= perlu_m:
            return s
    return SKALA_STANDAR[-1]


def _interval_grid(skala):
    return {500: 25, 1000: 50, 2000: 100, 2500: 100, 5000: 250, 10000: 500, 25000: 1000}.get(skala, max(10, int(round(skala / 20, -1))))


def _interval_kontur(skala):
    return (0.5, 2.5) if skala <= 1000 else (1.0, 5.0) if skala <= 2500 else (2.0, 10.0) if skala <= 5000 else (5.0, 25.0)


def _fsk(s):
    return f"{s:,}".replace(",", ".")


class Sheet:
    """Satu lembar kertas: bingkai, kolom informasi tepi kanan, helper mm -> koordinat figur."""

    def __init__(self, cfg, judul, no, total_ref, kertas):
        self.cfg = cfg
        self.W, self.H = KERTAS.get(kertas, KERTAS["A3"])
        self.fig = plt.figure(figsize=(self.W / 25.4, self.H / 25.4))
        self.info_w = max(88.0, 0.215 * self.W)
        self.left, self.right, self.bottom, self.top = 20.0, 10.0, 10.0, 10.0
        self.dx0 = self.left + 2
        self.dx1 = self.W - self.right - self.info_w - 2
        self.dy0 = self.bottom + 2
        self.dy1 = self.H - self.top - 2
        self.judul, self.no, self.total_ref = judul, no, total_ref
        f = self.fig
        f.patches.append(Rectangle((self.left / self.W, self.bottom / self.H), (self.W - self.left - self.right) / self.W,
                                   (self.H - self.top - self.bottom) / self.H, transform=f.transFigure, fill=False, lw=1.2, ec=INK))
        xi = (self.W - self.right - self.info_w) / self.W
        f.lines.append(Line2D([xi, xi], [self.bottom / self.H, 1 - self.top / self.H], transform=f.transFigure, lw=1.0, c=INK))

    def ax(self, x, y, w, h, **kw):
        return self.fig.add_axes([x / self.W, y / self.H, w / self.W, h / self.H], **kw)

    @property
    def draw_w(self):
        return self.dx1 - self.dx0

    @property
    def draw_h(self):
        return self.dy1 - self.dy0


def _box_axes(sh, y, h):
    x = sh.W - sh.right - sh.info_w
    a = sh.ax(x, y, sh.info_w, h)
    a.set_xlim(0, sh.info_w); a.set_ylim(0, h); a.axis("off")
    a.add_patch(Rectangle((0, 0), sh.info_w, h, fill=False, lw=0.7, ec=INK))
    return a


def info_tepi(sh, ctx, legenda, skala_txt, indeks_fn=None, catatan=None):
    """Kolom informasi tepi kanan: kop, judul, peta indeks, legenda, info teknis + skala + utara,
    catatan Kepmen, pengesahan (KTT), nomor gambar/lembar/revisi."""
    cfg, lb = sh.cfg, sh.cfg["lembar"]
    w = sh.info_w
    y = sh.H - sh.top
    h = 26; y -= h
    a = _box_axes(sh, y, h)
    tx = 3
    if lb.get("logo") and os.path.exists(lb["logo"]):
        img = plt.imread(lb["logo"])
        ai = sh.ax(sh.W - sh.right - sh.info_w + 2, y + 3, 20, 20); ai.imshow(img); ai.axis("off")
        tx = 25
    a.text(tx, h - 6, (cfg.get("perusahaan") or "NAMA PERUSAHAAN").upper(), fontsize=8, weight="bold", va="center")
    a.text(tx, h - 12, f"IUP: {lb.get('nomor_iup') or '-'}", fontsize=5.8, va="center")
    a.text(tx, h - 17, f"Lokasi: {lb.get('lokasi') or '-'}", fontsize=5.8, va="center")
    a.text(tx, h - 22, cfg["proyek"], fontsize=5.6, va="center", style="italic")
    h = 16; y -= h
    a = _box_axes(sh, y, h)
    a.text(3, h - 4.5, "JUDUL GAMBAR", fontsize=4.8, color="#555", va="center")
    a.text(3, h - 10.5, sh.judul, fontsize=7 if len(sh.judul) < 42 else 6, weight="bold", va="center")
    h = 50; y -= h
    a = _box_axes(sh, y, h)
    a.text(3, h - 4, "PETA INDEKS / LOKASI", fontsize=4.8, color="#555", va="center")
    if indeks_fn:
        ai = sh.ax(sh.W - sh.right - sh.info_w + 3, y + 3, w - 6, h - 9)
        indeks_fn(ai)
    h = 6.5 + 4.0 * len(legenda); y -= h
    a = _box_axes(sh, y, h)
    a.text(3, h - 4, "LEGENDA", fontsize=4.8, color="#555", va="center")
    for i, (kind, sty, lab) in enumerate(legenda):
        yy = h - 8.5 - 4.0 * i
        if kind == "line":
            a.plot([4, 16], [yy, yy], **sty)
        elif kind == "patch":
            a.add_patch(Rectangle((4, yy - 1.3), 12, 2.6, **sty))
        elif kind == "marker":
            a.plot([10], [yy], **sty)
        a.text(19, yy, lab, fontsize=5.2, va="center")
    h = 33; y -= h
    a = _box_axes(sh, y, h)
    a.text(3, h - 4, "INFORMASI TEKNIS", fontsize=4.8, color="#555", va="center")
    u = cfg["unit_terbesar"]
    rows = [f"Koordinat : {lb['sistem_koordinat']}", f"Topografi : {lb['sumber_topografi']}",
            f"V rencana : {cfg['kecepatan_rencana_kmh']:.0f} km/jam | {cfg['jumlah_jalur']} jalur",
            f"Unit      : {u['nama']} (lebar {u['lebar_m']} m, D roda {u['diameter_roda_m']} m)"]
    for i, r in enumerate(rows):
        a.text(3, h - 8.5 - 3.4 * i, r, fontsize=4.6, va="center", family="DejaVu Sans Mono")
    a.text(3, 9.3, skala_txt, fontsize=6.3, weight="bold", va="center")
    if ctx.get("skala_batang"):
        _skala_batang(a, 3, 3.0, ctx["skala_batang"], w - 32)
    _panah_utara(a, w - 9, 11, 8, ctx.get("rotasi_utara", 0.0))
    if catatan:
        h = 6.5 + 3.3 * len(catatan); y -= h
        a = _box_axes(sh, y, h)
        a.text(3, h - 4, "CATATAN KRITERIA (Kepmen ESDM 1827 K/30/MEM/2018)", fontsize=4.6, color="#555", va="center")
        for i, c in enumerate(catatan):
            a.text(3, h - 8.3 - 3.3 * i, c, fontsize=4.5, va="center")
    peng = lb.get("pengesahan") or []
    h = 25; y -= h
    a = _box_axes(sh, y, h)
    n = max(1, len(peng))
    cw = w / n
    for i, (jab, nama) in enumerate(peng):
        x0 = i * cw
        if i:
            a.plot([x0, x0], [0, h], lw=0.5, c=INK)
        a.text(x0 + cw / 2, h - 3.6, jab, fontsize=4.9, ha="center", va="center", weight="bold")
        a.plot([x0 + 3, x0 + cw - 3], [8.2, 8.2], lw=0.4, c="#777")
        a.text(x0 + cw / 2, 5.8, nama or "( .................. )", fontsize=4.5, ha="center", va="center")
        a.text(x0 + cw / 2, 2.2, "Tgl: ..........", fontsize=4.2, ha="center", va="center", color="#555")
    a.plot([0, w], [h - 7, h - 7], lw=0.5, c=INK)
    h = y - sh.bottom; y = sh.bottom
    a = _box_axes(sh, y, h)
    a.plot([w * 0.52, w * 0.52], [0, h], lw=0.5, c=INK)
    a.text(3, h * 0.74, "NO. GAMBAR", fontsize=4.6, color="#555", va="center")
    a.text(3, h * 0.32, f"{lb['nomor_gambar']}-{sh.no:02d}", fontsize=8.5, weight="bold", va="center")
    a.text(w * 0.52 + 3, h * 0.74, f"LEMBAR {sh.no} / {sh.total_ref[0]}", fontsize=6, va="center", weight="bold")
    a.text(w * 0.52 + 3, h * 0.32, f"Rev {lb['revisi']} | {_dt.date.today():%d-%m-%Y}", fontsize=5.2, va="center")


def _skala_batang(a, x, y, m_per_mm, panjang_mm):
    tot_m = panjang_mm * m_per_mm
    step = [1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 5000]
    seg_m = next((s for s in step if s * 4 >= tot_m * 0.6), step[-1])
    seg_mm = seg_m / m_per_mm
    for i in range(4):
        a.add_patch(Rectangle((x + i * seg_mm, y), seg_mm, 1.5, fc=INK if i % 2 == 0 else "white", ec=INK, lw=0.4))
        a.text(x + i * seg_mm, y + 3.0, f"{i * seg_m:g}", fontsize=4.1, ha="center", va="center")
    a.text(x + 4 * seg_mm, y + 3.0, f"{4 * seg_m:g} m", fontsize=4.1, ha="center", va="center")


def _panah_utara(a, x, y, size, rot_deg):
    t = math.radians(rot_deg)
    R = np.array([[math.cos(t), -math.sin(t)], [math.sin(t), math.cos(t)]])
    pts = np.array([[0, size / 2], [-size / 5, -size / 2], [0, -size / 4], [size / 5, -size / 2]]) @ R.T + [x, y]
    a.add_patch(MPoly(pts, closed=True, fc=INK, ec=INK, lw=0.4, zorder=9))
    q = np.array([0, size / 2 + size * 0.28]) @ R.T + [x, y]
    a.text(q[0], q[1], "U", fontsize=6, ha="center", va="center", weight="bold", zorder=9)


def _catatan_kepmen(cfg, s):
    g = s["geometri"]
    kr = cfg["_kriteria"]
    k = kr["lebar_jalan_dua_jalur_min_x_lebar_unit"] if cfg["jumlah_jalur"] >= 2 else kr["lebar_jalan_satu_jalur_min_x_lebar_unit"]
    return [f"Lebar jalur {g['W_lurus']:.2f} m >= {k:g} x lebar unit (hal. 99 i)",
            f"Tanggul {s['tanggul_tinggi_m']:.2f} m >= 3/4 diameter roda (hal. 99 ii)",
            f"Cross fall {max(cfg['kemiringan_melintang'], 0.02) * 100:.1f}% >= 2% (hal. 99 vi)",
            f"Grade maks {s['grade_maks_pct']:.2f}% <= 12% (hal. 99 vii)",
            "Tikungan: R, e, pelebaran sesuai V rencana (hal. 100 ix)",
            "Satuan meter; elevasi terhadap datum topografi"]


# ============================================================================ geometri bantu
class _Rot:
    """Rotasi tampilan plan agar segmen trase mendatar (seperti viewport Civil 3D)."""

    def __init__(self, theta, c):
        self.theta, self.c = theta, np.asarray(c, float)
        self.ct, self.st = math.cos(-theta), math.sin(-theta)

    def f(self, xy):
        xy = np.asarray(xy, float)
        d = xy[..., :2] - self.c
        return np.stack([d[..., 0] * self.ct - d[..., 1] * self.st, d[..., 0] * self.st + d[..., 1] * self.ct], axis=-1)


def _clip_line_box(p, q, box):
    from shapely.geometry import LineString, box as sbox
    g = LineString([p, q]).intersection(sbox(*box))
    if g.is_empty or g.geom_type != "LineString":
        return None
    return np.array(g.coords)


def _grid_utm(ax, rot, box, interval):
    x0, y0, x1, y1 = box
    c = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])
    ct, st = math.cos(rot.theta), math.sin(rot.theta)
    w = np.stack([c[:, 0] * ct - c[:, 1] * st, c[:, 0] * st + c[:, 1] * ct], axis=1) + rot.c
    E0, E1 = math.floor(w[:, 0].min() / interval) * interval, math.ceil(w[:, 0].max() / interval) * interval
    N0, N1 = math.floor(w[:, 1].min() / interval) * interval, math.ceil(w[:, 1].max() / interval) * interval
    for E in np.arange(E0, E1 + interval / 2, interval):
        seg = _clip_line_box(*rot.f(np.array([[E, N0 - interval], [E, N1 + interval]])), box)
        if seg is not None:
            ax.plot(seg[:, 0], seg[:, 1], c=GRID, lw=0.35, zorder=1)
            p = seg[np.argmin(seg[:, 1])]
            ax.text(p[0], p[1], f"E {E:,.0f}".replace(",", "."), fontsize=4.1, color="#4a5357", ha="left", va="bottom", rotation=90, zorder=6, clip_on=True)
    for N in np.arange(N0, N1 + interval / 2, interval):
        seg = _clip_line_box(*rot.f(np.array([[E0 - interval, N], [E1 + interval, N]])), box)
        if seg is not None:
            ax.plot(seg[:, 0], seg[:, 1], c=GRID, lw=0.35, zorder=1)
            p = seg[np.argmin(seg[:, 0])]
            ax.text(p[0], p[1], f"N {N:,.0f}".replace(",", "."), fontsize=4.1, color="#4a5357", ha="left", va="bottom", zorder=6, clip_on=True)


def _ortofoto(ax, cfg, rot=None):
    """Latar foto udara/ortofoto. lembar.ortofoto = {"path": "...jpg/png/tif", "extent": [xmin, ymin, xmax, ymax]}
    atau world file (.jgw/.pgw/.tfw) di samping gambar."""
    o = cfg["lembar"].get("ortofoto")
    if not o or not os.path.exists(o.get("path", "")):
        return False
    img = plt.imread(o["path"])
    ext = o.get("extent")
    if ext:
        ext = [ext[0], ext[2], ext[1], ext[3]]
    else:
        base, e = os.path.splitext(o["path"])
        wf = base + {".jpg": ".jgw", ".jpeg": ".jgw", ".png": ".pgw", ".tif": ".tfw", ".tiff": ".tfw"}.get(e.lower(), ".wld")
        if not os.path.exists(wf):
            return False
        A, D, B, E, C, F = [float(v) for v in open(wf).read().split()[:6]]
        hh, ww = img.shape[:2]
        ext = [C - A / 2, C + A * (ww - 0.5), F + E * (hh - 0.5), F - E / 2]
    tr = ax.transData
    if rot is not None:
        tr = Affine2D().translate(-rot.c[0], -rot.c[1]).rotate(-rot.theta) + ax.transData
    ax.imshow(img, extent=ext, transform=tr, zorder=0, interpolation="bilinear")
    return True


def _frame_plan_world(al, a0, b0, sh0, sk_h, prof_frac, band_h):
    pa, pb = al.at(a0)[0], al.at(b0)[0]
    theta = math.atan2(pb[1] - pa[1], pb[0] - pa[0])
    mid = np.array([al.at(v)[0] for v in np.linspace(a0, b0, 30)]).mean(axis=0)
    plan_h = sh0.draw_h - sh0.draw_h * prof_frac - band_h - 6
    hw, hh = sh0.draw_w * sk_h / 2000, plan_h * sk_h / 2000
    c = np.array([[-hw, -hh], [hw, -hh], [hw, hh], [-hw, hh]])
    ct, st = math.cos(theta), math.sin(theta)
    return np.stack([c[:, 0] * ct - c[:, 1] * st, c[:, 0] * st + c[:, 1] * ct], axis=1) + mid


# ============================================================================ render utama
def render(cfg, al, prof, eg_prof, xs, vol_rows, tabel_vol, s, eg_pts, eg_tris, cp_pts, cp_tris, cpts, ctris, terrain,
           pdf_path, out_dir):
    from haul_road import _feature_lines

    lb = cfg["lembar"]
    kertas = lb["kertas"]
    sh0 = Sheet(cfg, "", 0, [0], kertas); plt.close(sh0.fig)
    lab_w = 34.0
    prof_frac = 0.34
    band_h = 3 * 6.5
    sk_h = lb["skala_horizontal"]
    L_m = (sh0.draw_w - lab_w) * sk_h / 1000.0
    step = L_m - lb["overlap_m"]
    chunks = []
    a = al.sta0
    while a < al.sta_end - 1e-6:
        b = min(a + L_m, al.sta_end)
        chunks.append((a, b))
        if b >= al.sta_end - 1e-6:
            break
        a += step
    xs_lembar = [xs[r["idx"]] for r in tabel_vol]
    per = lb["penampang_per_lembar"]
    n_xs_sheets = math.ceil(len(xs_lembar) / per)
    rows_per_tab, tabs_per_sheet = 22, 6
    n_tab = math.ceil(len(tabel_vol) / rows_per_tab)
    n_vol_sheets = math.ceil(n_tab / tabs_per_sheet)
    total_ref = [1 + len(chunks) + 1 + n_xs_sheets + n_vol_sheets]
    feats = _feature_lines(xs)
    minor, major = _interval_kontur(sk_h)
    kontur = cx.contours(eg_pts, eg_tris, minor)
    sheets, daftar = [], []
    full_cl = np.array([al.at(v)[0] for v in np.arange(al.sta0, al.sta_end, max(1.0, al.length / 400))] + [al.at(al.sta_end)[0]])

    def legend_plan():
        return [("line", dict(c=CLC, lw=0.8, ls=(0, (8, 2, 2, 2))), "Garis tengah (CL) & stasiun"),
                ("line", dict(c=INK, lw=0.9), "Tepi jalur lalu lintas"),
                ("line", dict(c=DTC, lw=0.6, ls="--"), "Saluran drainase"),
                ("line", dict(c=BERMC, lw=0.8), "Tanggul pengaman"),
                ("line", dict(c=DAYC, lw=0.6), "Batas galian/timbunan (daylight)"),
                ("line", dict(c=SAMPLE, lw=0.5), "Garis penampang"),
                ("line", dict(c="#7d8a90", lw=0.4), f"Kontur EG {minor:g} m / {major:g} m"),
                ("line", dict(c=EGC, lw=0.7), "Profil tanah asli (EG)"),
                ("line", dict(c=FGC, lw=1.0, ls=(0, (6, 2))), "Profil desain (FG)"),
                ("patch", dict(fc=CUTC, alpha=0.75, ec="none"), "Galian"),
                ("patch", dict(fc=FILLC, alpha=0.75, ec="none"), "Timbunan")]

    def indeks(highlight=None):
        def f(ax):
            ax.plot(full_cl[:, 0], full_cl[:, 1], c=CLC, lw=0.8)
            if highlight is not None:
                hh = np.array([al.at(v)[0] for v in np.linspace(highlight[0], highlight[1], 40)])
                ax.plot(hh[:, 0], hh[:, 1], c="#f2b400", lw=3.2, alpha=0.9, solid_capstyle="butt")
            ax.plot(*full_cl[0], "o", ms=2.5, c=INK); ax.plot(*full_cl[-1], "s", ms=2.5, c=INK)
            ax.text(*full_cl[0], " Awal", fontsize=4.5); ax.text(*full_cl[-1], " Akhir", fontsize=4.5)
            ax.set_aspect("equal", adjustable="datalim"); ax.set_xticks([]); ax.set_yticks([])
            for sp in ax.spines.values():
                sp.set_lw(0.3)
        return f

    def finish(sh, judul):
        daftar.append(dict(no=sh.no, nomor=f"{lb['nomor_gambar']}-{sh.no:02d}", judul=judul))
        sheets.append(sh)

    cat = _catatan_kepmen(cfg, s)

    # ================================================================ 1. PETA SITUASI
    sh = Sheet(cfg, "PETA SITUASI TRASE & INDEKS LEMBAR", 1, total_ref, kertas)
    pad = 60
    bx = (full_cl[:, 0].min() - pad, full_cl[:, 1].min() - pad, full_cl[:, 0].max() + pad, full_cl[:, 1].max() + pad)
    sk_o = next((sk for sk in SKALA_STANDAR if sk >= 1000 and (bx[2] - bx[0]) <= sh.draw_w * sk / 1000
                 and (bx[3] - bx[1]) <= sh.draw_h * sk / 1000), SKALA_STANDAR[-1])
    ax = sh.ax(sh.dx0, sh.dy0, sh.draw_w, sh.draw_h)
    cxm, cym = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
    hw_, hh_ = sh.draw_w * sk_o / 2000, sh.draw_h * sk_o / 2000
    ax.set_xlim(cxm - hw_, cxm + hw_); ax.set_ylim(cym - hh_, cym + hh_)
    _ortofoto(ax, cfg)
    mi_o, ma_o = _interval_kontur(sk_o)
    for lev, seg in cx.contours(eg_pts, eg_tris, ma_o):
        ax.plot(seg[:, 0], seg[:, 1], c="#9aa5aa", lw=0.3, zorder=1)
    _grid_utm(ax, _Rot(0.0, np.zeros(2)), (cxm - hw_, cym - hh_, cxm + hw_, cym + hh_), _interval_grid(sk_o))
    for name, runs in feats.items():
        if name.startswith("DAYL"):
            for r in runs:
                r = np.array(r); ax.plot(r[:, 0], r[:, 1], c=DAYC, lw=0.4, zorder=3)
    ax.plot(full_cl[:, 0], full_cl[:, 1], c=CLC, lw=1.0, zorder=4)
    for v in np.arange(math.ceil(al.sta0 / 100) * 100, al.sta_end + 1e-6, 100):
        p = al.at(v)[0]
        ax.plot(*p, "o", ms=2.2, mfc=FILLC, mec=INK, mew=0.3, zorder=5)
        if abs(v % 500) < 1e-6:
            ax.text(p[0], p[1], f"  {cx.fmt_sta(v)}", fontsize=5.5, zorder=6, weight="bold")
    for k, (a0, b0) in enumerate(chunks):
        frame = _frame_plan_world(al, a0, b0, sh0, sk_h, prof_frac, band_h)
        ax.add_patch(MPoly(frame, closed=True, fill=False, ec="#f28c00", lw=0.8, ls="--", zorder=5))
        c0 = frame.mean(axis=0)
        ax.text(c0[0], c0[1], f"{lb['nomor_gambar']}-{k + 2:02d}", fontsize=5.5, color="#b35f00", ha="center", va="center", weight="bold", zorder=6)
    ax.text(full_cl[0, 0], full_cl[0, 1], f"  DESIGN SPEED = {cfg['kecepatan_rencana_kmh']:.0f} km/h\n  STA {cx.fmt_sta(al.sta0)}", fontsize=5.5, color=CLC, va="top", zorder=6)
    ax.set_xticks([]); ax.set_yticks([])
    ax.text(0.01, 0.99, f"PETA SITUASI TRASE {cfg['alinyemen'].get('nama', '')}  |  panjang {al.length:,.2f} m  |  SKALA 1:{_fsk(sk_o)}",
            transform=ax.transAxes, fontsize=7, weight="bold", va="top", bbox=dict(fc="white", ec="none", alpha=0.85, pad=1))
    info_tepi(sh, dict(skala_batang=sk_o / 1000), [("line", dict(c=CLC, lw=1), "Trase / garis tengah"),
                                                    ("marker", dict(marker="o", ms=3, mfc=FILLC, mec=INK, mew=0.3, ls=""), "Patok stasiun tiap 100 m"),
                                                    ("line", dict(c="#f28c00", lw=0.8, ls="--"), "Batas lembar plan & profile"),
                                                    ("line", dict(c=DAYC, lw=0.5), "Batas galian/timbunan"),
                                                    ("line", dict(c="#9aa5aa", lw=0.4), f"Kontur EG {ma_o:g} m")],
              f"SKALA 1 : {_fsk(sk_o)}", indeks(), cat)
    finish(sh, "Peta situasi trase & indeks lembar")

    # ================================================================ 2. PLAN & PROFILE
    for k, (a0, b0) in enumerate(chunks):
        no = k + 2
        sh = Sheet(cfg, f"PLAN & PROFILE STA {cx.fmt_sta(a0)} - {cx.fmt_sta(b0)}", no, total_ref, kertas)
        prof_h = sh.draw_h * prof_frac
        plan_h = sh.draw_h - prof_h - band_h - 6
        pa, pb = al.at(a0)[0], al.at(b0)[0]
        theta = math.atan2(pb[1] - pa[1], pb[0] - pa[0])
        mid = np.array([al.at(v)[0] for v in np.linspace(a0, b0, 30)]).mean(axis=0)
        rot = _Rot(theta, mid)
        axp = sh.ax(sh.dx0, sh.dy1 - plan_h, sh.draw_w, plan_h)
        hw_m, hh_m = sh.draw_w * sk_h / 2000, plan_h * sk_h / 2000
        box = (-hw_m, -hh_m, hw_m, hh_m)
        axp.set_xlim(box[0], box[2]); axp.set_ylim(box[1], box[3])
        _ortofoto(axp, cfg, rot)
        for lev, seg in kontur:
            r = rot.f(seg)
            if r[:, 0].max() < box[0] or r[:, 0].min() > box[2] or r[:, 1].max() < box[1] or r[:, 1].min() > box[3]:
                continue
            mj = abs(lev / major - round(lev / major)) < 1e-6
            axp.plot(r[:, 0], r[:, 1], c="#7d8a90" if mj else "#b8c1c5", lw=0.45 if mj else 0.25, zorder=1)
        _grid_utm(axp, rot, box, lb.get("interval_grid_m") or _interval_grid(sk_h))
        for x in xs:
            if a0 - 5 <= x["sta"] <= b0 + 5:
                r = rot.f(x["xyz"][[0, -1], :2])
                axp.plot(r[:, 0], r[:, 1], c=SAMPLE, lw=0.35, zorder=2)
        sty_map = {"ETW": dict(c=INK, lw=0.8), "DTCH_BI": dict(c=DTC, lw=0.45, ls="--"), "DTCH_BO": dict(c=DTC, lw=0.45, ls="--"),
                   "BERM_TO": dict(c=BERMC, lw=0.7), "BERM_TI": dict(c=BERMC, lw=0.5), "DAYL": dict(c=DAYC, lw=0.6),
                   "SHLD": dict(c="#555", lw=0.3)}
        for name, runs in feats.items():
            sty = sty_map.get(name.split("_L")[0].split("_R")[0])
            if not sty:
                continue
            for run in runs:
                r = rot.f(np.array(run)[:, :2])
                axp.plot(r[:, 0], r[:, 1], zorder=3, **sty)
        ss = np.arange(max(al.sta0, a0 - 60), min(al.sta_end, b0 + 60), 1.0)
        clr = rot.f(np.array([al.at(v)[0] for v in ss]))
        axp.plot(clr[:, 0], clr[:, 1], c=CLC, lw=0.8, ls=(0, (8, 2, 2, 2)), zorder=4)
        di = lb["interval_data_profil_m"]
        for v in np.arange(math.ceil(a0 / di) * di, b0 + 1e-6, di):
            p, t, _, _ = al.at(v)
            n = np.array([t[1], -t[0]])
            q = rot.f(np.array([p - n * 2.5, p + n * 2.5]))
            axp.plot(q[:, 0], q[:, 1], c=INK, lw=0.4, zorder=5)
        li = lb["interval_label_sta_m"]
        for v in np.arange(math.ceil(a0 / li) * li, b0 + 1e-6, li):
            p, t, _, _ = al.at(v)
            q = rot.f(p)
            ang = math.degrees(math.atan2(t[1], t[0])) - math.degrees(theta) + 90
            ang = (ang + 90) % 180 - 90
            axp.text(q[0], q[1], cx.fmt_sta(v), fontsize=6.2, color=CLC, rotation=ang, ha="center", va="center", zorder=7,
                     bbox=dict(fc="white", ec="#3c6fd1", lw=0.5, pad=0.6))
        for c in al.curves:
            e = c["elem"]
            if c["sta_pt"] >= a0 - 1 and c["sta_pc"] <= b0 + 1:
                for pt_, lab in ((e.start, "PC"), (e.end, "PT")):
                    q = rot.f(pt_)
                    axp.plot(*q, "o", ms=2, mfc="white", mec=INK, zorder=7)
                    axp.text(q[0], q[1], f" {lab}", fontsize=4.8, zorder=7)
                q = rot.f(e.pi)
                axp.plot(*q, "^", ms=2.6, c=INK, zorder=7)
                axp.text(q[0], q[1], f"  PI{c['pi_no']}  R={c['radius']:.0f}  D={c['delta_deg']:.2f} deg\n  L={c['L']:.2f}  e={c.get('e', 0) * 100:.1f}%  W={c.get('W', 0):.2f} m",
                         fontsize=4.8, zorder=7, va="bottom", bbox=dict(fc="white", ec="none", alpha=0.75, pad=0.4))
        if k == 0:
            q = rot.f(al.at(al.sta0)[0])
            axp.text(q[0], q[1] + 8 * sk_h / 1000, f"DESIGN SPEED = {cfg['kecepatan_rencana_kmh']:.0f} km/h\nSTA {cx.fmt_sta(al.sta0)}", fontsize=5.5, color=CLC, ha="left", va="bottom", zorder=7, clip_on=True)
        for v in (a0, b0):
            if al.sta0 + 1 < v < al.sta_end - 1:
                p, t, _, _ = al.at(v)
                n = np.array([t[1], -t[0]])
                q = rot.f(np.array([p - n * 45, p + n * 45]))
                axp.plot(q[:, 0], q[:, 1], c="#7a3fa0", lw=0.9, ls="-.", zorder=6)
                axp.text(q[1][0], q[1][1], f"MATCH LINE STA {cx.fmt_sta(v)}", fontsize=5, color="#7a3fa0", zorder=7, ha="center", va="bottom")
        axp.set_xticks([]); axp.set_yticks([])
        _panah_utara(axp, box[2] - 0.035 * (box[2] - box[0]), box[3] - 0.14 * (box[3] - box[1]), 0.08 * (box[3] - box[1]), -math.degrees(theta))
        axp.text(0.006, 0.985, f"PLAN  SKALA 1:{_fsk(sk_h)}", transform=axp.transAxes, fontsize=6.5, weight="bold", va="top",
                 bbox=dict(fc="white", ec="none", alpha=0.85, pad=0.5), zorder=8)
        # --- profil
        y_prof = sh.dy0 + band_h + 2
        axf = sh.ax(sh.dx0 + lab_w, y_prof, sh.draw_w - lab_w, prof_h)
        sf = np.arange(a0, b0 + 1e-6, 1.0)
        zf = prof.z(sf)
        se = np.array([p[0] for p in eg_prof]); ze_all = np.array([p[1] for p in eg_prof])
        ze = np.interp(sf, se, ze_all)
        lo, hi = min(zf.min(), ze.min()), max(zf.max(), ze.max())
        sv = _skala_pas((hi - lo) * 1.3 + 6, prof_h, lb["skala_vertikal"])
        span = prof_h * sv / 1000
        z0 = math.floor((lo - 0.1 * span) / 5) * 5
        axf.set_xlim(a0, a0 + L_m); axf.set_ylim(z0, z0 + span)
        axf.fill_between(sf, zf, ze, where=ze > zf, facecolor=CUTC, alpha=0.8, lw=0)
        axf.fill_between(sf, zf, ze, where=ze <= zf, facecolor=FILLC, alpha=0.8, lw=0)
        axf.plot(se, ze_all, c=EGC, lw=0.7)
        axf.plot(sf, zf, c=FGC, lw=1.0, ls=(0, (6, 2)))
        dz_lab = 5 if span <= 120 else 10 if span <= 300 else 25
        yt = np.arange(math.ceil(z0 / dz_lab) * dz_lab, z0 + span, dz_lab)
        axf.set_yticks(yt)
        axf.tick_params(axis="y", labelsize=4.6, length=2, pad=1)
        axf.tick_params(axis="x", length=0, labelbottom=False)
        for v in np.arange(math.ceil(a0 / di) * di, b0 + 1e-6, di):
            axf.axvline(v, c=GRID, lw=0.25, zorder=0)
        for zz in yt:
            axf.axhline(zz, c=GRID, lw=0.2, zorder=0)
        g = prof.grades()
        vang = sk_h / sv
        for i, (st, zz, Lv) in enumerate(prof.pvis):
            if a0 - 1e-6 <= st <= b0 + 1e-6:
                top = min(zz + 0.45 * span, z0 + span * 0.96)
                axf.plot([st, st], [zz, top], c=INK, lw=0.4)
                axf.plot(st, zz, "o", ms=2.2, mfc="white", mec=EGC, mew=0.6, zorder=5)
                txt = f"GRADE BREAK STA = {cx.fmt_sta(st)}\nELEV = {zz:.3f}" if not Lv else f"PVI STA = {cx.fmt_sta(st)}\nELEV = {zz:.3f}  L = {Lv:.0f} m"
                near0 = (st - a0) < L_m * 0.02
                axf.text(st + (L_m * 0.0025 if near0 else -L_m * 0.0025), top, txt, rotation=90, fontsize=4.3,
                         ha="left" if near0 else "right", va="top", linespacing=1.1)
                if Lv:
                    axf.plot([st - Lv / 2, st + Lv / 2], [prof.z(st - Lv / 2)[0], prof.z(st + Lv / 2)[0]], "|", c=INK, ms=5)
            if i < len(g):
                st2 = prof.pvis[i + 1][0]
                ma, mb = max(st, a0), min(st2, b0)
                if mb - ma > 0.1 * (b0 - a0):
                    xm = (ma + mb) / 2
                    axf.text(xm, float(prof.z(xm)[0]) + span * 0.035, f"{g[i] * 100:.2f}%", fontsize=6.8, ha="center", va="bottom",
                             rotation=math.degrees(math.atan(g[i] * vang)), color=CUTC if abs(g[i]) > cfg["_kriteria"]["grade_maks"] else INK)
        for c in al.curves:
            if c["sta_pt"] >= a0 and c["sta_pc"] <= b0:
                axf.axvspan(max(c["sta_pc"], a0), min(c["sta_pt"], b0), ymin=0, ymax=0.025, color="#3c6fd1", lw=0)
        axf.text(a0 + L_m * 0.004, z0 + span * 0.985, f"PROFILE  SKALA H 1:{_fsk(sk_h)}  V 1:{_fsk(sv)}", fontsize=6.5, weight="bold", va="top")
        axlab = sh.ax(sh.dx0, y_prof, lab_w, prof_h); axlab.axis("off")
        axlab.text(0.5, 0.5, "ELEVASI (m)", rotation=90, transform=axlab.transAxes, ha="center", va="center", fontsize=5.5)
        labels = lb["label_baris_profil"]
        axb = sh.ax(sh.dx0, sh.dy0, sh.draw_w, band_h)
        axb.set_xlim(0, sh.draw_w); axb.set_ylim(0, band_h); axb.axis("off")
        axb.add_patch(Rectangle((0, 0), sh.draw_w, band_h, fill=False, ec=BAND, lw=0.6))
        for r in (1, 2):
            axb.plot([0, sh.draw_w], [r * band_h / 3] * 2, c=BAND, lw=0.5)
        axb.plot([lab_w, lab_w], [0, band_h], c=BAND, lw=0.6)
        for r, lab in enumerate(labels):
            axb.text(1.5, band_h - (r + 0.5) * band_h / 3, lab, fontsize=4.8, va="center")
        mm_per_m = (sh.draw_w - lab_w) / L_m
        rot_txt = 90 if di * mm_per_m < 9.5 else 0
        for v in np.arange(math.ceil(a0 / di) * di, b0 + 1e-6, di):
            xmm = lab_w + (v - a0) * mm_per_m
            vals = [f"{float(np.interp(v, se, ze_all)):.2f}", f"{float(prof.z(v)[0]):.3f}", cx.fmt_sta(v)[:-3]]
            for r, tv in enumerate(vals):
                axb.text(xmm, band_h - (r + 0.5) * band_h / 3, tv, fontsize=4.1, ha="center", va="center", rotation=rot_txt)
            axb.plot([xmm, xmm], [band_h, band_h - 1.2], c=INK, lw=0.3)
        info_tepi(sh, dict(skala_batang=sk_h / 1000, rotasi_utara=-math.degrees(theta)), legend_plan(),
                  f"H 1:{_fsk(sk_h)}  |  V 1:{_fsk(sv)}", indeks((a0, b0)), cat)
        finish(sh, f"Plan & profile STA {cx.fmt_sta(a0)} - {cx.fmt_sta(b0)}")

    # ================================================================ 3. PENAMPANG TIPIKAL
    no = len(chunks) + 2
    sh = Sheet(cfg, "PENAMPANG JALAN (TIPIKAL)", no, total_ref, kertas)
    sk_t = _lembar_tipikal(sh, cfg, s)
    info_tepi(sh, dict(skala_batang=sk_t / 1000),
              [("line", dict(c=INK, lw=1.6), "Permukaan jalur lalu lintas"), ("patch", dict(fc=INK, ec=INK), "Tanggul pengaman"),
               ("line", dict(c=DTC, lw=0.8), "Saluran drainase"), ("line", dict(c=CUTC, lw=0.8, ls="--"), "Lereng galian"),
               ("line", dict(c=FILLC, lw=0.8, ls="--"), "Lereng timbunan")],
              f"SKALA 1 : {_fsk(sk_t)}", indeks(), cat)
    finish(sh, "Penampang jalan tipikal")

    # ================================================================ 4. PENAMPANG MELINTANG
    for j in range(n_xs_sheets):
        no += 1
        grp = list(range(j * per, min((j + 1) * per, len(xs_lembar))))
        a_, b_ = xs_lembar[grp[0]]["sta"], xs_lembar[grp[-1]]["sta"]
        sh = Sheet(cfg, f"PENAMPANG MELINTANG STA {cx.fmt_sta(a_)} - {cx.fmt_sta(b_)}", no, total_ref, kertas)
        blk_h = sh.draw_h / per
        for kk, ii in enumerate(grp):
            _blok_penampang(sh, cfg, xs_lembar[ii], tabel_vol[ii], sh.dx0, sh.dy1 - (kk + 1) * blk_h, sh.draw_w, blk_h)
        info_tepi(sh, dict(), [("line", dict(c=EGC, lw=0.8), "Tanah asli (existing ground)"), ("line", dict(c=FILLC, lw=0.9), "Desain (finished grade)"),
                               ("patch", dict(fc="white", hatch="////", ec=CUTC), "Galian (Ground Cut)"),
                               ("patch", dict(fc="white", hatch="////", ec=FILLC), "Timbunan (Ground Fill)"),
                               ("patch", dict(fc=INK, ec=INK), "Tanggul pengaman")],
                  "SKALA: tercantum pada tiap penampang", indeks((a_, b_)), cat)
        finish(sh, f"Penampang melintang STA {cx.fmt_sta(a_)} - {cx.fmt_sta(b_)}")

    # ================================================================ 5. TOTAL VOLUME TABLE
    for j in range(n_vol_sheets):
        no += 1
        sh = Sheet(cfg, "TABEL VOLUME GALIAN & TIMBUNAN", no, total_ref, kertas)
        cols = 3
        tw = sh.draw_w / cols - 4
        th = sh.draw_h / 2 - 8
        for t in range(tabs_per_sheet):
            ti = j * tabs_per_sheet + t
            if ti >= n_tab:
                break
            rows = tabel_vol[ti * rows_per_tab:(ti + 1) * rows_per_tab]
            cc, rr = t % cols, t // cols
            a_ = sh.ax(sh.dx0 + cc * (tw + 4), sh.dy1 - (rr + 1) * (th + 8), tw, th)
            a_.axis("off")
            data = [[cx.fmt_sta(r["sta"]), f"{r['luas_timbunan']:.2f}", f"{r['luas_galian']:.2f}", f"{r['vol_timbunan']:.2f}",
                     f"{r['vol_galian']:.2f}", f"{r['kum_timbunan']:.2f}", f"{r['kum_galian']:.2f}"] for r in rows]
            frac = (len(rows) + 1.6) / (rows_per_tab + 1.6)
            tb = a_.table(cellText=data, colLabels=["Station", "Fill Area", "Cut Area", "Fill Volume", "Cut Volume", "Cumulative\nFill Vol", "Cumulative\nCut Vol"],
                          cellLoc="left", colLoc="left", bbox=[0, 1 - frac, 1, frac])
            tb.auto_set_font_size(False); tb.set_fontsize(4.5)
            for (ri, ci), cell in tb.get_celld().items():
                cell.set_edgecolor("#d62728"); cell.set_linewidth(0.3)
                cell.get_text().set_color("#1f3fbf")
            a_.set_title("Total Volume Table", fontsize=5.5, color="#1f3fbf", pad=2)
        last = tabel_vol[-1]
        sh.fig.text(sh.dx0 / sh.W, (sh.dy0 + 1) / sh.H,
                    f"TOTAL: timbunan {last['kum_timbunan']:,.2f} m3  |  galian {last['kum_galian']:,.2f} m3  |  luas (m2) pada stasiun; volume = average end area dari penampang tiap {cfg['interval_penampang_m']:g} m",
                    fontsize=6, weight="bold")
        info_tepi(sh, dict(), [("line", dict(c="#1f3fbf", lw=0.8), "Luas m2, volume m3 (bank / padat)")], "TANPA SKALA", indeks(), cat)
        finish(sh, "Tabel volume galian & timbunan")

    total_ref[0] = len(sheets)
    with PdfPages(pdf_path) as pdf:
        for sh in sheets:
            pdf.savefig(sh.fig)
        info = pdf.infodict()
        info["Title"] = f"Gambar Perencanaan Jalan - {cfg['proyek']}"
        info["Author"] = cfg.get("perusahaan", "")
    prev = os.path.join(out_dir, "pratinjau")
    os.makedirs(prev, exist_ok=True)
    keep = {1, 2, len(chunks) + 2, len(chunks) + 3, len(sheets)}
    for sh in sheets:
        if sh.no in keep:
            sh.fig.savefig(os.path.join(prev, f"lembar_{sh.no:02d}.png"), dpi=120)
        plt.close(sh.fig)
    return daftar


def _poly_tanggul(d, codes, side):
    """Poligon tanggul (sisi -1 kiri / +1 kanan) dari titik berkode BERM_* + tetangga dalam, ditutup ke elevasi dasar."""
    idx = [i for i, c in enumerate(codes) if c.startswith("BERM") and np.sign(d[i][0]) == side]
    if not idx:
        return None
    inner = (min(idx) - 1) if side > 0 else (max(idx) + 1)
    outer = max(idx) if side > 0 else min(idx)
    if inner < 0 or inner >= len(d):
        return None
    zb = d[inner][1]
    seq = list(range(inner, outer + 1)) if side > 0 else list(range(inner, outer - 1, -1))
    pts = [(d[i][0], d[i][1]) for i in seq]
    if codes[outer] != "BERM_TOE":
        pts.append((d[outer][0], zb))
    return np.array(pts)


# ============================================================================ penampang tipikal
class _ConstT:
    def __init__(self, z):
        self.zv = z

    def z(self, x, y):
        return np.full(np.atleast_1d(x).shape, self.zv, float)


class _AlT:
    def at(self, s):
        return np.zeros(2), np.array([1.0, 0.0]), 0.0, None


class _PrT:
    def __init__(self, z):
        self.zv = z

    def z(self, s):
        return np.array([self.zv])


def _dim_h(ax, x0, x1, y, txt, below=False):
    ax.annotate("", xy=(x0, y), xytext=(x1, y), arrowprops=dict(arrowstyle="<->", lw=0.4, color=INK, shrinkA=0, shrinkB=0))
    ax.text((x0 + x1) / 2, y, txt, fontsize=5, ha="center", va="top" if below else "bottom", bbox=dict(fc="white", ec="none", pad=0.15))


def _lembar_tipikal(sh, cfg, s):
    import haul_road as hr

    geo = s["geometri"]
    zc = 0.0
    hc = cfg["galian"]["tinggi_jenjang_m"] * 1.6 or 7.0
    hf = cfg["timbunan"]["tinggi_jenjang_m"] * 1.6 or 6.0
    cut = hr.penampang(cfg, geo, _AlT(), _PrT(zc), _ConstT(zc + hc), 0.0, None)
    fil = hr.penampang(cfg, geo, _AlT(), _PrT(zc), _ConstT(zc - hf), 0.0, None)
    band_h = 3 * 6.5
    axw, axh = sh.draw_w - 34, sh.draw_h - band_h - 34
    ext = max(abs(np.array([p[0] for p in cut["design"] + fil["design"]])).max() + 3, 15)
    zr = (hc + hf) * 1.35 + 4
    sk = next(v for v in SKALA_STANDAR if v >= cfg["lembar"]["skala_penampang"] and axw * v / 1000 >= 2 * ext and axh * v / 1000 >= zr)
    ax = sh.ax(sh.dx0 + 30, sh.dy0 + band_h + 6, axw, axh)
    span_x, span_y = axw * sk / 1000, axh * sk / 1000
    zm = (hc - hf) / 2
    ax.set_xlim(-span_x / 2, span_x / 2); ax.set_ylim(zm - span_y / 2, zm + span_y / 2)
    common = {"ETW", "SHLD", "DTCH_BI", "DTCH_BO", "DTCH_TO", "BERM_TI", "BERM_TO", "BERM_TOE", "CL"}

    def split(x):
        d = x["design"]
        ci = [i for i, p in enumerate(d) if p[2] == "CL"][0]
        L = [i for i in range(ci, -1, -1) if d[i][2] in common]
        R = [i for i in range(ci, len(d)) if d[i][2] in common]
        return d, min(L), max(R)

    for x, col, below in ((cut, CUTC, False), (fil, FILLC, True)):
        d, i0, i1 = split(x)
        o = [p[0] for p in d]; z = [p[1] for p in d]
        ax.plot(o[:i0 + 1], z[:i0 + 1], c=col, lw=0.9, ls="--")
        ax.plot(o[i1:], z[i1:], c=col, lw=0.9, ls="--")
        for i in list(range(0, i0)) + list(range(i1, len(d) - 1)):
            (oa, za, _), (ob, zb, _) = d[i], d[i + 1]
            if abs(zb - za) > 0.2:
                r = abs(ob - oa) / abs(zb - za)
                ang = math.degrees(math.atan2(zb - za, ob - oa))
                ang = (ang + 90) % 180 - 90
                ax.text((oa + ob) / 2, (za + zb) / 2, f"{r:g}H:1V", fontsize=4.9, rotation=ang, ha="center", va="bottom", color=col)
            elif abs(ob - oa) > 0.3:
                _dim_h(ax, oa, ob, za + (0.45 if not below else -0.45), f"{abs(ob - oa):.2f}", below)
    d, i0, i1 = split(cut)
    core = d[i0:i1 + 1]
    o = np.array([p[0] for p in core]); z = np.array([p[1] for p in core]); c = [p[2] for p in core]
    ax.plot(o, z, c=INK, lw=0.6)
    ie = [i for i, cc in enumerate(c) if cc == "ETW"]
    ax.plot(o[ie[0]:ie[-1] + 1], z[ie[0]:ie[-1] + 1], c=INK, lw=2.2, solid_capstyle="butt")
    for i in range(len(c) - 1):
        if c[i].startswith("DTCH") or c[i + 1].startswith("DTCH"):
            if not (c[i] in ("BERM_TI",) or c[i + 1] in ("BERM_TI",)):
                ax.plot(o[i:i + 2], z[i:i + 2], c=DTC, lw=1.1)
    for side in (-1, 1):
        pg = _poly_tanggul(list(zip(o, z)), c, side)
        if pg is not None:
            ax.add_patch(MPoly(pg, closed=True, fc=INK, ec=INK, lw=0.4))
    yb = min(z) - 1.4
    xs_dim = sorted(set(round(v, 3) for v in o))
    lvl = 0
    for a_, b_ in zip(xs_dim[:-1], xs_dim[1:]):
        if b_ - a_ > 0.2:
            small = (b_ - a_) < 1.2
            lvl = (lvl + 1) % 3 if small else 0
            _dim_h(ax, a_, b_, yb - 0.75 * lvl, f"{b_ - a_:.2f}", True)
    for a_ in xs_dim:
        ax.plot([a_, a_], [yb - 1.6, float(np.interp(a_, o, z))], c="#999", lw=0.25)
    cf = max(cfg["kemiringan_melintang"], 0.02)
    for side in (-1, 1):
        ax.text(side * geo["W_lurus"] / 4, zc + 0.3, f"{cf * 100:.0f}%", fontsize=5.6, ha="center")
    Hb = s["tanggul_tinggi_m"]
    bi = [i for i, cc in enumerate(c) if cc.startswith("BERM") and o[i] > 0]
    if bi:
        ob = max(o[i] for i in bi) + 0.6
        zb0 = z[ie[-1]]
        ax.annotate("", xy=(ob, zb0), xytext=(ob, zb0 + Hb), arrowprops=dict(arrowstyle="<->", lw=0.4))
        ax.text(ob + 0.2, zb0 + Hb / 2, f"{Hb:.2f}", fontsize=5, va="center")
    sal = cfg["saluran"]
    if any(cc.startswith("DTCH") for cc in c):
        jd = [i for i, cc in enumerate(c) if cc == "DTCH_BO" and o[i] > 0]
        if jd:
            od = o[jd[0]] + 0.3
            ax.annotate("", xy=(od, z[jd[0]]), xytext=(od, z[jd[0]] + sal["dalam_m"]), arrowprops=dict(arrowstyle="<->", lw=0.35))
            ax.text(od + 0.15, z[jd[0]] + sal["dalam_m"] / 2, f"{sal['dalam_m']:.2f}", fontsize=4.6, va="center")
    ax.text(0, zm - span_y * 0.44,
            f"Jalur lalu lintas {geo['W_lurus']:.2f} m ({cfg['jumlah_jalur']} jalur, crown {cf * 100:.0f}%)  |  saluran: dasar {sal['lebar_dasar_m']} m, dalam {sal['dalam_m']} m, sisi {sal['kemiringan_sisi_HV']}H:1V  |  "
            f"tanggul {Hb:.2f} m  |  perkerasan {cfg['lapis_perkerasan']['tebal_m']} m {cfg['lapis_perkerasan']['material']}\n"
            f"Galian {cfg['galian']['kemiringan_HV']}H:1V, jenjang {cfg['galian']['lebar_jenjang_m']} m tiap {cfg['galian']['tinggi_jenjang_m']} m  |  "
            f"Timbunan {cfg['timbunan']['kemiringan_HV']}H:1V, jenjang {cfg['timbunan']['lebar_jenjang_m']} m tiap {cfg['timbunan']['tinggi_jenjang_m']} m  (merah = galian, hijau = timbunan)",
            fontsize=5.6, ha="center", va="bottom")
    ax.set_title("PENAMPANG JALAN", fontsize=10, pad=6, bbox=dict(fc="white", ec=INK, lw=0.6, pad=2.5))
    ax.tick_params(labelsize=5, right=True, labelright=True)
    ax.set_xticks(np.arange(math.ceil(-span_x / 2 / 5) * 5, span_x / 2, 5))
    for v in ax.get_xticks():
        ax.axvline(v, c=GRID, lw=0.2, zorder=0)
    for sp in ax.spines.values():
        sp.set_color(BAND)
    ax.text(0.005, 0.99, f"SKALA 1:{_fsk(sk)}  |  elevasi relatif terhadap CL", transform=ax.transAxes, fontsize=6, weight="bold", va="top")
    return sk


# ============================================================================ blok penampang melintang
def _blok_penampang(sh, cfg, x, row, X, Y, Wb, Hb_):
    band_h = 3 * 5.5
    lab_w = 28.0
    ax_h = Hb_ - band_h - 15
    ax_w = Wb - lab_w - 8
    d = np.array([(o, z) for o, z, _ in x["design"]])
    g = x["ground"]
    ext = max(abs(d[:, 0]).max() + 4, 20)
    zg_d = np.interp(d[:, 0], g[:, 0], g[:, 1])
    zlo = min(d[:, 1].min(), zg_d.min()) - 1.5
    zhi = max(d[:, 1].max(), zg_d.max()) + 3.5
    sk = next((v for v in SKALA_STANDAR if v >= cfg["lembar"]["skala_penampang"] and ax_w * v / 1000 >= 2 * ext and ax_h * v / 1000 >= (zhi - zlo)), SKALA_STANDAR[-1])
    span_x, span_y = ax_w * sk / 1000, ax_h * sk / 1000
    zmid = (zlo + zhi) / 2
    ax = sh.ax(X + lab_w, Y + band_h + 2, ax_w, ax_h)
    ax.set_xlim(-span_x / 2, span_x / 2); ax.set_ylim(zmid - span_y / 2, zmid + span_y / 2)
    oo = np.linspace(d[0, 0], d[-1, 0], 400)
    zd = np.interp(oo, d[:, 0], d[:, 1]); zg = np.interp(oo, g[:, 0], g[:, 1])
    ax.fill_between(oo, zd, zg, where=zg > zd, facecolor="none", hatch="////", edgecolor=CUTC, lw=0)
    ax.fill_between(oo, zd, zg, where=zg <= zd, facecolor="none", hatch="////", edgecolor=FILLC, lw=0)
    m = (g[:, 0] >= -span_x / 2) & (g[:, 0] <= span_x / 2)
    ax.plot(g[m, 0], g[m, 1], c=EGC, lw=0.7)
    ax.plot(d[:, 0], d[:, 1], c=FILLC, lw=0.8)
    cds = x["codes"]
    ie = [i for i, c in enumerate(cds) if c == "ETW"]
    ax.plot(d[ie[0]:ie[-1] + 1, 0], d[ie[0]:ie[-1] + 1, 1], c=INK, lw=1.6)
    for i in range(len(cds) - 1):
        if cds[i].startswith("DTCH") and cds[i + 1].startswith("DTCH") or (cds[i] == "ETW" and cds[i + 1] == "DTCH_BI") or (cds[i] == "DTCH_BI" and cds[i + 1] == "ETW"):
            ax.plot(d[i:i + 2, 0], d[i:i + 2, 1], c=DTC, lw=0.9)
    for side in (-1, 1):
        pg = _poly_tanggul(d.tolist(), cds, side)
        if pg is not None:
            ax.add_patch(MPoly(pg, closed=True, fc=INK, ec=INK, lw=0.3))
    for v in np.arange(math.ceil(-span_x / 2 / 5) * 5, span_x / 2, 5):
        ax.axvline(v, c=GRID, lw=0.25, ls="--", zorder=0)
    ax.axvline(0, c=INK, lw=0.4, ls=(0, (6, 2, 1, 2)))
    dz = 2 if span_y <= 30 else 5 if span_y <= 80 else 10
    ax.set_yticks(np.arange(math.ceil((zmid - span_y / 2) / dz) * dz, zmid + span_y / 2, dz))
    ax.tick_params(axis="y", labelsize=4.6, length=2, labelright=True, right=True)
    ax.tick_params(axis="x", length=0, labelbottom=False)
    for sp in ax.spines.values():
        sp.set_color(BAND)
    for i in (0, len(d) - 1):
        ax.text(d[i, 0], d[i, 1] + span_y * 0.02, f"OFF:{d[i, 0]:.2f}\nELEV:{d[i, 1]:.2f}", rotation=90, fontsize=4.3, ha="center", va="bottom")
    ax.text(0.15, x["zc"] + span_y * 0.07, f"OFF:0.00\nELEV:{x['zc']:.2f}", rotation=90, fontsize=4.3, ha="left", va="bottom")
    ax.text(0.995, 0.97, f"SKALA 1:{_fsk(sk)}", transform=ax.transAxes, fontsize=5.2, weight="bold", va="top", ha="right")
    at = sh.ax(X + lab_w + ax_w / 2 - 16, Y + Hb_ - 11, 32, 7.5); at.set_xticks([]); at.set_yticks([])
    at.text(0.5, 0.5, cx.fmt_sta(x["sta"]), ha="center", va="center", fontsize=8.5, transform=at.transAxes)
    am = sh.ax(X + lab_w + 2, Y + band_h + ax_h - 15, 64, 14); am.axis("off")
    tb = am.table(cellText=[["Ground Cut", f"{x['cut']:.2f}", f"{row['vol_galian']:.2f}", f"{row['kum_galian']:.2f}"],
                            ["Ground Fill", f"{x['fill']:.2f}", f"{row['vol_timbunan']:.2f}", f"{row['kum_timbunan']:.2f}"]],
                  colLabels=["Material Name", "Area", "Volume", "Cumulative Volume"], cellLoc="center", bbox=[0, 0, 1, 0.74])
    tb.auto_set_font_size(False); tb.set_fontsize(4.3)
    for (_, _), cell in tb.get_celld().items():
        cell.set_edgecolor("#d62728"); cell.set_linewidth(0.3); cell.get_text().set_color("#1f3fbf")
    am.text(0.5, 0.87, f"Material(s) at Station {cx.fmt_sta(x['sta'])}", ha="center", va="center", fontsize=4.6, color="#1f3fbf", transform=am.transAxes)
    am.add_patch(Rectangle((0, 0), 1, 1, transform=am.transAxes, fill=False, ec="#1f3fbf", lw=0.5))
    ab = sh.ax(X, Y, Wb - 8 + 0, band_h); ab.set_xlim(0, Wb - 8); ab.set_ylim(0, band_h); ab.axis("off")
    ab.add_patch(Rectangle((0, 0), Wb - 8, band_h, fill=False, ec=BAND, lw=0.5))
    for r in (1, 2):
        ab.plot([0, Wb - 8], [r * band_h / 3] * 2, c=BAND, lw=0.4)
    ab.plot([lab_w, lab_w], [0, band_h], c=BAND, lw=0.5)
    for r, lab in enumerate(["EXISTING ELEVATIONS", "PROPOSED ELEVATIONS", "OFFSET"]):
        ab.text(1, band_h - (r + 0.5) * band_h / 3, lab, fontsize=4.3, va="center")
    for v in np.arange(math.ceil(-span_x / 2 / 5) * 5, span_x / 2, 5):
        xm = lab_w + (v + span_x / 2) / span_x * ax_w
        if g[0, 0] <= v <= g[-1, 0]:
            ab.text(xm, band_h - 0.5 * band_h / 3, f"{np.interp(v, g[:, 0], g[:, 1]):.2f}", fontsize=4.1, ha="center", va="center")
        if d[0, 0] <= v <= d[-1, 0]:
            ab.text(xm, band_h - 1.5 * band_h / 3, f"{np.interp(v, d[:, 0], d[:, 1]):.2f}", fontsize=4.1, ha="center", va="center")
        ab.text(xm, band_h - 2.5 * band_h / 3, f"{v:.2f}", fontsize=4.1, ha="center", va="center")
